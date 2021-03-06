import datetime
import logging
from typing import Optional, Dict

import netaddr
from bson import ObjectId

import sdn_utils
from flow import FlowState
from repository.repository import Repository


class PolicyRoute:
    TYPE_STATIC = 1
    TYPE_AUTOMATE = 2

    STATUS_WAIT_APPLY = 0
    STATUS_WAIT_UPDATE = 1
    STATUS_WAIT_REMOVE = 2

    STATUS_ACTIVE = 3

    ACTION_DROP = 1
    ACTION_NEXT_HOP_IP = 2
    ACTION_EXIT_IF = 3

    # Custom
    # ACTION_NEXT_HOP_IP_CUSTOM = 2
    # ACTION_EXIT_IF_CUSTOM = 2

    FIELDS = ('src_ip',
              'src_wildcard',
              'src_port',
              'dst_ip',
              'dst_wildcard',
              'dst_port',
              'name',
              'policy_id',
              'time'
              )

    def __init__(self, policy=None, **kwargs):
        # TODO Support port
        self.src_network = None
        self.src_port = 'any'
        self.dst_network = None
        self.dst_port = 'any'
        self.name = None

        for field in self.FIELDS:
            setattr(self, field, None)

        if policy:
            for field, value in policy.items():
                if field in self.FIELDS:
                    setattr(self, field, value)

            self.policy = {}
            if policy.get('actions'):
                self.actions = policy['actions'].copy()
            else:
                self.actions = []
        else:
            self.policy = {}
            self.actions = []

        self.info = {}

    def set_name(self, name):
        self.name = name

    def set_policy(self, **kwargs):
        if kwargs.get('src_network'):
            self.src_network = netaddr.IPNetwork(kwargs.get('src_network'))

        if kwargs.get('dst_network'):
            self.dst_network = netaddr.IPNetwork(kwargs.get('dst_network'))

        if kwargs.get('src_port'):
            self.src_port = int(kwargs.get('src_port'))

        if kwargs.get('dst_port'):
            self.dst_port = int(kwargs.get('dst_port'))

    def set_action(self, action: Dict[str, Optional[str]]):
        raise NotImplementedError()

    def diff(self, new_policy):
        raise NotImplementedError()

    def add_action(self, device_id, management_ip, action, data=None):
        self.actions.append({
            'device_id': device_id,
            'management_ip': management_ip,
            'action': action,
            'data': data
        })

    def remove_action(self, node):
        self.actions = filter(lambda _node: _node != node, self.actions)

    def get_only_policy(self):
        return {
            'src_ip': str(self.src_network.ip),
            'src_port': None,
            'src_wildcard': str(self.src_network.hostmask),
            'dst_ip': str(self.dst_network.ip),
            'dst_port': None,
            'dst_wildcard': str(self.dst_network.hostmask),
        }

    def get_policy(self):
        return {
            'name': self.name,
            'new_flow': {
                'src_ip': str(self.src_network.ip),
                'src_port': self.src_port,
                'src_wildcard': str(self.src_network.hostmask),
                'dst_ip': str(self.dst_network.ip),
                'dst_port': self.dst_port,
                'dst_wildcard': str(self.dst_network.hostmask),
                'actions': self.actions.copy(),
            },
            'info': self.info
        }


class FlowRoutingRepository(Repository):

    # TYPES = (
    #     (1, 'Static'),
    #     (2, 'Automate')
    # )

    def __init__(self):
        super(FlowRoutingRepository, self).__init__()
        self.policy = self.db.flow_routing  # Todo deprecated
        self.model = self.db.flow_routing
        self.policy_pending = self.db.policy_pending

    def get_by_id(self, _id):
        return self.policy.find_one({"_id": ObjectId(_id)})

    def get_flows_by_state(self, state, limit=10):
        if state not in FlowState:
            raise ValueError("Flow state: {} not in FlowState class".format(state))

        flows = self.policy.find({'state': state.value}).limit(limit)

        return flows

    def set_flow_state(self, flow_id, state):
        if state not in FlowState:
            raise ValueError("Flow state: {} not in FlowState class".format(state))

        flow = self.policy.find_one({'flow_id': flow_id})
        if not flow:
            logging.warning("Flow id: {} not exist !!!".format(flow_id))
            return True

        self.policy.update_one({'flow_id': flow_id}, {'$set': {'state': state.value}})

        return True

    def add_new_pending_policy(self, policy):
        self.policy_pending.insert_one({
            'type': 'update',
            'policy': policy,
            'created_at': sdn_utils.datetime_now()
        })

    def add_or_update_flow_routing(self, flow_routing):
        new_flow = flow_routing['new_flow']
        old_flow = self.model.find_one({
            'src_ip': new_flow['src_ip'],
            'src_port': new_flow['src_port'],
            'src_wildcard': new_flow['src_wildcard'],
            'dst_ip': new_flow['dst_ip'],
            'dst_port': new_flow['dst_port'],
            'dst_wildcard': new_flow['dst_wildcard']
        })

        now = sdn_utils.datetime_now()

        flow_routing['created_at'] = now
        flow_routing['updated_at'] = now

        new_flow_actions = []
        wait_remove = []

        for action in flow_routing['new_flow']['actions']:
            action['device_id'] = ObjectId(action['device_id'])
            new_flow_actions.append(action['device_id'])

        if old_flow:
            for old_flow_action in old_flow['actions']:
                if old_flow_action['device_id'] not in new_flow_actions:
                    wait_remove.append(old_flow_action)
            print(wait_remove)
            remove_old_device = {
                'name': 'remove_device',
                'src_ip': '0.0.0.0',
                'src_port': 'any',
                'src_wildcard': '0.0.0.0',
                'dst_ip': '0.0.0.0',
                'dst_port': 'any',
                'dst_wildcard': '0.0.0.0',
                'actions': wait_remove,
                'flow_id': old_flow['flow_id'],
                'info': {
                    'submit_from': {
                        'type': PolicyRoute.TYPE_STATIC,
                        'user': 'Unknown - Todo Implement'
                    },
                    'status': PolicyRoute.STATUS_WAIT_REMOVE
                }
            }
            self.model.update_one({
                '_id': old_flow['_id']
            }, {'$set': {
                'new_flow': flow_routing['new_flow'],
                'info': flow_routing['info']
            }})
            self.model.insert_one(remove_old_device)
            return True

        self.model.insert_one(flow_routing)
        return True

    def find_pending_apply(self, limit=None):
        flow_list = self.policy.find({
            'info.status': {'$in': [
                PolicyRoute.STATUS_WAIT_APPLY,
                PolicyRoute.STATUS_WAIT_REMOVE,
                PolicyRoute.STATUS_WAIT_UPDATE
            ]}
        })

        if isinstance(limit, int):
            flow_list = flow_list.limit(limit)

        flow_list = flow_list.sort('updated_at', 1)

        return flow_list

    def get_pending(self, limit=None, device_ip=None):

        policy_list = self.policy_pending.find({})
        policy_list.sort('time', 1)

        if limit:
            policy_list.limit(limit)

        return policy_list

    def set_status_apply(self, flow_id: int):
        self.policy.update_one({
            'flow_id': flow_id
        }, {'$set': {'status': PolicyRoute.STATUS_ACTIVE, 'new_flow': {}}})

    def set_status_wait_remove(self, flow_id: int):
        self.policy.update_one({
            'flow_id': flow_id
        }, {'$set': {'info.status': PolicyRoute.STATUS_WAIT_REMOVE}})

    def update_flow(self, flow):
        flow['updated_at'] = sdn_utils.datetime_now()
        self.policy.update_one({
            '_id': flow['_id']
        }, {'$set': flow})

    def sum_bytes_pending_has_pass_interface(self, interface_ip, limit=1, side='in'):
        if side == 'in':
            side = 'policy.info.old_path_link.in'
            new_side = 'policy.info.new_path_link.in'
        else:
            side = 'policy.info.old_path_link.out'
            new_side = 'policy.info.new_path_link.out'

        policy_list = self.policy_pending.aggregate([
            {
                '$match': {
                    side: interface_ip,
                    new_side: {'$ne': interface_ip}  # Switch to another route
                }
            },
            {
                '$group': {
                    '_id': {
                        'interface_ip': "$" + side
                    },
                    'total': {
                        '$sum': '$policy.info.in_bytes'
                    }
                }
            },
            {
                '$limit': limit
            }
        ])

        return policy_list

    def get_last_policy_apply(self, device_ip, time=15, **kwargs):
        """

        :param device_ip: Device IP Address
        :param time: Time in seconds
        :return:
        """
        return self.policy.find_one({
            'info.submit_from.device_ip': device_ip,
            'created_at': {'$lte': datetime.datetime.now() - datetime.timedelta(seconds=time)}
        }, sort=[('created_at', -1)], **kwargs)

    def set_policy(self, policy):
        # Update time
        policy['created_at'] = sdn_utils.datetime_now()
        self.policy.replace_one({
            'policy_id': policy['policy_id']
        }, policy, upsert=True)

    def get_policy_old_path_has_pass_interface(self, interface_ip: str, submit_from_type: int, limit=1, side='in',
                                               device_ip=None):
        db_filter = {
            'info.old_path_link.in': interface_ip,
            'info.submit_from.type': submit_from_type
        }
        if device_ip:
            db_filter['info.submit_from.device_ip'] = device_ip
        return self.policy.find(db_filter, limit=limit)

    def get_policy_is_submit_from(self, device_ip):
        return self.policy.find_one({
            'info_submit_from.device_ip': device_ip
        })

    def get_all(self):
        return self.policy.find()

    def get_by_submit_from_type(self, submit_from_type: int, limit=None, skip=None):
        return self.policy.find({'info.submit_from.type': submit_from_type})

    def add_remove_policy_pending(self, policy):
        """

        :param policy: Policy ID or Policy info
        :return:
        """
        if isinstance(policy, int):
            policy = self.policy.find_one({'policy_id': policy})
            if not policy:
                return

        self.policy_pending.insert_one({
            'type': 'remove',
            'policy': policy,
            'created_at': sdn_utils.datetime_now()
        })

    def remove_pending(self, _id):
        self.policy_pending.remove(_id)

    def remove_policy(self, _id):
        self.policy.remove(_id)

    def remove_by_id(self, _id):
        self.policy.remove({"_id": ObjectId(_id)})

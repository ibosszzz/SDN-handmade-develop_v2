import requests
ip = "10.30.7.31"

def get_wildcard(mask):
    wildcard = ""
    check = ""
    for i in range(32):
        if len(check) == 8:
            check = str(int(check, 2))
            wildcard = wildcard+check+"."
            check = ""
        if i < mask:
            check = check+"0"
        else:
            check = check+"1"
    check = str(int(check, 2))
    wildcard = wildcard+check
    return wildcard

def get_nexthop_from_management_ip(device_id1, device_id2):
    links = requests.get("http://"+ip+":5001/api/v1/link/").json()
    for link in links['links']:
        if device_id1 == link['src_node_ip'] and device_id2 == link['dst_node_ip']:
            return link['dst_ip']
        elif device_id1 == link['dst_node_ip'] and device_id2 == link['src_node_ip']:
            return link['src_ip']

def find_nexthop_node(src_mgmtip, dst_mgmtip):
    flows = requests.get("http://"+ip+":5001/api/v1/flow").json()
    for flow in flows['flows']:
        if (flow['ipv4_dst_addr'] == dst_mgmtip):
            return requests.get("http://"+ip+":5001/api/v1/device/"+flow['ipv4_next_hop']).json()['devices']['management_ip'], flow

def change_route(path, flow):
    new_flow = {'name':'new_route', 'src_ip':flow['ipv4_src_addr'], 'src_port':'any', 'src_subnet':get_wildcard(flow['src_mask']), 'dst_ip':flow['ipv4_dst_addr'], 'dst_port':'any', 'dst_subnet':get_wildcard(flow['dst_mask']), 'actions':[]}
    for i in range(len(path)-1):
        device = requests.get("http://{}:5001/api/v1/device/mgmtip/{}".format(
            ip,
            path[i]
        )).json()
        device_id = device['device']['_id']['$oid']
        action = {'device_id':device_id, 'action':2, 'data':get_nexthop_from_management_ip(path[i], path[i+1])}
        new_flow['actions'].append(action)
    response = requests.post("http://"+ip+":5001/api/v1/flow/routing", json=new_flow)
    print("change route success")

def get_path(src_mgmtip, dst_mgmtip):
    paths = requests.get("http://"+ip+":5001/api/v1/path/"+src_mgmtip+","+dst_mgmtip).json()
    nexthop_node, flow = find_nexthop_node(src_mgmtip, dst_mgmtip)
    for path in paths['paths']:
        if (path['nexthop_node'] != nexthop_node):
            change_route(path['path'], flow)
            break

get_path("100.1.1.1", "100.1.3.1")
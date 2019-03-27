import requests
ip = "10.30.7.46"

routes = requests.get("http://"+ip+":5001/api/v1/routes/").json()['routes']

def get_name_from_device_id(device_id):
    return requests.get("http://"+ip+":5001/api/v1/device/"+device_id).json()['device'][0]['name'].split(".")[0]

def get_device_id(network, next_hop=None, device_id=None):
    for route in routes:
        if next_hop:
            if route['dst'] == network and route['next_hop'] == next_hop:
                return route['device_id']['$oid'], route['next_hop'], route['if_index']
        elif device_id:
            if route['dst'] == network and route['device_id']['$oid'] == device_id:
                return route['device_id']['$oid'], route['next_hop'], route['if_index']

def get_utilize(link):
    return link['src_in_use']+link['dst_in_use']+link['src_out_use']+link['dst_out_use']

def get_link(name, next_hop, if_index):
    #print(name, next_hop, if_index)
    links = requests.get("http://"+ip+":5001/api/v1/link/"+name).json()['link']
    for link in links:
        if link['dst_ip'] == next_hop:
            return link['dst_node_hostname'].split(".")[0], link['dst_node_id']['$oid'], get_utilize(link)
        elif link['src_ip'] == next_hop:
            return link['src_node_hostname'].split(".")[0], link['src_node_id']['$oid'], get_utilize(link)
        elif link['src_if_index'] == if_index and link['src_node_hostname'] and next_hop == "0.0.0.0":
            return link['dst_node_hostname'].split(".")[0], link['dst_node_id']['$oid'], get_utilize(link)
        elif link['dst_if_index'] == if_index and link['dst_node_hostname'] and next_hop == "0.0.0.0":
            return link['src_node_hostname'].split(".")[0], link['src_node_id']['$oid'], get_utilize(link)
        else:
            pass

def route(src, dst):
    device_id, next_hop, if_index = get_device_id(src, "0.0.0.0")
    name = get_name_from_device_id(device_id)
    print(name, end="")
    dst_device_id, next_hop, if_index = get_device_id(dst, "0.0.0.0")
    while (dst_device_id != device_id):
        print(" -> ", end="")
        device_id, next_hop, if_index = get_device_id(dst, None, device_id)
        name, device_id, utilize = get_link(get_name_from_device_id(device_id), next_hop, if_index)
        print("%.4f" % utilize+" -> "+name, end="")
    print()


route("100.1.1.0", "100.1.3.0")
route("100.1.2.0", "100.1.4.0")
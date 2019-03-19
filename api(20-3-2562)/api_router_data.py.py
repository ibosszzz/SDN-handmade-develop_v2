import requests
ip = "10.30.7.31"
devices = requests.get("http://"+ip+":5001/api/v1/device/").json()

def show_router_name():
    for device in devices['devices']:
        print(device['name'])

def show_router_interfaces():
    for device in devices['devices']:
        print(device['name'])
        for interface in device['interfaces']:
            if 'ipv4_address' in interface:
                print(interface['description'] +" ip: "+ interface['ipv4_address'])

def show_routes():
    for device in devices['devices']:
        print(device['name'])
        routes = requests.get("http://"+ip+":5001/api/v1/routes/"+device['name']).json()
        for route in routes['routes']:
            print("destination : "+route['dst']+" mask : "+route['mask']+" next_hop : "+route['next_hop'])

#show_router_name()
#show_router_interfaces()
show_routes()
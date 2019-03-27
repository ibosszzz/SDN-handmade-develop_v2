import requests
ip = "10.30.7.46"

def device_info():
    devices = requests.get("http://"+ip+":5001/api/v1/device/").json()
    for device in devices['devices']:
        print("name : "+device['name'].split(".")[0])
        for interface in device['interfaces']:
            if ("ipv4_address" in interface):
                print(interface['description']+" ip : "+interface['ipv4_address']+" admin_status : ", end="")
                print(interface['admin_status'])
                print(" bw_in_usage_persec : "+str(interface['bw_in_usage_persec'])+" bw_out_usage_persec : "+str(interface['bw_out_usage_persec']))
        print()

device_info()

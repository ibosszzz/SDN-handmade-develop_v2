import netmiko
from pymongo import MongoClient

client = MongoClient('localhost', 27017)
db = client['test_setup']
collection = db['device']

devices = client.test_setup.device.find()
for device in devices:
    cisco = {
        'device_type' : device['type'],
        'ip' : device['management_ip'],
        'username' : device['ssh_info']['username'],
        'password' : device['ssh_info']['password']
    }
    net_connect = netmiko.ConnectHandler(**cisco)
    #prompt = net_connect.find_prompt()
    #print(prompt)
    interface = 'f0/0' #interface connect to management device
    ip = '10.1.1.10' #ip management device
    port = '23456'
    source_interface = 'f0/0'

    snmp_commands = ['snmp-server enable traps', 'snmp-server community public RO', 'snmp-server community private RW']
    netflow_commands = ['interface '+interface, 'ip route-cache flow', 'exit', 'ip flow-export destination '+ip+' '+port, 'ip flow-export source '+source_interface, 'ip flow-export version 9', 'ip flow-cache timeout active 1', 'ip flow-cache  timeout inactive 15', 'ip flow-export template refresh-rate 1']
    snmp = net_connect.send_config_set(snmp_commands)
    print(snmp)
    netflow = net_connect.send_config_set(netflow_commands)
    print(netflow)

    save = net_connect.send_command("wr")
    print(save)
    show_run = net_connect.send_command("show run")
    print(show_run)

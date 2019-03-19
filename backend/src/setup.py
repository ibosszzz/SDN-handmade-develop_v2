import paramiko
import time
from pymongo import MongoClient

client = MongoClient('localhost', 27017)
devices = client.sdn01.device.find() #client.(database).(collection).find()

for device in devices:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(device['management_ip'], port=22, username=device['ssh_info']['username'], password=device['ssh_info']['password'])
    remote_connect = ssh.invoke_shell()
    output = remote_connect.recv(1000)
    print("connect to "+device['management_ip'], end=" ")
    if output.decode("utf-8")[-1] == "#":
        print("Privileged mode")
    elif output.decode("utf-8")[-1] == ">":
        print("User mode")
        remote_connect.send("enable\n")
        time.sleep(0.1)
        remote_connect.send(input()+"\n")
    else:
        pass
    # set snmp
    snmp_commands = ['conf t\n', 'snmp-server enable traps\n', 'snmp-server community public RO\n', 'snmp-server community private RW\n']
    for command in snmp_commands:
        remote_connect.send(command)
        time.sleep(0.5)
    # set netflow
    interfaces = client.sdn01.device.find({'management_ip': device['management_ip']}, {'_id':0, 'interfaces': 1})
    for interface in interfaces:
        if "ipv4_address" in interface:
            for command in ['interface '+interface+'\n', 'ip route-cache flow\n', 'exit\n']:
                remote_connect.send(command)
                time.sleep(0.5)
    ip = '10.30.7.100' #ip management device
    port = '23456'
    for command in ['ip flow-export destination '+ip+' '+port+'\n', 'ip flow-export version 9\n', 'ip flow-cache timeout active 1\n', 'ip flow-cache timeout inactive 15\n', 'ip flow-export template refresh-rate 1\n']:
        remote_connect.send(command)
        time.sleep(0.5)
    ssh.close()

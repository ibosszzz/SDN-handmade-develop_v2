from urllib.parse import quote

database = {
    'default': {
        'driver': 'mongodb',  # Currently support only mongo
        'uri': "mongodb://127.0.0.1:27017",
	#'uri': "mongodb://username:" + quote('password') + "@127.0.0.1:27017/",
        'database': 'sdn01',
        'max_pool_size': 10,
    }
}

rest_api = {
    'host': '0.0.0.0',
    'port': 5000
}

netmiko = {
    'global_delay_factor': 1
}

snmp_worker = {
    'pool': 4  # Can set auto or number
}

netflow = {
    'bind_ip': '0.0.0.0',
    'bind_port': 23456
}

app = {
    'version': '0.0.1 Beta'
}

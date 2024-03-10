#!/usr/bin/env python3

import requests
import logging
import os
import json

# Set up logging
logging.basicConfig(filename='logs/zabbix_automation_suite.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Define your Zabbix API endpoint and credentials
zabbix_url = "https://hetzner-monitor.wee.co.il/zabbix/api_jsonrpc.php"
zabbix_username = str(os.environ.get("ZABBIX_USERNAME")) # !!! Enviromental variable have to be added to a system
zabbix_password = str(os.environ.get("ZABBIX_PASSWORD")) # !!! Enviromental variable have to be added to a system

def zabbix_authentication():   
   # User authentication payload
    authentication = {
        "jsonrpc": "2.0",
        "method": "user.login",
        "params": {
            "user": zabbix_username,
            "password": zabbix_password
        },
        "id": 2
    }    
    # User logout payload
    logout = {
        "jsonrpc": "2.0",
        "method": "user.logout",
        "params": [],
        "id": 1
    }    
    kill_sessions = requests.post(zabbix_url, json=logout)
    logging.info(f"Logout from Zabbix request executed with status code: {kill_sessions.status_code}")
    with open("auth/zabbix_auth.txt", "w") as f:
        f.write("")
        os.chmod("auth/zabbix_auth.txt", 0o600)
    # Post authentication and save hash value to a variable
    try:
        auth = requests.post(zabbix_url, json=authentication)
        auth.raise_for_status()  # Raise HTTPError for bad responses        
        auth_parsed = auth.json()
        if "result" in auth_parsed:
            logging.info("Authentificated to Zabbix successfuly")
            with open("auth/zabbix_auth.txt", "w") as f:
                f.write(auth_parsed['result'])
                return True
        else: 
#            logging.info(f"{zabbix_username}, {zabbix_password}")
            logging.critical(f"Authentication failed with error: {json.dumps(auth_parsed['error'], indent=4)}")
            return False            
    except requests.RequestException as exception:
        logging.critical(f"Connection to Zabbix failed with exception: {exception}")
        return False

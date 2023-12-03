import requests
import json
import datetime
import urllib3
import re
import atexit
import time


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
headers = {
    'Authorization': 'Token key',
    'Content-Type': 'application/json',
    'Accept': 'application/json; indent=4',
}

def get_netbox_vm(server):
    response = requests.get(
        'https://netboxnew.wee.co.il/api/virtualization/virtual-machines/?q='+server,
        headers=headers, verify=False,timeout=180)
 
    if response.status_code != 204:

        Dict1 = json.loads(response.text)
        list_netbox_id_vm = []

        for i in Dict1["results"]:
            print([i])

        else:
            print("id")
        return list_netbox_id_vm
    print("STOP")
    return "STOP"

server='82.166.213.135'
List_netbox = get_netbox_vm(server)
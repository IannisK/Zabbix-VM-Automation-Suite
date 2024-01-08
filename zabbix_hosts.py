#!/usr/bin/env python3

import time
import socket
import json
import requests
import logging
import sys
import os
import re
import subprocess
from zabbix_auth import zabbix_authentication

templates_with_id = []
groups_with_id = []
auth_key = ""

# Set up logging for script
logging.basicConfig(filename='logs/zabbix_automation_suite.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

zabbix_url = "https://hetzner-monitor.wee.co.il/zabbix/api_jsonrpc.php"

# Function to obtain templates' IDs with specific names
def get_templates_id():
    templates = ["Template OS Windows", "Template OS Linux", "template cPanel backup"]
    global templates_with_id
    # Payload for search template ID with template name
    templateget = {
        "jsonrpc": "2.0",
        "method": "template.get",
        "params": {
            "output": ["templateid", "name"],
            "filter": {
                "host": templates
            }
        },
        "id": 3,
        "auth": auth_key
    }
    templates_info = requests.post(zabbix_url, json=templateget)
    if templates_info.status_code == 200:
        templates_info_pars = templates_info.json()
        if "result" in templates_info_pars:
            templates_with_id = templates_info_pars["result"]
            logging.info(f"Templates with IDs retrieved successfully")
            # logging.info(templates_with_id)
        else: 
            logging.warning(f"Request for templates with IDs failed with error: {json.dumps(templates_info_pars['error'], indent=4)}")
    else:
        logging.warning(f"Request for templates IDs failed with code: {templates_info.status_code}")

# Function to obtain groups' IDs with scecific names       
def get_groups_id():
    groups = ["Allwindows", "Windows General", "Linux servers", "Fortigate", "Uniq", "cPanels", "Clients"]
    global groups_with_id
    # Payload for search group ID with group name
    hostgroupget = {
        "jsonrpc": "2.0",
        "method": "hostgroup.get",
        "params": {
            "output": ["groupid", "name"],
            "filter": {
                "name": groups
            }
        },
        "id": 4,
        "auth": auth_key
    }
    groups_info = requests.post(zabbix_url, json=hostgroupget)
    if groups_info.status_code == 200:
        groups_info_pars = groups_info.json()
        if "result" in groups_info_pars:
            groups_with_id = groups_info_pars["result"]
            logging.info(f"Groups with IDs retrieved successfully")
            # logging.info(groups_with_id)
        else:
            logging.warning(f"Request for groups with IDs failed with error: {json.dumps(groups_info_pars['error'], indent=4)}")
    else:
        logging.warning(f"Request for templates IDs failed with code: {groups_info.status_code}")


# Function to check if IP address exists in Zabbix
def check_ip_in_zabbix(ip_address, client_socket):
    # Payload for host search in Zabbix with IP
    hostget = {
        "jsonrpc": "2.0",
        "method": "host.get",
        "params": {
            "output": ["hostid", "host", "name"],
            "selectParentTemplates": ["templateid", "name"],
            "selectGroups": ["groupid", "name"],
            "filter": {"ip": ip_address}
        },
        "id": 5,
        "auth": auth_key
    }
    # Send the API request
    try:
        hostinfo = requests.post(zabbix_url, json=hostget)
    except Exception as e:
        logging.error(f"Host.get request to Zabbix failed with error: {e}")
        response = ("HTTP/1.1 503 Service Unavailable\r\nContent-Length: 48\r\n\r\nConnection received but connect to Zabbix failed")
        client_socket.sendall(response.encode())
        return
    # Parse the response and check if the IP address exists
    try:
        hostinfo_pars = hostinfo.json()
    except json.JSONDecodeError:
        logging.error("Invalid JSON data")
        client_socket.close()
        return
            
    if "result" in hostinfo_pars and len(hostinfo_pars["result"]) != 0:
        # Save host info from Zabbix to a variable
        try:
            zabbix_host = { 
                "hostid": hostinfo_pars["result"][0]["hostid"],
                "hostname": hostinfo_pars["result"][0]["host"],
                "visiblename": hostinfo_pars["result"][0]["name"],
                "ip": ip_address,
                "groups": hostinfo_pars["result"][0]["groups"],
                "templates": hostinfo_pars["result"][0]["parentTemplates"]
                }
            logging.info(f"Host IP {ip_address} already exists in Zabbix")
            return zabbix_host  # IP address exists in Zabbix
        except Exception as e:
            logging.error(f"Error in check_ip_in_zabbix() function in zabbix_host dictionary {e}")
            return
    elif len(hostinfo_pars["result"]) == 0:
        logging.info(f"Host IP {ip_address} was not found")
        response = ("HTTP/1.1 404 Not Found\r\nContent-Length: 50\r\n\r\nConnection received but IP was not found in Zabbix")
        client_socket.sendall(response.encode())
        return False
    else: 
        logging.warning(f"Host IP {ip_address} search failed with error: {json.dumps(hostinfo_pars['error'], indent=4)}")
        response = ("HTTP/1.1 502 Bad Gateway\r\nContent-Length: 49\r\n\r\nConnection received but IP search in Zabbix failed")
        client_socket.sendall(response.encode())
        return

# Function to check accuracy between Zabbix and NetBox
def check_zabbix_accuracy(zabbix_host, netbox_host):
    changes = False
    templates_change = False
    groups_change = False
    # Compare and update simple fields
    for key in ["hostname", "visiblename"]:
        if zabbix_host[key] != netbox_host[key]:
            logging.info(f"Updating {key}: \"{zabbix_host[key]}\" -> \"{netbox_host[key]}\"")
            zabbix_host[key] = netbox_host[key]
            changes = True
    # Append unique templates
    zabbix_host_templates = [template["name"] for template in zabbix_host["templates"]] 
    if set(netbox_host["templates"]) != set(zabbix_host_templates) and "template cPanel backup" not in zabbix_host_templates:
        logging.info(f"Templates differ between NetBox and Zabbix. Replacing Zabbix templates with NetBox ones.")
        zabbix_host["templates"] = [{"name": template} for template in netbox_host["templates"]]
        changes = True
        templates_change = True
    # Append unique groups
    zabbix_host_groups = [group["name"] for group in zabbix_host["groups"]]
    if set(netbox_host["groups"]) != set(zabbix_host_groups):
        logging.info(f"Groups differ between NetBox and Zabbix. Replacing Zabbix groups with NetBox ones.")
        zabbix_host["groups"] = [{"name": group} for group in netbox_host["groups"]]
        changes = True
        groups_change = True
    return changes, zabbix_host, templates_change, groups_change

# Function to update a host in Zabbix
def zabbix_update_host(zabbix_host, templates_change, groups_change):        
    if templates_change:
        # Iterate over each template in zabbix_host["templates"] and complete missing template IDs
        for template in zabbix_host["templates"]:
            if "templateid" not in template:
                for template_with_id in templates_with_id:
                    if template_with_id["name"] == template["name"]:
                        template["templateid"] = template_with_id["templateid"]
                        break  # Exit the inner loop once the templateid is found
    if groups_change:
        # Iterate over each group in zabbix_host["groups"] and complete missing group IDs
        for group in zabbix_host["groups"]:
            if "groupid" not in group:
                for group_with_id in groups_with_id:
                    if group_with_id["name"] == group["name"]:
                        group["groupid"] = group_with_id["groupid"]
                        break  # Exit the inner loop once the group is found
    # Payload for host update in Zabbix
    host_update = {
        "jsonrpc": "2.0",
        "method": "host.update",
        "params": {
            "hostid": zabbix_host["hostid"],
            "host": zabbix_host["hostname"],
            "name": zabbix_host["visiblename"],
            "templates": [template["templateid"] for template in zabbix_host["templates"]],
            "groups": [group["groupid"] for group in zabbix_host["groups"]]
        },
        "id": 6,
        "auth": auth_key
    }
    # Send update request to Zabbix and check the result
    try:
        update_request = requests.post(zabbix_url, json=host_update)
    except Exception as e:
        logging.error(f"Host.update request to Zabbix failed with error: {e}")
        response = ("HTTP/1.1 503 Service Unavailable\r\nContent-Length: 48\r\n\r\nConnection received but connect to Zabbix failed")
        client_socket.sendall(response.encode())

    if update_request.status_code == 200:
        update_request_pars = update_request.json()
        if "result" in update_request_pars:
            logging.info(f"Host {zabbix_host['visiblename']} with IP {zabbix_host['ip']} updated succesfully")
        else:
            logging.error(f"Host {zabbix_host['visiblename']} with IP {zabbix_host['ip']} update failed with error: {json.dumps(update_request_pars['error'], indent=4)}")
    else: 
        logging.error(f"Connect to Zabbix failed with code: {update_request.status_code}")

# Function to create a host in Zabbix
def zabbix_create_host(host_name, visible_name, proxy, ip_address, templates, groups):
    # Execute ansible playbook with extra variables
    ansible_start_command = [
        "ansible-playbook",
        "-e",
        f'host_name="{host_name}" visible_name="{visible_name}" proxy="{proxy}" ip="{ip_address}" link_templates="{templates}" host_groups="{groups}"',
        "zabbix_create_host.yml"
    ]
    logging.info("Start of playbook zabbix_create_host")
    logging.info(f"Ansible variables: \nhost_name = {host_name} \nvisible_name = {visible_name} \nip = {ip_address} \nproxy = {proxy} \nlink_templates = {templates} \nhost_groups = {groups}")
    try:
        result = subprocess.run(ansible_start_command, check=True)
        logging.info(f"Host [{visible_name}] created successfully")
        return  # Playbook executed successfully
    except subprocess.CalledProcessError:
        logging.critical(f"Host [{visible_name}] creation failed with with return code {e.returncode} and output: {e.output.decode()}") # Playbook execution failed
        return

# Function to handle incoming connection
def handle_connection(client_socket):
    logging.info("Start of handle_connection function")
    # Handle connection and extract data from POST request
    netbox_data = client_socket.recv(8192)
    netbox_data = netbox_data.decode().strip()
    # logging.info(netbox_data)
    
    if "\r\n\r\n" not in netbox_data:
        logging.error("No header-body delimiter found")
        response = ("HTTP/1.1 400 Bad Request\r\n\r\n")
        client_socket.sendall(response.encode())
        client_socket.close()
        return
    headers, body = netbox_data.split("\r\n\r\n", 1)
    
    if not headers.startswith("POST"):
        logging.error("Received non-POST request")
        response = ("HTTP/1.1 400 Bad Request\r\n\r\n")
        client_socket.sendall(response.encode())
        client_socket.close()
        return 
    
    # Parse data from NetBox
    try:        
        netbox_host = json.loads(body)    
    except json.JSONDecodeError:
        logging.error("Invalid JSON data")
        response = ("HTTP/1.1 400 Bad Request\r\n\r\n")
        client_socket.sendall(response.encode())
        client_socket.close()
        return
    
    linux_fam = ["linux", "centos", "debian", "ubuntu"]
    templates = []
    groups = []

#    logging.info(json.dumps(netbox_host, indent=4))

    # IP address set with netmask discard if there is one
    try:
        ip_address = netbox_host.get("data", {}).get("primary_ip", {}).get("address")
        if "/" in ip_address: ip_address = ip_address.split('/')[0]
        logging.info(f"IP address retrieved successfully {ip_address}")
    except Exception as e:
        logging.info(f"IP address retrieve failed with error: {e}")
        return
        
    # Exclude Test cluster from processing
    try:
        cluster = netbox_host.get("data", {}).get("cluster")
        logging.info(f"Cluster retrieve successfully: {cluster.get('name')}")
        if cluster and "test" in cluster.get("name", "").lower():
            logging.error("VM is in Test cluster, no need to process")
            response = ("HTTP/1.1 400 Bad Request\r\n\r\n")
            client_socket.sendall(response.encode())
            return
    except Exception as e:
        logging.info(f"Error while processing cluster information: {e}")
    
    # Tags set
    try:
        tags_data = netbox_host.get("data", {}).get("tags", [])
        tags = [tag["name"].lower() for tag in tags_data] # Creates array from "name" fields in tag_data dictionary
        logging.info("Tags retrieved successfully")
        # Check if the virtual machine is in an orphaned state (indicating that it will be shut down and should not proceed)
        if "orphaned" in tags: 
            logging.error("VM is in orphaned state, no need to process")
            response = ("HTTP/1.1 400 Bad Request\r\n\r\n")
            client_socket.sendall(response.encode())
            client_socket.close()
            return
    except Exception as e:
        logging.info(f"Tags retrieve failed with error: {e}")
        
    if ip_address and netbox_host.get("data", {}).get("status", {}).get("value").lower() == "active":

        # Check the platform and visible name to assign a template and group
        visible_name = netbox_host.get("data", {}).get("name")
        platform = netbox_host.get("data", {}).get("platform", {}).get("name").lower()

        # Checking for EBAY flag
        if "ebay" in visible_name.lower():
            logging.info("EBAY host, no need for monitoring")
            return 
        
        if "windows" in platform:
            templates.append("Template OS Windows")
            groups.extend(["Allwindows", "Windows General"])
            logging.info("Windows template and groups appended")
        elif any(os in platform for os in linux_fam): 
            templates.append("Template OS Linux")
            groups.append("Linux servers")
            logging.info("Linux template and group appended")
            # Additional check for cPanel mentions in the name to append backup monitoring
            if " cp " in visible_name.lower() or "cpanel" in visible_name.lower() or re.search(r"cp\d{2}", visible_name.lower()):
                templates.append("template cPanel backup")
                groups.append("cPanels")
                logging.info("cPanel template and groups appended")
        else: 
            logging.error(f"There are no matches with the platform type")
            logging.info("Connection closed")
            response = ("HTTP/1.1 422 Unprocessable Entity\r\n\r\n")
            client_socket.sendall(response.encode())
            client_socket.close()
            return       

        # Check extra information in tags to assign templates and groups
        for tag in tags:
            if tag == "uniq": 
                groups.append("Uniq")
                logging.info("Uniq group appended")
            if tag == "cpanel":
                groups.append("cPanels")
                templates.append("template cPanel backup")
                logging.info("cPanel template and group appended")   

        host_name = netbox_host.get("data", {}).get("custom_fields", {}).get("vcsa_vm_guest_hostname")
        logging.info(f"Hostname retrieved successfully")
        location = netbox_host.get("data", {}).get("site", {}).get("name").lower()       

        # Extract the location information and set "proxy" variable
        if ip_address.startswith("172."): 
                    if "pluto-vcenter" in location: 
                        proxy = "62.90.18.89"
                    elif "jupiter-vcenter" in location:
                        proxy = "80.178.113.59"
        else: 
            proxy = ""
            # Check if the IP address exists in Zabbix
        
        logging.info("Start of check_ip_in_zabbix() function")
        zabbix_host = check_ip_in_zabbix(ip_address, client_socket)
        logging.info("End of check_ip_in_zabbix() function")
        
        if zabbix_host is None:
            logging.info("Connection closed due to the error mentioned above")
            client_socket.close()
            return
        elif zabbix_host: 
            # Create a dictionary with NetBox host information
            netbox_host = {
                "hostname": host_name,
                "visiblename": visible_name,
                "ip" : ip_address,
                "templates": templates,
                "groups": groups
            }
            logging.info(f"Zabbix_host = {zabbix_host}")
            logging.info(f"Netbox_host = {netbox_host}")
            # Check if the Zabbix host is up to date
            logging.info("Execution of check_zabbix_accuracy function")
            check_zabbix_accuracy_result = check_zabbix_accuracy(zabbix_host, netbox_host)
            if not check_zabbix_accuracy_result[0]: # changes variable (boolean)
                logging.info(f"Zabbix host \"{netbox_host['visiblename']}\" already exists and up to date")
                return
            else:
                # Update the Zabbix host with new information 
                updated_zabbix_host = check_zabbix_accuracy_result[1] # zabbix_host variable
                templates_change = check_zabbix_accuracy_result[2] # templates_change variable
                groups_change = check_zabbix_accuracy_result[3] # groups_change variable
                
                logging.info("Start of zabbix_update_host() function")
                zabbix_update_host(updated_zabbix_host, templates_change, groups_change)
                return
        else:
            # Create a new host in Zabbix if it doesn't exist
            logging.info("Start of zabbix_create_host() function")
            zabbix_create_host(host_name, visible_name, proxy, ip_address, templates, groups)
            logging.info("End of zabbix_create_host() function")
            logging.info("Connection closed")
            client_socket.close()
            return
    else:
        logging.error("Invalid data format or VM not active")
        return
        # # Send the response back to the client
        # logging.info("Connection closed")
        # client_socket.close()
        # return

# Main function with socket set
def main(): 
    #Listen on port 17777 and open a socket    
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(("0.0.0.0", 17777))
        server_socket.listen(10)
        while True:
            try:
                client_socket, client_addr = server_socket.accept()
                logging.info(f"Connection from {client_addr}")
                try:
                    handle_connection(client_socket)
                except Exception as e:
                    logging.error(f"Error in handle_connection() function: {e}")
                finally:
                    logging.info("Connection closed from handle_connection() function")
                    client_socket.close()             
            except Exception as e:
                logging.error(f"Error in main() function: {e}")
                time.sleep(1)
            # finally:
            #     logging.info("Connection closed from the main() function")
            #     client_socket.close()

# The very start of the script
logging.info("Script starting up...")
if __name__ == '__main__':
    # Zabbix authentication with retries if failed
    logging.info(f"Zabbix authentication start")
    zabbix_authentication_result = zabbix_authentication()        
    if zabbix_authentication_result == True:
        # Zabbix authentication check
        with open("auth/zabbix_auth.txt", "r") as auth_file:
            auth_key = auth_file.read()
    else:
        logging.critical("Script terminated due to previous errors")
        sys.exit(1)

    get_templates_id()
    get_groups_id()
    main()
logging.info("Script shutting down...")

Zabbix Automation Suite
_____________
      Overview
_____________
The Zabbix Automation Suite is a Python-based tool designed to automate the integration and synchronization of host data between Zabbix and NetBox. This suite facilitates the seamless management of host information, ensuring consistency and accuracy across both platforms.

______________
      Features 
______________
# Automated Synchronization: 
Automatically updates Zabbix with the latest host information from NetBox, ensuring data consistency.
# Host Creation and Update: 
Capable of creating new hosts in Zabbix based on data received from NetBox and updating existing hosts if changes are detected.
# Template and Group Management: 
Dynamically assigns templates and groups to hosts in Zabbix based on their platform and other attributes defined in NetBox.
# Error Handling and Logging: 
Robust error handling and detailed logging for easy troubleshooting and maintenance.
# Flexible Platform Support: 
Supports various platforms, including different Linux distributions and Windows, with the ability to extend this support as needed.
________________
      Workflow
________________
# Listening for Data: 
The suite listens on a specified port (default: 17777) for incoming connections.
# Data Reception and Parsing: 
Upon receiving data, it parses the JSON payload to extract host information.
# Data Processing:
Determines if the host exists in Zabbix.
If the host exists, it checks for any discrepancies between NetBox and Zabbix data and updates Zabbix if necessary.
If the host does not exist, it creates a new host entry in Zabbix with the relevant details.
# Template and Group Assignment: 
Based on the platform and other attributes of the host, the suite assigns appropriate templates and groups in Zabbix.
# Logging and Error Handling: 
Throughout the process, the suite logs various activities and errors for monitoring and debugging purposes.
_______________________
      Detailed Functionality
_______________________
# Zabbix Authentication: Authenticates with Zabbix to perform API requests.
# Templates and Groups Retrieval: 
Retrieves template and group IDs from Zabbix for later use.
# Host Check and Update: 
Checks if a given IP address exists in Zabbix and updates host details if there are changes.
# Host Creation: 
If a host does not exist in Zabbix, it triggers an Ansible playbook (zabbix_create_host.yml) to create the host with the specified parameters.
# Error and Exception Management: 
Handles various exceptions and errors gracefully, ensuring the suite continues to operate and logs pertinent information.
_______________________
      Installation and Setup
_______________________
# Prerequisites:
Python 3.x installed with necessary libraries
Access to Zabbix API.
Ansible installed for running playbooks.
Docker with Nginx container or Nginx server itself installed.

# Running the Suite:
1.	Create directory /etc/ ZabbixAutomationSuite
2.	Place to the created directory files: zabbix_hosts.py, zabbix_auth.py, zabbix_create_host.yml, ansible.cfg, nginx.conf
3.	Give execute permissions to .py files with command “chmod +x *.py”
4.	Add your Zabbix username and login to /etc/environment:
ZABBIX_USERNAME=[your username]
ZABBIX_PASSWORD=[your password]
5.	Run command “source /etc/environment”
6.	Copy file zabbix-automation-suite.sevice to /etc/systemd/system/
7.	Run command “systemctl daemon-reload”
8.	Run command “systemctl enable zabbix-automation-suite”
9.	Run command “systemctl start zabbix-automation-suite”
10.	Run Nginx Docker container with command “docker run --network=bridge-network --name webhook-receiver -v /etc/ZabbixAutomationSuite/nginx.conf:/etc/nginx/conf.d/default.conf -d -p 8080:8080 --restart=always nginx”
11.	Enable webhooks in Netbox: 
URL: http://[your-nginx -address]:8080/webhook-receiver
HTTP method: POST
HTTP content type: application/json
Conditions: {"and": [{"attr": "status.value", "value": "active"}, {"op": "contains", "attr": "primary_ip.address", "value": "."}, {"attr": "name", "value": "", "negate": true}, {"attr": "platform.name", "value": "", "negate": true}, {"attr": "custom_fields.VM_hostname", "value": "", "negate": true}]}

# Logging
The suite logs all its operations, including any errors or warnings, to a specified log file (zabbix_automation_suite.log).
Detailed logging aids in monitoring the suite's performance and troubleshooting any issues that arise.
Conclusion
The Zabbix Automation Suite is a powerful tool for organizations using both Zabbix and NetBox, streamlining the process of keeping host data synchronized across these platforms. Its error handling, logging capabilities, and automated processes make it a valuable asset for IT infrastructure management and monitoring.

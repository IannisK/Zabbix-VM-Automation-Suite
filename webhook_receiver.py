#!/usr/bin/env python3

import socket
import logging
import json

logging.basicConfig(filename='logs/webhooks_receiver.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def handle_connection(client_socket):

    # Receive data from NetBox
    netbox_data = client_socket.recv(4096)
    logging.info(netbox_data)
    netbox_data = netbox_data.decode().strip()
    logging.info(netbox_data)
    if "\r\n\r\n" not in netbox_data:
        logging.error("No header-body delimiter found")
        response = "HTTP/1.1 400 Bad Request\r\n\r\n 1"
        client_socket.sendall(response.encode())
        client_socket.close()
        return
    headers, body = netbox_data.split("\r\n\r\n", 1)
    logging.info(body)
    
    if not headers.startswith("POST"):
        logging.error("Received non-POST request")
        response = ("HTTP/1.1 400 Bad Request\r\n\r\n 2")
        client_socket.sendall(response.encode())
        client_socket.close()
        return 
    # Parse data from NetBox
    try:        
        netbox_host = json.loads(body)
        logging.info(netbox_host) 
        logging.info(json.dumps(netbox_host, indent=4))
        logging.info(netbox_data.get("timestamp"))
        logging.info(netbox_data.get("data", {}).get("display"))
    except json.JSONDecodeError:
        logging.error("Invalid JSON data")
        response = ("HTTP/1.1 400 Bad Request\r\n\r\n 3")
        client_socket.sendall(response.encode())
        client_socket.close()
        return

    # Send the response back to the client
    logging.info("Connection closed")
    response = ("HTTP/1.1 200 OK\r\n\r\n")
    client_socket.sendall(response.encode())
    client_socket.close()

def main(): 
    #Listen on port 7777 and open a socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("0.0.0.0", 17777))
    server_socket.listen(10)

    while True:
        client_socket, client_addr = server_socket.accept()
        logging.info(f"Connection from {client_addr}")
        handle_connection(client_socket)


if __name__ == '__main__':
    # Zabbix authentication with retries if failed
    main()

#!/usr/bin/env python3
import re
import json

phrase = {
    "code": -32602,
    "message": "Invalid params.",
    "data": "Host with the same name \\"WIN-7FEJSHG6A4B\\" already exists."
}
phrase = json.loads(phrase)
match = re.search('\\"(.+?)\\"', phrase.get("data"))
print(match)

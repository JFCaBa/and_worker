import bluetooth
import subprocess
import os
import time
import requests
import json
import traceback


class BluetoothServer:
    def __init__(self):
        self.server_sock = None
        self.client_sock = None
        self.wallet_address = None  # Initialize wallet_address as None
        print("Setting up Bluetooth server")


    def start_docker_container(self):
        # Stop the existing container if it's running
        subprocess.run(["docker", "stop", "worker"], stderr=subprocess.DEVNULL)
        subprocess.run(["docker", "rm", "worker"], stderr=subprocess.DEVNULL)

        # Start a new container with the wallet address as an environment variable
        subprocess.run([
            "docker", "run",
            "--name", "worker",
            "-e", f"WALLET_ADDRESS={self.wallet_address}",
            "-d",
            "jfca68/pnd_scanner_worker"
        ])
    
    def update_wifi_settings(self, ssid, psk):
        config_lines = [
            '\nnetwork={',
            f'    ssid="{ssid}"',
            f'    psk="{psk}"',
            '    key_mgmt=WPA-PSK',
            '}'
        ]
        with open('/etc/wpa_supplicant/wpa_supplicant.conf', 'a') as wifi_file:
            wifi_file.writelines('\n'.join(config_lines))
        subprocess.run(['wpa_cli', '-i', 'wlan0', 'reconfigure'])

    def has_internet_connection(self):
        try:
            requests.get("http://www.google.com", timeout=5)
            return True
        except (requests.ConnectionError, requests.Timeout):
            return False
    
    def wait_for_conditions(self):
        while True:
            if self.wallet_address and self.has_internet_connection():
                print("Internet connection available and wallet address received. Starting Docker container.")
                self.start_docker_container()
                break
            elif not self.wallet_address:
                print("\rWaiting for wallet address...     ",end='')
            elif not self.has_internet_connection():
                print("\rWaiting for internet connection...", end='')
            time.sleep(5)  # Check every 5 seconds
    
    def run(self):
        try:
            # Create a new server socket using RFCOMM protocol
            self.server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)

            # Bind to any port
            self.server_sock.bind(("", bluetooth.PORT_ANY))
            self.server_sock.listen(1)

            # Get the port the server socket is listening
            port = self.server_sock.getsockname()[1]

            # Provide a valid UUID for the service
            service_id = "00001101-0000-1000-8000-00805F9B34FB"
            service_name = "My Miner Service"
            service_classes = [service_id, bluetooth.SERIAL_PORT_CLASS]
            profiles = [bluetooth.SERIAL_PORT_PROFILE]
        
            bluetooth.advertise_service(
                self.server_sock, service_name,
                service_id=service_id,
                service_classes=service_classes,
                profiles=profiles
            )

            print(f"Waiting for connection on RFCOMM channel {port}")

            # Accept incoming connections
            self.client_sock, client_info = self.server_sock.accept()
            print(f"Accepted connection from {client_info}")

            # Now you can use self.client_sock to communicate with the connected device
            # Use self.client_sock.recv(size) to read data and self.client_sock.send(data) to send data

            # ... (handle notifications and other logic)

        except Exception as e:
            print(f"An error occurred: {e}")
            traceback.print_exc()  # This will print the detailed traceback

        finally:
            if self.client_sock:
                self.client_sock.close()
            if self.server_sock:
                self.server_sock.close()
            print("Disconnected.")
    
    def handleNotification(self, cHandle, data):
        try:
            data_str = data.decode("utf-8")
            print(f"Received [{data_str}]")

            # Parse data as JSON
            payload = json.loads(data_str)
            hotspot = payload.get("hotspot")
            password = payload.get("password")
            wallet = payload.get("wallet")

            # Update WiFi settings
            if hotspot and password:
                self.update_wifi_settings(hotspot, password)
                print("WiFi settings updated.")

            # Cache wallet address
            if wallet:
                self.wallet_address = wallet
                print(f"Cached wallet address: {self.wallet_address}")

        except json.JSONDecodeError as e:
            print(f"An error occurred: {e.msg}")

if __name__ == "__main__":
    server = BluetoothServer()
    server.run()

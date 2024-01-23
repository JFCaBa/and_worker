import bluetooth
import json
import subprocess
import os
import time
import requests

class BluetoothServer:
    def __init__(self):
        self.server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        self.port = 1
        self.server_sock.bind(("", self.port))
        self.server_sock.listen(1)
        self.wallet_address = None  # Initialize wallet_address as None
        print(f"Waiting for a connection on RFCOMM channel {self.port}")

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
                print("Waiting for wallet address...")
            elif not self.has_internet_connection():
                print("Waiting for internet connection...")
            time.sleep(5)  # Check every 5 seconds
    
    def run(self):
        client_sock, client_info = self.server_sock.accept()
        print("Accepted connection from ", client_info)

        try:
            data = client_sock.recv(1024)  # Adjust the buffer size if necessary
            if data:
                print(f"Received [{data}]")

                # Parse data as JSON
                try:
                    payload = json.loads(data.decode("utf-8"))
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

                    # Check conditions and act accordingly
                    self.wait_for_conditions()

                except json.JSONDecodeError as e:
                    print(f"An error occurred: {e.msg}")
        except OSError:
            pass

        print("Disconnected.")
        client_sock.close()

    def __del__(self):
        self.server_sock.close()

if __name__ == "__main__":
    server = BluetoothServer()
    server.run()

from bluepy import btle
import json
import subprocess
import os
import time
import requests


class BluetoothServer:
    def __init__(self):
        self.peripheral = None
        self.wallet_address = None  # Initialize wallet_address as None
        adv_data = btle.AdvertisingData()
        adv_data.setCompleteLocalName("Raspberry Pi")
        self.peripheral.advertise(adv_data, interval_ms=1000)

        print("Waiting for a Bluetooth connection")

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
            self.peripheral = btle.Peripheral()
            self.peripheral.setDelegate(self)

            print("Scanning for devices...")
            scanner = btle.Scanner()
            devices = scanner.scan(10)  # Scan for 10 seconds (adjust as needed)

            for device in devices:
                # Check if the device has a name and matches a specific name or MAC address
                if device.getValueText(btle.ScanEntry.COMPLETE_LOCAL_NAME) == "iPhone" or device.addr == "00:11:22:33:44:55":
                    print(f"Connecting to {device.addr}...")
                    self.peripheral.connect(device.addr)
                    break

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

        except KeyboardInterrupt:
            pass
        finally:
            if self.peripheral:
                self.peripheral.disconnect()
    
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

#!/bin/bash
export WS_URI='ws://onedayvpn.com:5001'
export WALLET_ADDRESS='123456'
for i in {1..5}; do
    python miner/main.py & 
done

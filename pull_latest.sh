#!/bin/bash

# Pull the latest image
docker pull jfca68/miner:vps

# Stop and remove the existing worker container (if it exists)
docker stop miner || true
docker rm miner || true

# Run the new worker container
docker run -d --name miner -e "WS_URI=ws://onedayvpn.com:5001" -e "WALLET_ADDRESS=123456" jfca68/miner:vps

# Check if Watchtower is running, and only run if it's not
if [ ! "$(docker ps -q -f name=watchtower)" ]; then
    if [ "$(docker ps -aq -f status=exited -f name=watchtower)" ]; then
        # Cleanup
        docker rm watchtower
    fi
    # Run Watchtower
    docker run -d --name watchtower -v /var/run/docker.sock:/var/run/docker.sock -e WATCHTOWER_POLL_INTERVAL=300 containrrr/watchtower miner:vps

fi

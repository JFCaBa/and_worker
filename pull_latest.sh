#!/bin/bash

# Pull the latest image
docker pull jfca68/pnd_scanner_worker:latest

# Stop and remove the existing worker container (if it exists)
docker stop worker || true
docker rm worker || true

# Run the new worker container
docker run --name worker -d jfca68/pnd_scanner_worker:latest

# Check if Watchtower is running, and only run if it's not
if [ ! "$(docker ps -q -f name=watchtower)" ]; then
    if [ "$(docker ps -aq -f status=exited -f name=watchtower)" ]; then
        # Cleanup
        docker rm watchtower
    fi
    # Run Watchtower
    docker run -d --name watchtower -v /var/run/docker.sock:/var/run/docker.sock containrrr/watchtower
fi

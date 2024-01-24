# Use an official Python runtime as a parent image
FROM python:3.8-slim

# Set the working directory in the container to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install build dependencies (example for Debian/Ubuntu-based images)
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    python3-dev \
&& rm -rf /var/lib/apt/lists/*

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Set fixed WS_URI as an environment variable
ENV WS_URI=ws://onedayvpn.com:5001

# Set a placeholder for WALLET_ADDRESS which will be provided at runtime
ENV WALLET_ADDRESS=

# Run main.py when the container launches
CMD ["python", "./main.py"]

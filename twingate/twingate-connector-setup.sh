#!/bin/bash
set -e

# Install Twingate connector
curl -s https://binaries.twingate.com/connector/setup.sh | sudo bash

# Configure connector
sudo tee /etc/twingate/connector.conf > /dev/null <<EOL
TWINGATE_ACCESS_TOKEN=${ACCESS_TOKEN}
TWINGATE_REFRESH_TOKEN=${REFRESH_TOKEN}
TWINGATE_NETWORK=${NETWORK}
TWINGATE_LOG_ANALYTICS=v2
TWINGATE_LABEL_DEPLOYED_BY=terraform
EOL

# Enable and start service
sudo systemctl enable twingate-connector
sudo systemctl start twingate-connector
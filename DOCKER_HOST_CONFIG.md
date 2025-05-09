# Docker Host Configuration Guide

This guide explains how to configure Docker to listen on both the Unix socket and TCP port 2375, allowing remote access to your Docker daemon.

## Security Warning

**IMPORTANT**: Exposing Docker on TCP without TLS encryption is a security risk. Port 2375 is the unencrypted Docker port. For production environments, you should use port 2376 with TLS certificates instead.

Only use this configuration in a secure environment where you trust all users on the network.

## Configuration Methods

There are two ways to configure the Docker host:

1. **Using the provided script** (recommended)
2. **Manual configuration**

## Method 1: Using the Provided Script

We've created a script that automates the configuration process:

```bash
# Make the script executable
chmod +x docker-daemon-config.sh

# Run the script as root
sudo ./docker-daemon-config.sh
```

The script will:
- Create or update the Docker daemon configuration file
- Configure systemd if needed
- Restart the Docker service
- Update firewall rules if necessary

After running the script, you can verify the configuration:

```bash
chmod +x verify-docker-host.sh
./verify-docker-host.sh
```

## Method 2: Manual Configuration

If you prefer to configure Docker manually, follow these steps:

### Step 1: Create/Edit the Docker daemon configuration file

Create or edit the file `/etc/docker/daemon.json`:

```bash
sudo mkdir -p /etc/docker
sudo nano /etc/docker/daemon.json
```

Add the following content:

```json
{
  "hosts": ["unix:///var/run/docker.sock", "tcp://0.0.0.0:2375"]
}
```

### Step 2: Update systemd configuration (if using systemd)

Create a systemd override directory:

```bash
sudo mkdir -p /etc/systemd/system/docker.service.d
```

Create an override file:

```bash
sudo nano /etc/systemd/system/docker.service.d/override.conf
```

Add the following content:

```
[Service]
ExecStart=
ExecStart=/usr/bin/dockerd
```

Reload systemd configuration:

```bash
sudo systemctl daemon-reload
```

### Step 3: Restart Docker service

```bash
sudo systemctl restart docker
```

### Step 4: Configure firewall (if needed)

For UFW:
```bash
sudo ufw allow 2375/tcp
```

For FirewallD:
```bash
sudo firewall-cmd --permanent --add-port=2375/tcp
sudo firewall-cmd --reload
```

## Verifying the Configuration

To verify that Docker is listening on TCP port 2375:

```bash
# Check if the port is open
sudo netstat -tuln | grep 2375

# Test connection to local Docker daemon over TCP
export DOCKER_HOST=tcp://localhost:2375
docker info

# Restore default Docker host
unset DOCKER_HOST
```

## Connecting from Remote Machines

From another machine, you can connect to your Docker daemon using:

```bash
# Replace YOUR_SERVER_IP with your server's IP address
docker -H tcp://YOUR_SERVER_IP:2375 info
```

Or set the DOCKER_HOST environment variable:

```bash
export DOCKER_HOST=tcp://YOUR_SERVER_IP:2375
docker info
```

## Troubleshooting

### Docker service fails to start

Check the Docker service logs:

```bash
sudo journalctl -u docker
```

Common issues:
- Syntax error in daemon.json
- Port 2375 already in use
- Insufficient permissions

### Cannot connect from remote machine

Check the following:
- Firewall settings on the server
- Network connectivity between machines
- Docker service is running
- Docker is listening on the correct interface

## Reverting Changes

To revert to the default configuration:

1. Remove or update the daemon.json file:
```bash
sudo rm /etc/docker/daemon.json
# or
sudo nano /etc/docker/daemon.json
# Remove the "hosts" line or the entire file
```

2. Remove the systemd override:
```bash
sudo rm -rf /etc/systemd/system/docker.service.d
sudo systemctl daemon-reload
```

3. Restart Docker:
```bash
sudo systemctl restart docker
```

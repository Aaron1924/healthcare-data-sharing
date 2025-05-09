# External Access to Healthcare Data Sharing System

This document provides instructions for setting up and accessing the Healthcare Data Sharing application from external machines.

## Server Setup (Host Machine)

### 1. Configure Firewall

Ensure your firewall allows incoming connections on the following ports:

- **8501**: Streamlit Web UI
- **8000**: FastAPI Backend
- **5001**: IPFS API
- **8080**: IPFS Gateway
- **4001**: IPFS Swarm (optional, for IPFS network connectivity)

#### Windows Firewall

1. Open Windows Defender Firewall with Advanced Security
2. Select "Inbound Rules" and click "New Rule..."
3. Select "Port" and click "Next"
4. Select "TCP" and enter the ports: "8501, 8000, 5001, 8080, 4001"
5. Select "Allow the connection" and click "Next"
6. Select the network types (Domain, Private, Public) and click "Next"
7. Name the rule (e.g., "Healthcare Data Sharing") and click "Finish"

#### Linux (UFW)

```bash
sudo ufw allow 8501/tcp
sudo ufw allow 8000/tcp
sudo ufw allow 5001/tcp
sudo ufw allow 8080/tcp
sudo ufw allow 4001/tcp
sudo ufw reload
```

### 2. Find Your IP Address

You need to know your machine's IP address to share with others:

#### Windows

```bash
ipconfig
```

Look for the IPv4 Address under your active network adapter.

#### Linux

```bash
ip addr show
```

Look for the inet address under your active network adapter.

### 3. Start the Docker Containers

```bash
./docker-setup.sh start
```

## Client Access (External Users)

External users can access the system using the following URLs (replace `YOUR_SERVER_IP` with the actual IP address of the server):

- **Web UI**: `http://YOUR_SERVER_IP:8501`
- **API Documentation**: `http://YOUR_SERVER_IP:8000/docs`
- **IPFS Gateway**: `http://YOUR_SERVER_IP:8080/ipfs/[CID]`
- **IPFS WebUI**: `http://YOUR_SERVER_IP:5001/webui`

## Security Considerations

### 1. Authentication

The current setup does not include authentication for external access. For production use, consider adding:

- API authentication (JWT, OAuth, etc.)
- Web UI authentication
- HTTPS for encrypted connections

### 2. Network Security

For better security:

- Use a reverse proxy (like Nginx) with HTTPS
- Set up proper authentication
- Consider using a VPN for sensitive deployments
- Limit access to specific IP addresses

### 3. Docker Network Configuration

The Docker Compose file has been configured to bind services to all network interfaces (0.0.0.0) to allow external access. This means:

- Services are accessible from any network interface on the host
- External users can connect if the host's firewall allows it
- The Docker internal network still provides isolation between containers

## Troubleshooting

### 1. Connection Issues

If external users cannot connect:

1. Verify the Docker containers are running:
   ```bash
   docker ps
   ```

2. Check that services are bound to 0.0.0.0:
   ```bash
   docker exec healthcare-api netstat -tulpn | grep 8000
   docker exec healthcare-web netstat -tulpn | grep 8501
   ```

3. Verify firewall settings:
   ```bash
   # Windows
   netsh advfirewall firewall show rule name="Healthcare Data Sharing"
   
   # Linux
   sudo ufw status
   ```

4. Test local access first:
   ```bash
   curl http://localhost:8000/docs
   ```

### 2. IPFS Connection Issues

If IPFS is not accessible externally:

1. Check IPFS configuration:
   ```bash
   docker exec ipfs-node ipfs config Addresses.API
   ```
   It should show `/ip4/0.0.0.0/tcp/5001`

2. Restart the IPFS container:
   ```bash
   docker-compose restart ipfs
   ```

## Advanced: Using a Domain Name

For easier access, you can set up a domain name pointing to your server:

1. Register a domain name or use a dynamic DNS service
2. Configure DNS records to point to your server's IP address
3. Set up a reverse proxy (like Nginx) to route traffic based on subdomains

Example Nginx configuration:

```nginx
server {
    listen 80;
    server_name app.yourdomain.com;
    
    location / {
        proxy_pass http://localhost:8501;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

server {
    listen 80;
    server_name api.yourdomain.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

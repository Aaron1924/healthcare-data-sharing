#!/usr/bin/env python3
import os
import sys
import subprocess
import time
import argparse
import signal
import atexit

# Global variables to track processes
processes = []

def cleanup():
    """Kill all processes on exit"""
    for process in processes:
        try:
            process.terminate()
            print(f"Terminated process {process.pid}")
        except:
            pass

# Register cleanup function
atexit.register(cleanup)

def signal_handler(sig, frame):
    """Handle Ctrl+C"""
    print("Shutting down...")
    cleanup()
    sys.exit(0)

# Register signal handler
signal.signal(signal.SIGINT, signal_handler)

def run_command(command, cwd=None):
    """Run a command and return the process"""
    process = subprocess.Popen(
        command,
        shell=True,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )
    processes.append(process)
    return process

def check_ipfs():
    """Check if IPFS is running"""
    try:
        import ipfshttpclient
        client = ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001')
        return True
    except:
        return False

def start_ipfs():
    """Start IPFS daemon using Docker"""
    print("Starting IPFS daemon...")
    if check_ipfs():
        print("IPFS is already running")
        return True
    
    # Check if Docker is available
    docker_process = run_command("docker --version")
    docker_process.wait()
    if docker_process.returncode != 0:
        print("Docker is not available. Please install Docker or start IPFS manually.")
        return False
    
    # Check if IPFS container is already running
    docker_ps = run_command("docker ps -q -f name=ipfs-node")
    container_id = docker_ps.communicate()[0].strip()
    
    if container_id:
        print(f"IPFS container is already running with ID: {container_id}")
    else:
        # Check if container exists but is stopped
        docker_ps = run_command("docker ps -aq -f name=ipfs-node")
        container_id = docker_ps.communicate()[0].strip()
        
        if container_id:
            print(f"Starting existing IPFS container with ID: {container_id}")
            start_process = run_command(f"docker start {container_id}")
            start_process.wait()
        else:
            # Create and start a new container
            print("Creating and starting new IPFS container...")
            run_process = run_command(
                "docker run -d --name ipfs-node -v ipfs-data:/data/ipfs -p 4001:4001 -p 8080:8080 -p 5001:5001 ipfs/kubo"
            )
            run_process.wait()
    
    # Wait for IPFS to start
    print("Waiting for IPFS to start...")
    max_attempts = 10
    for i in range(max_attempts):
        if check_ipfs():
            print("IPFS is running")
            return True
        print(f"Waiting for IPFS to start ({i+1}/{max_attempts})...")
        time.sleep(2)
    
    print("Failed to start IPFS")
    return False

def start_backend():
    """Start the backend server"""
    print("Starting backend server...")
    backend_process = run_command("python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000")
    
    # Wait for backend to start
    print("Waiting for backend to start...")
    max_attempts = 10
    for i in range(max_attempts):
        try:
            import requests
            response = requests.get("http://localhost:8000/api/health")
            if response.status_code == 200:
                print("Backend is running")
                return True
        except:
            pass
        print(f"Waiting for backend to start ({i+1}/{max_attempts})...")
        time.sleep(2)
    
    print("Failed to start backend")
    return False

def start_frontend():
    """Start the frontend server"""
    print("Starting frontend server...")
    frontend_process = run_command("streamlit run app/main.py")
    
    # Wait for frontend to start
    print("Waiting for frontend to start...")
    max_attempts = 10
    for i in range(max_attempts):
        try:
            import requests
            response = requests.get("http://localhost:8501")
            if response.status_code == 200:
                print("Frontend is running")
                return True
        except:
            pass
        print(f"Waiting for frontend to start ({i+1}/{max_attempts})...")
        time.sleep(2)
    
    print("Failed to start frontend")
    return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Run the Healthcare Data Sharing application")
    parser.add_argument("--no-ipfs", action="store_true", help="Don't start IPFS daemon")
    parser.add_argument("--backend-only", action="store_true", help="Start only the backend server")
    parser.add_argument("--frontend-only", action="store_true", help="Start only the frontend server")
    args = parser.parse_args()
    
    # Start IPFS if needed
    if not args.no_ipfs and not args.frontend_only:
        if not start_ipfs():
            return 1
    
    # Start backend if needed
    if not args.frontend_only:
        if not start_backend():
            return 1
    
    # Start frontend if needed
    if not args.backend_only:
        if not start_frontend():
            return 1
    
    print("\nAll services are running!")
    print("- Backend: http://localhost:8000")
    print("- Frontend: http://localhost:8501")
    print("- IPFS: http://localhost:5001/webui")
    print("\nPress Ctrl+C to stop all services")
    
    # Keep the script running
    try:
        while True:
            # Check if any process has terminated
            for process in processes:
                if process.poll() is not None:
                    print(f"Process {process.pid} has terminated with code {process.returncode}")
                    processes.remove(process)
            
            # If all processes have terminated, exit
            if not processes:
                print("All processes have terminated")
                return 0
            
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
        cleanup()
        return 0

if __name__ == "__main__":
    sys.exit(main())

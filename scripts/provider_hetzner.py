#!/usr/bin/env python3
import os
import sys
import requests
import json
import time

HETZNER_API_URL = "https://api.hetzner.cloud/v1"

def get_token():
    # Load from .env or environment
    if os.path.exists(".env"):
        with open(".env") as f:
            for line in f:
                if line.startswith("HCLOUD_TOKEN="):
                    return line.strip().split("=")[1]
    return os.getenv("HCLOUD_TOKEN")

def hetzner_post(endpoint, data, token):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    response = requests.post(f"{HETZNER_API_URL}/{endpoint}", json=data, headers=headers)
    return response.json()

def hetzner_get(endpoint, token):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{HETZNER_API_URL}/{endpoint}", headers=headers)
    return response.json()

def setup_ssh_key(token):
    pub_key_path = os.path.expanduser("~/.ssh/id_ed25519.pub")
    if not os.path.exists(pub_key_path):
        print("SSH public key not found.")
        return None
    
    with open(pub_key_path) as f:
        pub_key = f.read().strip()
    
    # Check if key already exists
    keys = hetzner_get("ssh_keys", token)
    for k in keys.get("ssh_keys", []):
        if k["public_key"].split()[1] == pub_key.split()[1]:
            return k["id"]
    
    # Upload new key
    data = {
        "name": f"agent-key-{int(time.time())}",
        "public_key": pub_key
    }
    res = hetzner_post("ssh_keys", data, token)
    return res.get("ssh_key", {}).get("id")

def create_server(token, ssh_key_id):
    # Optimized for 2026: CAX11 (ARM64) is cost-effective
    data = {
        "name": f"agent-node-{int(time.time())}",
        "server_type": "cax11",
        "image": "ubuntu-24.04",
        "location": "nbg1", # Nuremberg
        "ssh_keys": [ssh_key_id]
    }
    res = hetzner_post("servers", data, token)
    if "error" in res:
        print(f"Error creating server: {res['error']}")
        return None
    return res["server"]["id"]

def wait_for_server(token, server_id):
    print(f"Waiting for server {server_id} to be ready...")
    while True:
        res = hetzner_get(f"servers/{server_id}", token)
        status = res.get("server", {}).get("status")
        if status == "running":
            ip = res["server"]["public_net"]["ipv4"]["ip"]
            return ip
        elif status == "off":
             # Try to power on if it's off
             hetzner_post(f"servers/{server_id}/actions/poweron", {}, token)
        
        time.sleep(5)

if __name__ == "__main__":
    token = get_token()
    if not token:
        print("Error: HCLOUD_TOKEN not found.")
        sys.exit(1)
    
    key_id = setup_ssh_key(token)
    if not key_id:
        print("Error: Failed to setup SSH key.")
        sys.exit(1)
    
    server_id = create_server(token, key_id)
    if server_id:
        ip = wait_for_server(token, server_id)
        print(f"SUCCESS: Server is ready at {ip}")
        # Save to a state file
        with open("server_state.json", "w") as f:
            json.dump({"server_id": server_id, "ip": ip}, f)

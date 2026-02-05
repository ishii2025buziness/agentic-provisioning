#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import axios from 'axios';
import dotenv from 'dotenv';
import { os } from 'node:os';

dotenv.config();

const HETZNER_API_URL = "https://api.hetzner.cloud/v1";

async function get_token() {
    return process.env.HCLOUD_TOKEN;
}

const client = (token) => axios.create({
    baseURL: HETZNER_API_URL,
    headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json"
    }
});

async function setup_ssh_key(token) {
    const pubKeyPath = path.join(process.env.HOME || process.env.USERPROFILE, '.ssh', 'id_ed25519.pub');
    if (!fs.existsSync(pubKeyPath)) {
        console.error("SSH public key not found at " + pubKeyPath);
        return null;
    }

    const pubKey = fs.readFileSync(pubKeyPath, 'utf8').trim();
    const c = client(token);

    // Check if key already exists
    const keysRes = await c.get('ssh_keys');
    const existingKey = keysRes.data.ssh_keys.find(k => k.public_key.split(' ')[1] === pubKey.split(' ')[1]);

    if (existingKey) {
        return existingKey.id;
    }

    // Upload new key
    const res = await c.post('ssh_keys', {
        name: `agent-key-${Date.now()}`,
        public_key: pubKey
    });
    return res.data.ssh_key.id;
}

async function create_server(token, sshKeyId) {
    const c = client(token);
    try {
        const res = await c.post('servers', {
            name: `agent-node-${Date.now()}`,
            server_type: "cax11",
            image: "ubuntu-24.04",
            location: "nbg1",
            ssh_keys: [sshKeyId]
        });
        return res.data.server.id;
    } catch (error) {
        console.error("Error creating server:", error.response?.data || error.message);
        return null;
    }
}

async function wait_for_server(token, serverId) {
    const c = client(token);
    console.log(`Waiting for server ${serverId} to be ready...`);
    while (true) {
        const res = await c.get(`servers/${serverId}`);
        const status = res.data.server.status;
        if (status === "running") {
            return res.data.server.public_net.ipv4.ip;
        } else if (status === "off") {
            await c.post(`servers/${serverId}/actions/poweron`);
        }
        await new Promise(resolve => setTimeout(resolve, 5000));
    }
}

async function main() {
    const token = await get_token();
    if (!token) {
        console.error("Error: HCLOUD_TOKEN not found in .env or environment.");
        process.exit(1);
    }

    const keyId = await setup_ssh_key(token);
    if (!keyId) {
        console.error("Error: Failed to setup SSH key.");
        process.exit(1);
    }

    const serverId = await create_server(token, keyId);
    if (serverId) {
        const ip = await wait_for_server(token, serverId);
        console.log(`SUCCESS: Server is ready at ${ip}`);
        fs.writeFileSync("server_state.json", JSON.stringify({ server_id: serverId, ip: ip }, null, 2));
    }
}

main().catch(err => {
    console.error(err);
    process.exit(1);
});

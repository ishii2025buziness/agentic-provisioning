#!/usr/bin/env node
import fs from 'node:fs';
import { execSync } from 'node:child_process';

/**
 * Deploy Stack to Hetzner
 * 1. Read server state
 * 2. Rsync files to server
 * 3. Setup remote environment
 */
async function deploy() {
    if (!fs.existsSync('server_state.json')) {
        console.error("Error: server_state.json not found. Run 'npm run hetzner' first.");
        process.exit(1);
    }

    const { ip } = JSON.parse(fs.readFileSync('server_state.json'));
    console.log(`[Deploy] Target: root@${ip}`);

    try {
        // Step 1: Sync files (excluding node_modules)
        console.log("[Deploy] Syncing files via rsync...");
        execSync(`rsync -avz --exclude 'node_modules' --exclude '.git' ./ root@${ip}:~/app/`, { stdio: 'inherit' });

        // Step 2: Setup Remote (Install Node.js & Dependencies)
        console.log("[Deploy] Setting up remote environment...");
        const remoteCmd = `
            curl -fsSL https://deb.nodesource.com/setup_20.x | bash - &&
            apt-get install -y nodejs &&
            cd ~/app &&
            npm install &&
            npm install -g pm2 &&
            pm2 delete x-collector || true &&
            pm2 start scripts/collector_x_apify.js --name x-collector -- --interval 3600
        `;
        execSync(`ssh -o StrictHostKeyChecking=no root@${ip} "${remoteCmd}"`, { stdio: 'inherit' });

        console.log(`\n[SUCCESS] Deployed to ${ip}!`);
        console.log(`The collector is now running in the background on Hetzner.`);
        console.log(`You can turn off your local PC now.`);
    } catch (error) {
        console.error("[Deploy] Failed:", error.message);
    }
}

deploy();

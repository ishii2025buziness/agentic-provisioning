#!/usr/bin/env node
import fs from 'node:fs';
import axios from 'axios';
import dotenv from 'dotenv';

dotenv.config();

const APIFY_API_URL = "https://api.apify.com/v2";

async function get_token() {
    return process.env.APIFY_API_TOKEN;
}

/**
 * X (Twitter) Data Collector - Full Coverage Edition
 * Modes:
 * 1. 'search'   - Query based (Advanced search supported)
 * 2. 'user'     - Fetch tweets from specific handles
 * 3. 'list'     - Fetch context from a specific X List (URL required)
 * 4. 'profile'  - Fetch metadata for specific handles
 * 5. 'url'      - Direct URL scraping (specific tweets, searches, or profiles)
 */
async function run_twitter_scraper(token, options = {}) {
    const {
        mode = 'search',
        query = '',
        handles = [],
        urls = [], // For 'list' or 'url' modes
        maxTweets = 10,
        actorId = "apify~twitter-scraper-v2"
    } = options;

    console.log(`[X-Collector] Mode: ${mode.toUpperCase()} | Max Items: ${maxTweets}`);

    let runInput = {
        maxTweets: maxTweets,
        addUserInfo: true,
        sort: "Latest" // Default to latest for polling accuracy
    };

    // Advanced Polymorphic Input Mapping
    if (mode === 'search') {
        runInput.searchTerms = Array.isArray(query) ? query : [query];
    } else if (mode === 'user') {
        runInput.twitterHandles = Array.isArray(handles) ? handles : [handles];
    } else if (mode === 'list' || mode === 'url') {
        runInput.startUrls = (Array.isArray(urls) ? urls : [urls]).map(u => ({ url: u }));
    } else if (mode === 'profile') {
        runInput.twitterHandles = Array.isArray(handles) ? handles : [handles];
        runInput.scrapeProfile = true;
    }

    try {
        const runRes = await axios.post(`${APIFY_API_URL}/acts/${actorId}/runs?token=${token}`, runInput);
        const runId = runRes.data.data.id;
        const datasetId = runRes.data.data.defaultDatasetId;

        console.log(`[X-Collector] Run started: ${runId}. Polling latest posts...`);

        // Polling loop
        while (true) {
            const statusRes = await axios.get(`${APIFY_API_URL}/acts/${actorId}/runs/${runId}?token=${token}`);
            const { status } = statusRes.data.data;

            if (status === "SUCCEEDED") break;
            if (["FAILED", "ABORTED", "TIMED-OUT"].includes(status)) {
                throw new Error(`Apify Actor failed with status: ${status}`);
            }
            await new Promise(resolve => setTimeout(resolve, 5000));
        }

        console.log("[X-Collector] Fetching results...");
        const itemsRes = await axios.get(`${APIFY_API_URL}/datasets/${datasetId}/items?token=${token}`);
        return itemsRes.data;

    } catch (error) {
        console.error("[X-Collector] Error:", error.response?.data || error.message);
        return null;
    }
}

async function main() {
    const token = await get_token();
    if (!token) {
        console.error("Error: APIFY_API_TOKEN not found.");
        process.exit(1);
    }

    // Read Mission from config.json
    let config = { mission: { mode: 'search', query: 'AI Agents 2026', maxTweets: 10 } };
    const configPath = 'config.json';
    const vaultPath = 'vault/x_vault.jsonl';
    const latestPath = 'x_data_latest.json';

    if (!fs.existsSync('vault')) fs.mkdirSync('vault');

    try {
        if (fs.existsSync(configPath)) {
            config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
        }
    } catch (e) {
        console.error("Error reading config.json, using defaults.");
    }

    console.log(`[X-Collector] Starting mission: ${JSON.stringify(config.mission)}`);
    const results = await run_twitter_scraper(token, config.mission);

    if (results && results.length > 0) {
        // Load existing IDs for deduplication
        const existingIds = new Set();
        if (fs.existsSync(vaultPath)) {
            const lines = fs.readFileSync(vaultPath, 'utf8').split('\n').filter(Boolean);
            lines.forEach(line => {
                try {
                    const tweet = JSON.parse(line);
                    if (tweet.id) existingIds.add(tweet.id);
                } catch (e) { }
            });
        }

        // Filter new items
        const newItems = results.filter(item => !existingIds.has(item.id));
        console.log(`[X-Collector] Found ${results.length} items. New unique items: ${newItems.length}`);

        if (newItems.length > 0) {
            // Append to Vault (Deduplicated Data Store)
            const stream = fs.createWriteStream(vaultPath, { flags: 'a' });
            newItems.forEach(item => {
                stream.write(JSON.stringify(item) + '\n');
            });
            stream.end();
            console.log(`[X-Collector] Appended ${newItems.length} new items to vault.`);
        }

        // Still update the "latest" for dashboard preview
        fs.writeFileSync(latestPath, JSON.stringify(results.slice(0, 20), null, 2));

        // Update metadata
        config.settings = config.settings || {};
        config.settings.last_run = new Date().toISOString();
        config.settings.total_stored = (existingIds.size + newItems.length);
        fs.writeFileSync(configPath, JSON.stringify(config, null, 2));

        // Trigger Cloud Sync if configured
        try {
            console.log("[X-Collector] Triggering Cloud Backup...");
            const { execSync } = await import('node:child_process');
            execSync('node scripts/cloud_sync.js', { stdio: 'inherit' });
        } catch (e) {
            console.error("[X-Collector] Cloud Backup failed or not configured.");
        }
    }
}

main().catch(err => {
    console.error(err);
    process.exit(1);
});

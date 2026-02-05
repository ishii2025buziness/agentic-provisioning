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
 * X (Twitter) Data Collector
 * Modes:
 * 1. 'search' - Query based search (Advanced queries supported)
 * 2. 'user'   - Fetch tweets from specific handles
 * 3. 'profile'- Fetch metadata for specific handles
 */
async function run_twitter_scraper(token, options = {}) {
    const {
        mode = 'search',
        query = 'AI Agents 2026',
        handles = [],
        maxTweets = 10,
        actorId = "apify~twitter-scraper-v2"
    } = options;

    console.log(`[X-Collector] Mode: ${mode} | Max Items: ${maxTweets}`);

    // Prepare Input based on mode
    let runInput = {
        maxTweets: maxTweets,
        addUserInfo: true
    };

    if (mode === 'search') {
        runInput.searchQueries = Array.isArray(query) ? query : [query];
    } else if (mode === 'user' || mode === 'profile') {
        runInput.twitterHandles = Array.isArray(handles) ? handles : [handles];
        if (mode === 'profile') runInput.scrapeProfile = true;
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

    // Example: Time-series search for specific keywords
    const results = await run_twitter_scraper(token, {
        mode: 'search',
        query: 'AI Agents 2026 lang:ja',
        maxTweets: 5
    });

    if (results) {
        console.log(`[SUCCESS] Collected ${results.length} items.`);
        const filename = `x_data_${Date.now()}.json`;
        fs.writeFileSync(filename, JSON.stringify(results, null, 2));
        console.log(`Data saved to ${filename}`);
    }
}

main().catch(err => {
    console.error(err);
    process.exit(1);
});

#!/usr/bin/env node
import fs from 'node:fs';
import axios from 'axios';
import dotenv from 'dotenv';

dotenv.config();

const APIFY_API_URL = "https://api.apify.com/v2";

async function get_token() {
    return process.env.APIFY_API_TOKEN;
}

async function run_twitter_scraper(token, query, maxTweets = 10) {
    // Current stable public actor slug
    const actorId = "apify~twitter-scraper-v2";

    console.log(`Starting Apify Actor ${actorId} for query: ${query}...`);

    try {
        const runRes = await axios.post(`${APIFY_API_URL}/acts/${actorId}/runs?token=${token}`, {
            searchQueries: [query],
            maxTweets: maxTweets,
            addUserInfo: true
        });

        const runId = runRes.data.data.id;
        const datasetId = runRes.data.data.defaultDatasetId;

        console.log(`Run started: ${runId}. Waiting for completion...`);

        while (true) {
            const statusRes = await axios.get(`${APIFY_API_URL}/acts/${actorId}/runs/${runId}?token=${token}`);
            const status = statusRes.data.data.status;

            if (status === "SUCCEEDED") break;
            if (["FAILED", "ABORTED", "TIMED-OUT"].includes(status)) {
                console.error(`Actor run failed with status: ${status}`);
                return null;
            }
            await new Promise(resolve => setTimeout(resolve, 10000));
        }

        console.log("Fetching results from dataset...");
        const itemsRes = await axios.get(`${APIFY_API_URL}/datasets/${datasetId}/items?token=${token}`);
        return itemsRes.data;

    } catch (error) {
        console.error("Error with Apify API:", error.response?.data || error.message);
        return null;
    }
}

async function main() {
    const token = await get_token();
    if (!token) {
        console.error("Error: APIFY_API_TOKEN not found.");
        process.exit(1);
    }

    const results = await run_twitter_scraper(token, "AI Agents 2026");
    if (results) {
        console.log(`SUCCESS: Collected ${results.length} tweets.`);
        fs.writeFileSync("collected_tweets_sample.json", JSON.stringify(results, null, 2));
        console.log("Sample data saved to collected_tweets_sample.json");
    }
}

main().catch(err => {
    console.error(err);
    process.exit(1);
});

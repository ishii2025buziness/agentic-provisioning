#!/usr/bin/env python3
import os
import sys
import requests
import json
import time

APIFY_API_URL = "https://api.apify.com/v2"

def get_token():
    if os.path.exists(".env"):
        with open(".env") as f:
            for line in f:
                if line.startswith("APIFY_API_TOKEN="):
                    return line.strip().split("=")[1]
    return os.getenv("APIFY_API_TOKEN")

def run_twitter_scraper(token, query, max_tweets=10):
    # Using 'apify~twitter-scraper'
    actor_id = "apify~twitter-scraper"
    
    run_input = {
        "searchQueries": [query],
        "maxTweets": max_tweets,
        "addUserInfo": True
    }
    
    print(f"Starting Apify Actor {actor_id} for query: {query}...")
    headers = {"Content-Type": "application/json"}
    start_url = f"{APIFY_API_URL}/acts/{actor_id}/runs?token={token}"
    
    res = requests.post(start_url, json=run_input, headers=headers)
    run_data = res.json()
    
    if "error" in run_data:
        print(f"Error starting Actor: {run_data['error']}")
        return None
    
    run_id = run_data["data"]["id"]
    dataset_id = run_data["data"]["defaultDatasetId"]
    
    print(f"Run started: {run_id}. Waiting for completion...")
    
    # Poll for completion
    while True:
        status_url = f"{APIFY_API_URL}/acts/{actor_id}/runs/{run_id}?token={token}"
        status_res = requests.get(status_url)
        status_data = status_res.json()
        
        status = status_data["data"]["status"]
        if status == "SUCCEEDED":
            break
        elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
            print(f"Actor run failed with status: {status}")
            return None
        
        time.sleep(10)
    
    # Fetch results
    print("Fetching results from dataset...")
    items_url = f"{APIFY_API_URL}/datasets/{dataset_id}/items?token={token}"
    items_res = requests.get(items_url)
    return items_res.json()

if __name__ == "__main__":
    token = get_token()
    if not token:
        print("Error: APIFY_API_TOKEN not found.")
        sys.exit(1)
    
    results = run_twitter_scraper(token, "AI Agents 2026")
    if results:
        print(f"SUCCESS: Collected {len(results)} tweets.")
        with open("collected_tweets_sample.json", "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print("Sample data saved to collected_tweets_sample.json")

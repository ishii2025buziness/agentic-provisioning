import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";
import fs from "node:fs";
import dotenv from "dotenv";

dotenv.config();

/**
 * Sync Local Vault to Cloud Storage (R2/S3)
 */
async function syncToCloud() {
    const {
        R2_ACCOUNT_ID,
        R2_ACCESS_KEY_ID,
        R2_SECRET_ACCESS_KEY,
        R2_BUCKET_NAME
    } = process.env;

    if (!R2_ACCESS_KEY_ID || !R2_SECRET_ACCESS_KEY || !R2_BUCKET_NAME) {
        console.log("[CloudSync] External storage credentials not set. Skipping cloud sync.");
        return;
    }

    const s3 = new S3Client({
        region: "auto",
        endpoint: `https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com`,
        credentials: {
            accessKeyId: R2_ACCESS_KEY_ID,
            secretAccessKey: R2_SECRET_ACCESS_KEY,
        },
    });

    const vaultPath = "vault/x_vault.jsonl";
    if (!fs.existsSync(vaultPath)) return;

    console.log(`[CloudSync] Mirroring vault to R2 bucket: ${R2_BUCKET_NAME}...`);

    try {
        const fileContent = fs.readFileSync(vaultPath);
        const command = new PutObjectCommand({
            Bucket: R2_BUCKET_NAME,
            Key: "backups/x_vault.jsonl",
            Body: fileContent,
            ContentType: "application/x-jsonlines",
        });

        await s3.send(command);
        console.log("[CloudSync] SUCCESS: Vault synced to Cloudflare R2.");

        // Update last sync in config
        if (fs.existsSync('config.json')) {
            const config = JSON.parse(fs.readFileSync('config.json', 'utf8'));
            config.settings = config.settings || {};
            config.settings.last_cloud_sync = new Date().toISOString();
            fs.writeFileSync('config.json', JSON.stringify(config, null, 2));
        }
    } catch (err) {
        console.error("[CloudSync] FAILED:", err.message);
    }
}

syncToCloud();

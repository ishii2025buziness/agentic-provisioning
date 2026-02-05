import express from 'express';
import fs from 'node:fs';
import path from 'node:path';
import { execSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());
app.use(express.static(path.join(__dirname, '../dashboard')));

// API: Get Status & Config
app.get('/api/status', (req, res) => {
    let status = "Unknown";
    let uptime = "0s";
    try {
        const pm2Status = execSync('pm2 jlist').toString();
        const list = JSON.parse(pm2Status);
        const collector = list.find(p => p.name === 'x-collector');
        if (collector) {
            status = collector.pm2_env.status;
            uptime = Math.floor((Date.now() - collector.pm2_env.pm_uptime) / 1000) + "s";
        }
    } catch (e) {
        status = "PM2 Not Found";
    }

    const config = JSON.parse(fs.readFileSync('config.json', 'utf8'));

    // Calculate vault size if possible
    let vaultSize = config.settings?.total_stored || 0;

    res.json({ status, uptime, config, vaultSize });
});

// API: Save Config
app.post('/api/config', (req, res) => {
    const newConfig = req.body;
    fs.writeFileSync('config.json', JSON.stringify(newConfig, null, 2));
    res.json({ success: true });
});

// API: Control (Start/Stop)
app.post('/api/control', (req, res) => {
    const { action } = req.body;
    try {
        if (action === 'start') {
            execSync('pm2 start x-collector');
        } else if (action === 'stop') {
            execSync('pm2 stop x-collector');
        } else if (action === 'restart') {
            execSync('pm2 restart x-collector');
        }
        res.json({ success: true });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

// API: Get Latest Data
app.get('/api/data', (req, res) => {
    const dataPath = 'x_data_latest.json';
    if (fs.existsSync(dataPath)) {
        const data = fs.readFileSync(dataPath, 'utf8');
        res.json(JSON.parse(data));
    } else {
        res.json([]);
    }
});

app.listen(PORT, '0.0.0.0', () => {
    console.log(`[Dashboard] Serving at http://0.0.0.0:${PORT}`);
});

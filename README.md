# YT Vault — Vercel Edition

Fully serverless YouTube downloader. No background threads, no disk writes.

## Architecture

```
Browser  →  /api/info     (yt-dlp metadata, no download)
         →  /api/download (extract direct stream URL)
         →  /api/proxy    (stream file through Vercel to browser)
```

The proxy route avoids CORS issues with YouTube's signed CDN URLs and
gives the browser a clean `Content-Disposition: attachment` header.

## Deploy to Vercel

### 1. Install Vercel CLI
```bash
npm i -g vercel
```

### 2. Clone / enter the project
```bash
cd yt-vault-vercel
```

### 3. Deploy
```bash
vercel
```
Follow the prompts. On first deploy Vercel will auto-detect the Python runtime.

### 4. Set function timeouts (already in vercel.json)
- `/api/info`     → 30s
- `/api/download` → 60s
- `/api/proxy`    → 60s

> **Note:** Vercel Hobby plan caps at 10s. Upgrade to Pro for the full 60s,
> or self-host on Railway/Render for unlimited runtime.

## Local Development
```bash
pip install yt-dlp requests
vercel dev        # runs all /api routes + serves /public
```

## File Structure
```
yt-vault-vercel/
├── vercel.json          # routing + function config
├── requirements.txt     # Python deps (yt-dlp)
├── api/
│   ├── info.py          # GET video metadata + formats
│   ├── download.py      # Resolve direct stream URL
│   └── proxy.py         # Stream file to browser
└── public/
    └── index.html       # Frontend UI
```

## Limitations on Vercel Hobby
| Limit | Hobby | Pro |
|-------|-------|-----|
| Function timeout | 10s | 60s |
| Response size | 5 MB | 5 MB |
| Bandwidth | 100 GB/mo | 1 TB/mo |

For large files (>5 MB response) or long videos, consider Railway or Render.

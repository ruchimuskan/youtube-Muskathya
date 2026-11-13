# One-time setup (phir sirf `git push`)

Tumhein **sirf ek baar** yeh karna hai — uske baad har `git push` par [cron-job.org](https://console.cron-job.org/dashboard) schedules khud update ho jati hain.

## 1. GitHub repository secrets

Repo: **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Kahan se |
|--------|-----------|
| `CRONJOB_API_KEY` | [cron-job.org Console](https://console.cron-job.org/dashboard) → **Settings** → API key |
| `GH_DISPATCH_PAT` | [GitHub PAT](https://github.com/settings/tokens) → classic → scope **`repo`** |
| `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN` | Pehle se (generate ke liye) |
| `AI_PROVIDER` | Optional (`auto` / `cloudflare` / `ollama`) |

## 2. Mac par self-hosted runner (video + OAuth yahin chalti hai)

Runner labels: `self-hosted`, `macOS`, `youtube-ai`  
Project folder mein `.env`, `client_secrets.json`, `data/oauth_tokens.json` rahein (git mein nahi).

## 3. Push

```bash
git push origin main
```

Workflow **Sync cron-job.org schedules** automatically creates:

- **3:00 PM IST** → GitHub `daily_pipeline` → video + YouTube upload  
- **6:00 PM IST** → GitHub `upload_queue` → deferred uploads  

Dashboard: [cron-job.org](https://console.cron-job.org/dashboard)

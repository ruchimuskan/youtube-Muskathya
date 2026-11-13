# Bina daily kuch kiye video (sach + options)

## Ab cloud mode (Mac optional)

| Part | Kahan chalta hai |
|------|------------------|
| Timer | [cron-job.org](https://console.cron-job.org/dashboard) |
| Trigger + **video + upload** | **GitHub Actions** (`ubuntu-latest` cloud) |
| YouTube login | GitHub Secrets (`GOOGLE_CLIENT_SECRETS_JSON`, `YOUTUBE_OAUTH_TOKENS_JSON`) |

👉 **Mac on rakhne ki zaroorat nahi** — pipeline GitHub ke server par chalti hai. Tum bas git push / cron schedule.

**Note:** Private repo par GitHub **free minutes limit** hai — lambi video daily chalane par kabhi paid minutes lag sakte hain.

---

## Option A — Mac hi server (sabse kam kaam)

1. Mac **sleep off** (Power settings) ya 3–7 PM awake
2. GitHub → repo **Settings → Actions → Runners** → runner **Idle** (green)
3. Ek baar runner ko service: `cd actions-runner && sudo ./svc.sh install && sudo ./svc.sh start`

Phir cron-job + GitHub khud chalayenge.

---

## Option B — Asli “server only” (Mac free)

Rent Ubuntu VPS (Hetzner / DigitalOcean ~$5/mo), **ek baar** setup → phir Mac band rakho:

1. VPS par clone repo, `.env`, `client_secrets.json`, OAuth tokens copy
2. Install runner with label `youtube-ai`
3. `bash scripts/cloud/ubuntu_bootstrap.sh`

Details: `scripts/cloud/ubuntu_bootstrap.sh`

---

## 100% cloud bina kisi machine ke?

Is project ke liye **abhi possible nahi** — YouTube OAuth, Piper, local video files GitHub ke shared runner par is architecture mein nahi chalte. Cloud VPS = ek baar setup, phir zero daily touch.

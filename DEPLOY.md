# Deploying blackfox as a live web app (Render)

This repo ships a `Dockerfile` (which bundles the Tectonic LaTeX engine) and a
`render.yaml` blueprint, so you can put the web UI online with HTTPS and accounts.

## Read this first — what running it publicly means

- **It costs money two ways.** A small monthly fee for the always-on host (see
  below) **and** every resume build calls the Claude API on *your*
  `ANTHROPIC_API_KEY`. A public sign-up page means anyone who finds the URL can
  spend your API budget. This blueprint is a **quick public demo** — it has no
  rate limiting or invite gate. Don't share the URL widely without adding those
  (ask and I'll wire them up).
- **You need a paid instance for data to persist.** Accounts and resumes live on
  a disk. Render's free plan has **no disk** and sleeps when idle, so data would
  reset on every deploy/sleep. The blueprint uses the **Starter** plan (~$7/mo)
  with a 1 GB disk. Fine to start, easy to scale down/delete later.
- **Keep your API key out of git.** It's set in the Render dashboard as a secret,
  never committed. (`.env` is git- and docker-ignored.)

## Deploy on Render (blueprint, ~5 minutes)

1. Push this repo to GitHub (already done if you used `gh`).
2. Go to <https://dashboard.render.com> → **New + → Blueprint**.
3. Connect your GitHub and pick the `blackfox` repo. Render reads
   `render.yaml` and proposes a Docker web service with a disk.
4. When prompted, set the **`ANTHROPIC_API_KEY`** environment variable to your
   key (it's marked `sync: false` so Render asks you for it).
   `RESUME_AGENT_SECRET_KEY` is generated for you; `RESUME_AGENT_ENV=production`
   is already set.
5. Click **Apply**. The first build takes a few minutes (it installs Tectonic).
6. When it's live, open the `https://blackfox-xxxx.onrender.com` URL, create
   an account, and build a resume — exactly like the local app.

### Manual setup (instead of the blueprint)

New + → **Web Service** → your repo → Runtime **Docker**. Add a **Disk** mounted
at `/data` (1 GB). Add env vars `ANTHROPIC_API_KEY` (secret),
`RESUME_AGENT_ENV=production`, and `RESUME_AGENT_SECRET_KEY` (any long random
string). Deploy.

## Test the image locally first (optional)

```bash
docker build -t blackfox .
docker run --rm -p 8000:8000 \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -e RESUME_AGENT_SECRET_KEY=dev-secret \
  -v "$PWD/_data:/data" \
  blackfox
# open http://localhost:8000
```

(Drop `RESUME_AGENT_ENV=production` locally, or it'll require HTTPS for cookies —
the image sets it; pass `-e RESUME_AGENT_ENV=` to override when testing over
plain http.)

## Notes & limits

- **Single instance.** Builds run as background threads inside the web process,
  so this is designed to run as **one** instance (the disk also can't be shared
  across instances). Don't scale the service past 1.
- **First build per deploy is slower.** Tectonic downloads LaTeX packages on
  first use; they're cached on the `/data` disk afterward.
- **Custom domain & HTTPS** are available in Render's service settings; TLS is
  automatic.

## Hardening for real public use (not included here)

If this graduates from demo to something you share widely, add: per-account and
per-IP **rate limits**, a **cap on builds per user**, **CSRF tokens** on the
forms, optional **email verification**, and an **invite code** on sign-up. Say
the word and I'll add them.

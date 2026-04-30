# 🚀 LinkMasterBot — Telegram Link Shortener + FastAPI Bypass Gateway

A production-grade hybrid system:
- **Telegram Bot** (python-telegram-bot v21+) for user management, API config, admin panel.
- **FastAPI Web Gateway** for click handling, IP-based 1st/2nd-visit routing, and bypass redirection.
- **Supabase (Postgres)** as datastore.

Implements the bypass logic from the `LKSFY Instant Redirect` userscript
(https://greasyfork.org/en/scripts/571604-lksfy-instant-redirect).

## Features
- 🛠️ Per-user GPLinks / LinkShortify API key configuration
- 💎 1st visit → user's API · 2nd+ visit → admin's API (silent monetization)
- 🚀 Server-side LKSFY bypass (forces `ab=1` cookie + intermediate-domain `?id=` resolution)
- 📊 Admin panel with toggles: Bypass on/off · Global Redirect on/off · IP logging
- 🔒 Banning, stats, premium flag

## Deploy on Render
1. Import this repo to Render → **New Web Service**.
2. Build: `pip install -r requirements.txt`
3. Start: `bash start.sh`
4. Set env vars (see `.env.example`).
5. Run `db/migrations.sql` in Supabase SQL editor.

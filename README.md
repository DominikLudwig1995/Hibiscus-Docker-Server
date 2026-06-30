<div align="center">

# 🌺 Hibiscus Docker Server

**Your own online banking server — self-hosted, private, no third parties.**

[![CI](https://github.com/DominikLudwig1995/Hibiscus-Docker-Server/actions/workflows/docker-image.yml/badge.svg)](https://github.com/DominikLudwig1995/Hibiscus-Docker-Server/actions/workflows/docker-image.yml)
[![Hibiscus](https://img.shields.io/badge/hibiscus--server-2.12.4-green)](https://www.willuhn.de/products/hibiscus-server/)
[![Platforms](https://img.shields.io/badge/platforms-amd64%20%7C%20arm64-lightgrey)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## What does this do?

This runs [Hibiscus Server](https://www.willuhn.de/products/hibiscus-server/) — an open-source HBCI/FinTS banking server — on your own machine using Docker. Once running, it gives you programmatic access to your German bank accounts:

- 📥 Fetch account transactions and balances
- 💸 Initiate transfers
- 🔔 Set up automatic transaction fetching

**Your banking credentials never leave your machine.** No cloud, no third-party app, no subscription.

---

## Requirements

- A machine with [Docker](https://docs.docker.com/get-docker/) and Docker Compose v2
- A German bank account with **HBCI/FinTS PIN/TAN** online banking access
  - Most German banks support this (Sparkasse, Volksbank, Deutsche Bank, ING, DKB, …)
  - Check with your bank if unsure — look for "FinTS" or "HBCI" in your online banking settings

---

## Setup (5 minutes)

### Step 1 — Download the files

```bash
git clone https://github.com/DominikLudwig1995/Hibiscus-Docker-Server.git
cd Hibiscus-Docker-Server
```

No git? Download the ZIP from GitHub and unpack it.

### Step 2 — Create your config file

```bash
cp .env.example .env
```

Open `.env` in any text editor and set three values:

```env
HIBISCUS_PASSWORD=choose-a-strong-password
DB_USERNAME=hibiscus
DB_PASSWORD=choose-another-password
```

| Setting | What it is |
|---------|-----------|
| `HIBISCUS_PASSWORD` | The master password for your Hibiscus installation. You'll use this to log in to the web interface. **Write it down — you cannot recover it if lost.** |
| `DB_USERNAME` | Username for the internal database. `hibiscus` is fine. |
| `DB_PASSWORD` | Password for the internal database. Any strong password works. |

### Step 3 — Start

```bash
docker compose up -d
```

This downloads the image, starts the database, and launches Hibiscus. **First start takes about 90 seconds.**

### Step 4 — Open the web interface

Go to **http://localhost:8888** in your browser and log in with your `HIBISCUS_PASSWORD`.

> **Running on a server?** Replace `localhost` with your server's IP address or hostname.

---

## Day-to-day usage

### Start / stop

```bash
docker compose up -d      # start in background
docker compose down       # stop
docker compose restart    # restart both services
```

### Check if everything is running

```bash
docker compose ps
```

Both `hibiscus` and `hibiscus-db` should show **healthy**.

### View logs

```bash
docker logs hibiscus       # Hibiscus logs
docker logs hibiscus-db    # Database logs
docker logs -f hibiscus    # Follow live (Ctrl+C to stop)
```

### Automatic start on boot

The services are configured with `restart: unless-stopped` — they restart automatically after a reboot or crash unless you explicitly stop them with `docker compose down`.

---

## Adding your bank accounts

Bank accounts are configured through the Hibiscus web interface at **http://localhost:8888**.

1. Log in with your `HIBISCUS_PASSWORD`
2. Go to **Einstellungen → Bankzugänge** (Settings → Bank connections)
3. Add your bank using your BLZ (bank routing number), online banking user ID, and PIN
4. Hibiscus will connect to your bank and download your accounts

You will need:
- Your bank's **BLZ** (8-digit routing number)
- Your **online banking user ID** (Kontonummer or Legitimations-ID)
- Your **online banking PIN**
- Your bank's **FinTS/HBCI server address** (usually findable in your bank's online banking help)

---

## Backup

> **Back up regularly.** Your banking keys and account history are stored locally — there is no cloud backup.

```bash
# Back up everything (run this regularly, e.g. weekly via cron)
docker exec hibiscus-db pg_dump -U hibiscus hibiscus > hibiscus-backup-$(date +%Y%m%d).sql
tar czf jameica-backup-$(date +%Y%m%d).tar.gz ./data/jameica
```

Keep the two backup files together — you need both to restore.

### Restore from backup

```bash
# Stop Hibiscus first
docker compose down

# Restore Jameica data (keys, config)
tar xzf jameica-backup-20250101.tar.gz

# Start the database only
docker compose up -d postgres

# Restore the database
docker exec -i hibiscus-db psql -U hibiscus hibiscus < hibiscus-backup-20250101.sql

# Start everything
docker compose up -d
```

---

## Configuration reference

The `.env` file controls all settings. Uncomment and change any line to override the default.

```env
# ── Required ──────────────────────────────────────────────────────────────────

HIBISCUS_PASSWORD=your-master-password
DB_USERNAME=hibiscus
DB_PASSWORD=your-db-password

# ── Optional ──────────────────────────────────────────────────────────────────

# Change the port the web interface is available on (default: 8888)
# HIBISCUS_PORT=8888

# Disable login requirement (not recommended outside of local/test use)
# HIBISCUS_HTTP_AUTH=false

# Disable SSL (only for testing — leave enabled in production)
# HIBISCUS_HTTP_SSL=false

# Store Jameica data in a custom directory instead of ./data/jameica
# JAMEICA_DATA_PATH=/opt/hibiscus/data
```

---

## Updating Hibiscus

When a new version of this image is released:

```bash
docker compose pull
docker compose up -d
```

That's it. Your data is stored in a separate volume and is not affected by the update.

---

## Troubleshooting

### The web interface doesn't load

1. Wait 90 seconds — Hibiscus takes a moment to start up on first boot
2. Check that both services are healthy: `docker compose ps`
3. Check the logs for errors: `docker logs hibiscus`

### I forgot my master password

The master password cannot be recovered — it encrypts your banking keys. You will need to start fresh:

```bash
docker compose down
rm -rf ./data/jameica      # ⚠️ this deletes your Hibiscus config and keys
docker compose up -d
```

You will then need to re-add your bank accounts.

### Port 8888 is already in use

Add this to your `.env` and restart:

```env
HIBISCUS_PORT=8889
```

### Running on a Raspberry Pi or Apple Silicon Mac

The image supports both `amd64` and `arm64` natively — no extra steps needed. Docker will automatically use the right version.

### Something else is wrong

```bash
docker logs hibiscus 2>&1 | tail -50
```

Share the output when asking for help.

---

## Uninstall

```bash
# Stop and remove containers, network, and database volume
docker compose down -v

# Remove Jameica data (banking keys, account history)
rm -rf ./data/

# Remove the Docker image
docker rmi ghcr.io/dominikludwig1995/hibiscus:latest
```

---

## Credits

Hibiscus Server is built and maintained by [willuhn.de](https://www.willuhn.de).

- **Hibiscus Server** — [willuhn.de/products/hibiscus-server](https://www.willuhn.de/products/hibiscus-server/)
- **Source code** — [github.com/willuhn-open-projects/hibiscus](https://github.com/willuhn-open-projects/hibiscus)

---

<div align="center">

Questions or issues? [Open a GitHub issue](https://github.com/DominikLudwig1995/Hibiscus-Docker-Server/issues)

</div>

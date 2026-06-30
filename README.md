<div align="center">

# 🌺 Hibiscus Docker Server

**Self-hosted HBCI/FinTS online banking — containerized, hardened, ready to ship.**

[![CI](https://github.com/DominikLudwig1995/Hibiscus-Docker-Server/actions/workflows/docker-image.yml/badge.svg)](https://github.com/DominikLudwig1995/Hibiscus-Docker-Server/actions/workflows/docker-image.yml)
[![GHCR](https://img.shields.io/badge/ghcr.io-dominikludwig1995%2Fhibiscus-blue?logo=github&logoColor=white)](https://github.com/DominikLudwig1995/Hibiscus-Docker-Server/pkgs/container/hibiscus)
[![Hibiscus](https://img.shields.io/badge/hibiscus--server-2.12.4-green)](https://www.willuhn.de/products/hibiscus-server/)
[![Ubuntu 26.04](https://img.shields.io/badge/ubuntu-26.04-E95420?logo=ubuntu&logoColor=white)](https://hub.docker.com/_/ubuntu)
[![Platforms](https://img.shields.io/badge/platforms-amd64%20%7C%20arm64-lightgrey)](#building-locally)

[Quick Start](#quick-start) · [Configuration](#configuration) · [Provisioning CLI](#provisioning-cli) · [Upgrading](#upgrading) · [Troubleshooting](#troubleshooting) · [Credits](#credits)

</div>

---

## What is this?

[Hibiscus Server](https://www.willuhn.de/products/hibiscus-server/) is an open-source HBCI/FinTS banking server that lets you access your German bank accounts programmatically — fetch transactions, check balances, initiate transfers — without relying on any third-party service. You own the server, you own the data.

This repo wraps it in a production-ready Docker image:

| Feature | Detail |
|---------|--------|
| **Zero config files in the image** | All settings are injected at startup from environment variables |
| **PostgreSQL included** | docker-compose brings up Postgres + Hibiscus in one command |
| **Multi-arch** | Native `linux/amd64` and `linux/arm64` (Raspberry Pi, Apple Silicon, cloud VMs) |
| **3-stage build** | Build tools never reach the runtime image — minimal attack surface |
| **Jinja2 provisioner** | Typed, validated, testable config rendering with a Rich CLI |
| **Security scanning** | Trivy CVE scan on every release, results in the GitHub Security tab |
| **Dependabot** | Automatic PRs for base image, Actions, and Python dependency updates |

---

## Quick Start

### Prerequisites

- Docker + Docker Compose (v2)
- A German bank account that supports HBCI/FinTS (FinTS 3.0 / PIN/TAN)

### 1 — Get the files

```bash
git clone https://github.com/DominikLudwig1995/Hibiscus-Docker-Server.git
cd Hibiscus-Docker-Server
```

Or just grab the two files you need:

```bash
curl -O https://raw.githubusercontent.com/DominikLudwig1995/Hibiscus-Docker-Server/main/docker-compose.yml
curl -O https://raw.githubusercontent.com/DominikLudwig1995/Hibiscus-Docker-Server/main/.env.example
```

### 2 — Configure

```bash
cp .env.example .env
```

Open `.env` and set the three required values:

```env
HIBISCUS_PASSWORD=your-hibiscus-master-password
DB_USERNAME=hibiscus
DB_PASSWORD=your-postgres-password
```

> **Security note**: `HIBISCUS_PASSWORD` is the master password that encrypts your banking credentials in Hibiscus. Choose something strong and store it safely — losing it means losing access to your Hibiscus data.

### 3 — Start

```bash
docker compose up -d
```

This starts PostgreSQL, waits for it to be healthy, then starts Hibiscus and provisions all config files from your `.env`. First start takes ~90 seconds (JVM startup + DB initialisation).

### 4 — Open the web interface

```
http://localhost:8888
```

Log in with the Hibiscus master password you set in step 2.

### 5 — Check it's running

```bash
docker compose ps           # both services should show "healthy"
docker logs hibiscus        # provisioner output + Hibiscus startup log
```

---

## Configuration

All config lives in a single `.env` file. Credentials are shared between `postgres` and `hibiscus` — no duplication, no separate secret files.

### Required

| Variable | Description |
|----------|-------------|
| `HIBISCUS_PASSWORD` | Hibiscus master password — encrypts your banking keystore |
| `DB_PASSWORD` | PostgreSQL password (shared between the two services) |
| `DB_USERNAME` | PostgreSQL username (default: `hibiscus`) |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_NAME` | `hibiscus` | PostgreSQL database name |
| `HIBISCUS_PORT` | `8888` | Host port the web interface is exposed on |
| `HIBISCUS_HTTP_AUTH` | `true` | Enable HTTP basic auth on the web interface |
| `HIBISCUS_HTTP_SSL` | `true` | Enable SSL on the web interface |
| `JAMEICA_DATA_PATH` | `./data/jameica` | Host path for persistent Jameica data (bank accounts, keys, history) |
| `HIBISCUS_IMAGE` | `ghcr.io/dominikludwig1995/hibiscus:2.12.4` | Override to use a locally built image |

### Build args (only when running `docker compose build`)

| Variable | Default | Description |
|----------|---------|-------------|
| `HIBISCUS_VERSION` | `2.12.4` | Hibiscus Server version to download |
| `MARIADB_CONNECTOR_VERSION` | `3.5.3` | MariaDB JDBC connector version |
| `POSTGRES_DRIVER_VERSION` | `42.7.7` | PostgreSQL JDBC driver version |

### Advanced Hibiscus variables

These are set automatically by the compose file but can be overridden for custom setups:

| Variable | Default | Description |
|----------|---------|-------------|
| `HIBISCUS_DB_TYPE` | `postgresql` | `postgresql` or `mysql` |
| `HIBISCUS_DB_HOST` | `postgres` | Database hostname |
| `HIBISCUS_DB_PORT` | `5432` | Database port |
| `HIBISCUS_ACCOUNTS_FILE` | — | Path to a YAML file with PIN/TAN bank account entries |

---

## Provisioning CLI

At container startup, the provisioner reads your environment variables and renders the Hibiscus `.properties` files using Jinja2 templates. You can also run it locally for validation and debugging.

### Run locally

```bash
cd provision
pip install -r requirements.txt

# Validate config before deploying
HIBISCUS_PASSWORD=secret \
HIBISCUS_DB_USERNAME=hibiscus \
HIBISCUS_DB_PASSWORD=dbpass \
  python provision.py validate --from-env

# Preview what would be written (nothing is touched)
HIBISCUS_PASSWORD=secret \
HIBISCUS_DB_USERNAME=hibiscus \
HIBISCUS_DB_PASSWORD=dbpass \
  python provision.py render --from-env --dry-run

# Show resolved config with secrets masked
python provision.py show --config config.example.yml
```

### Using a config file instead of env vars

```yaml
# config.yml
hibiscus_password: "your-master-password"
db_username: hibiscus
db_password: "your-db-password"
db_host: postgres
db_type: postgresql

accounts:
  - name: mybank
    server: hbci.mybank.de
    blz: "12345678"
    userid: myuserid
    hbciversion: "300"
```

```bash
python provision.py render --config config.yml --out /tmp/cfg
```

### Rendered files

| Template | Output file | Controls |
|----------|-------------|---------|
| `HBCIDBService.properties.j2` | `HBCIDBService.properties` | DB driver, JDBC URL, credentials |
| `Plugin.properties.j2` | `Plugin.properties` | Web interface port, auth, SSL |
| `PinTanConfig.properties.j2` | `PinTanConfig.properties` | PIN/TAN bank account entries |

### Adding bank accounts

Mount a YAML file and point `HIBISCUS_ACCOUNTS_FILE` at it:

```yaml
# accounts.yml
- name: mybank
  server: hbci.mybank.de
  blz: "12345678"          # BLZ (bank code)
  userid: myuserid
  customerid: myuserid     # optional, defaults to userid
  hbciversion: "300"       # optional, default "300"
  port: 443                # optional, default 443
```

```yaml
# docker-compose.yml override
services:
  hibiscus:
    environment:
      HIBISCUS_ACCOUNTS_FILE: /run/accounts.yml
    volumes:
      - ./accounts.yml:/run/accounts.yml:ro
```

---

## Building Locally

```bash
# Build with defaults
docker compose build

# Build a specific Hibiscus version
HIBISCUS_VERSION=2.12.4 docker compose build

# Use the locally built image instead of pulling from GHCR
HIBISCUS_IMAGE=hibiscus-docker-server-hibiscus docker compose up -d

# Multi-platform build with Buildx (outside compose)
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t hibiscus:local .
```

---

## How It Works

```
GitHub Actions (on git tag v*.*.*)
─────────────────────────────────────────────────────
  test-provision          build                security-scan
  ──────────────   ──────────────────────   ──────────────────
  pytest (33 tests) → amd64 build + CST  →  Trivy → SARIF
                    → arm64 build + push
                          │
                          ▼
              ghcr.io/dominikludwig1995/hibiscus
              :2.12.4  :2.12  :2


Docker image — 3-stage build
──────────────────────────────────────────────────────
  hibiscus-fetch          python-venv           runtime
  ─────────────────   ──────────────────   ──────────────────
  wget Hibiscus zip   pip install into     JRE-headless +
  wget MariaDB jar    /opt/venv            python3 only
  wget PG driver                           (no build tools)
          │                  │                    │
          └──────────────────┴────────────────────┘
                                  │
                             ENTRYPOINT
                          1. provision render --from-env
                             → writes .properties files
                          2. exec jameicaserver.sh
                             (PID 1, signals forwarded)
```

---

## Upgrading

### Upgrading Hibiscus

1. Check the [Hibiscus Server download page](https://www.willuhn.de/products/hibiscus-server/download.php) for the latest version
2. Update `HIBISCUS_VERSION` in your `.env` (for local builds) or wait for a new release tag here
3. Rebuild and restart:

```bash
docker compose build --no-cache
docker compose up -d
```

### Upgrading PostgreSQL

```bash
# Stop the stack first — never upgrade Postgres with Hibiscus running
docker compose down

# Pull the new Postgres image
docker compose pull postgres

# Start — Postgres auto-upgrades the data directory if needed
docker compose up -d
```

> **Warning**: Major PostgreSQL version upgrades (e.g., 16 → 17) require a data migration. Back up `./data/` first.

---

## Backup

Your data lives in two places:

| What | Where | Contains |
|------|-------|---------|
| Jameica data | `JAMEICA_DATA_PATH` (default `./data/jameica`) | Banking keys, PIN/TAN accounts, plugin config |
| Database | Docker volume `postgres-data` | Transactions, account history, Hibiscus data |

```bash
# Back up the database
docker exec hibiscus-db pg_dump -U hibiscus hibiscus > hibiscus-$(date +%Y%m%d).sql

# Back up Jameica data
tar czf jameica-$(date +%Y%m%d).tar.gz ./data/jameica
```

Restore:

```bash
# Restore database
docker exec -i hibiscus-db psql -U hibiscus hibiscus < hibiscus-20250101.sql

# Restore Jameica data
tar xzf jameica-20250101.tar.gz
```

---

## Testing

### Unit tests

```bash
pip install -r provision/requirements.txt pytest
pytest tests/test_provision.py -v
```

33 tests covering: config loading from file and env, `_FILE` secret convention, all three Jinja2 templates, validation, and the full CLI (`render` / `validate` / `show`).

### Container structure tests

```bash
docker build -t hibiscus:test .
container-structure-test test \
  --image hibiscus:test \
  --config tests/container-structure-test.yml
```

Checks: Java + Python available, provisioner importable, all templates present, port 8888 exposed, no Windows artefacts, `update.check=false`.

---

## Troubleshooting

### Container exits immediately

```bash
docker logs hibiscus
```

The provisioner prints exactly which required env vars are missing before it exits. Check that `HIBISCUS_PASSWORD`, `DB_PASSWORD`, and `DB_USERNAME` are all set in `.env`.

### Web interface unreachable

```bash
docker compose ps           # is hibiscus "healthy"?
docker logs hibiscus        # look for "Server started" near the bottom
```

The JVM takes up to 90 seconds to start. The health check `start_period` is set to 90s — wait before investigating. If it never becomes healthy, the logs will show why.

### Port already in use

```bash
# Use a different host port
echo "HIBISCUS_PORT=8889" >> .env
docker compose up -d
```

### Database connection refused

Hibiscus waits for Postgres to pass its health check before starting (`depends_on: condition: service_healthy`). If Postgres is slow to start, Hibiscus waits automatically. Check Postgres logs if it never becomes healthy:

```bash
docker logs hibiscus-db
```

### arm64 / Raspberry Pi issues

Use the GHCR image — it ships native `linux/arm64` layers (no QEMU emulation). If you're building locally on a Raspberry Pi, the build will take longer but produces a native image.

### Reset everything

```bash
docker compose down -v       # removes containers AND the postgres-data volume
rm -rf ./data/jameica        # removes Jameica data (irreversible!)
docker compose up -d         # fresh start
```

---

## Security

- **No secrets in the image** — all sensitive values are injected at runtime via env vars
- **Non-root container** — runs as `hibiscus` (UID 1000)
- **Trivy CVE scanning** — runs on every release; results in the [Security tab](https://github.com/DominikLudwig1995/Hibiscus-Docker-Server/security/code-scanning)
- **Dependabot** — weekly PRs for Ubuntu base image, GitHub Actions, and Python dependencies
- **Mend/WhiteSource SCA** — configured via `.whitesource` for additional supply-chain scanning
- **Update checks disabled** — `update.check=false` is set in `UpdateService.properties`; updates are handled by rebuilding the image

---

## Credits

This project would not exist without the work of the Hibiscus and Jameica maintainers.

- **Hibiscus Server** — [willuhn.de/products/hibiscus-server](https://www.willuhn.de/products/hibiscus-server/)
- **Hibiscus source code** — [github.com/willuhn-open-projects/hibiscus](https://github.com/willuhn-open-projects/hibiscus)
- **Jameica** (the plugin runtime Hibiscus runs on) — [willuhn.de/products/jameica](https://www.willuhn.de/products/jameica/)

Thank you for building and maintaining open-source banking software that puts users in control of their own financial data.

---

<div align="center">

Built with ❤️ for the self-hosting community · [Hibiscus Server](https://www.willuhn.de/products/hibiscus-server/) by [willuhn.de](https://www.willuhn.de)

</div>

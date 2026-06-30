# Hibiscus Docker Server

[![Build & Publish Docker Image](https://github.com/DominikLudwig1995/Hibiscus-Docker-Server/actions/workflows/docker-image.yml/badge.svg)](https://github.com/DominikLudwig1995/Hibiscus-Docker-Server/actions/workflows/docker-image.yml)
[![GitHub Container Registry](https://img.shields.io/badge/ghcr.io-dominikludwig1995%2Fhibiscus-blue?logo=github)](https://github.com/DominikLudwig1995/Hibiscus-Docker-Server/pkgs/container/hibiscus)
[![Ubuntu 24.04](https://img.shields.io/badge/ubuntu-24.04-orange?logo=ubuntu)](https://hub.docker.com/_/ubuntu)

Dockerized [Hibiscus Server](https://www.willuhn.de/products/hibiscus-server/) — a self-hosted HBCI/FinTS online banking server.  
Runs on `linux/amd64` and `linux/arm64` (Raspberry Pi, Apple Silicon).

**Config is provisioned at startup** from environment variables — no manual editing of `.properties` files, no secret files baked into the image.

---

## Table of Contents

- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
- [Image Tags](#image-tags)
- [Environment Variables](#environment-variables)
- [Secrets](#secrets)
- [Provisioning CLI](#provisioning-cli)
- [Building Locally](#building-locally)
- [Testing](#testing)
- [Upgrading Hibiscus](#upgrading-hibiscus)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

```bash
# Create secret files (one value per file)
mkdir -p secrets
echo "hibiscus_master_password" > secrets/hibiscus_password
echo "db_user"                  > secrets/db_username
echo "db_pass"                  > secrets/db_password

# Start (defaults: db on 127.0.0.1:3306, web on :8888)
SECRETS_PATH=./secrets docker compose up -d
```

Open `http://localhost:8888` in your browser.

---

## How It Works

The container follows a three-stage build and a provisioning-on-startup pattern:

```
┌─────────────────────┐   ┌───────────────────────┐
│  hibiscus-fetch     │   │  python-venv           │
│  (build stage)      │   │  (build stage)         │
│                     │   │                        │
│  Downloads Hibiscus │   │  pip install into      │
│  + MariaDB jar      │   │  /opt/venv             │
└────────┬────────────┘   └──────────┬─────────────┘
         │                           │
         └────────────┬──────────────┘
                      ▼
         ┌────────────────────────┐
         │  runtime               │
         │                        │
         │  ENTRYPOINT:           │
         │  1. provision render   │  ← renders Jinja2 templates
         │     --from-env         │    from HIBISCUS_* env vars
         │  2. exec jameicaserver │  ← starts Hibiscus
         └────────────────────────┘
```

At startup, `provision.py render --from-env` reads `HIBISCUS_*` environment variables, renders the Jinja2 templates into the Hibiscus `cfg/` directory, and writes the password file — then `exec`s the Hibiscus process so signals are forwarded correctly.

---

## Image Tags

Images are published to `ghcr.io/dominikludwig1995/hibiscus`.

| Tag | Description |
|-----|-------------|
| `main` | Latest build from the `main` branch (mutable) |
| `sha-<commit>` | Immutable build pinned to a specific commit |
| `v2.10.7` | Full semver tag (on git release tags) |
| `2.10` | Minor version alias |
| `2` | Major version alias |

**Pin to `sha-` or a semver tag in production** — never rely on a mutable tag for stability.

---

## Environment Variables

### Required

| Variable | `_FILE` variant | Description |
|---|---|---|
| `HIBISCUS_PASSWORD` | `HIBISCUS_PASSWORD_FILE` | Hibiscus master password |
| `HIBISCUS_DB_USERNAME` | `HIBISCUS_DB_USERNAME_FILE` | Database username |
| `HIBISCUS_DB_PASSWORD` | `HIBISCUS_DB_PASSWORD_FILE` | Database password |

### Optional

| Variable | Default | Description |
|---|---|---|
| `HIBISCUS_DB_HOST` | `127.0.0.1` | Database host |
| `HIBISCUS_DB_PORT` | `3306` | Database port |
| `HIBISCUS_DB_NAME` | `hibiscus` | Database name |
| `HIBISCUS_HTTP_PORT` | `8888` | Hibiscus web interface port |
| `HIBISCUS_HTTP_AUTH` | `true` | Enable HTTP basic auth |
| `HIBISCUS_HTTP_SSL` | `true` | Enable SSL on the web interface |
| `HIBISCUS_ACCOUNTS_FILE` | — | Path to a YAML file with bank account entries |

### `_FILE` convention

Every secret variable supports a `_FILE` variant that reads the value from a file path. This is the standard Docker secrets pattern:

```yaml
# docker-compose.yml
environment:
  HIBISCUS_PASSWORD_FILE: /run/secrets/hibiscus_password
secrets:
  - hibiscus_password
```

---

## Secrets

The `docker-compose.yml` uses Docker Compose secrets. Create one file per secret:

```
secrets/
  hibiscus_password   ← Hibiscus master password
  db_username         ← Database username
  db_password         ← Database password
```

Set `SECRETS_PATH` to point to your secrets directory (default: `/opt/hibiscus/secrets`).

For bank account configuration (PIN/TAN), create a YAML file and mount it:

```yaml
# accounts.yml
- name: mybank
  server: hbci.mybank.de
  blz: "12345678"
  userid: myuserid
  hbciversion: "300"
```

```yaml
environment:
  HIBISCUS_ACCOUNTS_FILE: /run/secrets/accounts.yml
secrets:
  - accounts.yml
```

---

## Provisioning CLI

The provisioning script can also be used standalone for local development and CI:

```bash
cd provision
pip install -r requirements.txt

# Validate a config file
python provision.py validate --config config.example.yml

# Preview rendered output without writing files
python provision.py render --config config.example.yml --dry-run

# Write to a secrets directory
python provision.py render --config config.example.yml --out ./secrets

# Read from environment variables
HIBISCUS_PASSWORD=secret HIBISCUS_DB_USERNAME=admin HIBISCUS_DB_PASSWORD=pass \
  python provision.py render --from-env --dry-run

# Show resolved config (secrets masked)
python provision.py show --config config.example.yml
```

---

## Building Locally

```bash
# Build with default Hibiscus version
docker build -t hibiscus:local .

# Build with a specific version
docker build --build-arg HIBISCUS_VERSION=2.10.7 -t hibiscus:2.10.7 .

# Multi-platform build
docker buildx build --platform linux/amd64,linux/arm64 -t hibiscus:local .
```

---

## Testing

### Provisioning script (pytest)

```bash
pip install -r provision/requirements.txt pytest
pytest tests/test_provision.py -v
```

32 tests covering config loading, env var parsing, `_FILE` secrets, all three Jinja2 templates, validation, and the full CLI surface.

### Container structure tests

Requires [container-structure-test](https://github.com/GoogleContainerTools/container-structure-test).

```bash
docker build -t hibiscus:test .
container-structure-test test --image hibiscus:test --config tests/container-structure-test.yml
```

Both suites run automatically in CI on every push and pull request.

---

## Upgrading Hibiscus

Update `HIBISCUS_VERSION` in `docker-compose.yml` (or pass it as a build arg), then rebuild:

```bash
docker compose build --no-cache
docker compose up -d
```

---

## Troubleshooting

**Container exits immediately**  
Run `docker logs hibiscus`. The provisioner prints which env vars are missing before exiting.

**Port already in use**  
Set `HIBISCUS_HTTP_PORT` and `HIBISCUS_PORT` in your `.env` file.

**Arm64 / Raspberry Pi**  
Use the pre-built GHCR image — it ships native `linux/arm64` layers; no emulation needed.

**Health check failing**  
The server needs ~90 seconds to start. The `start_period` is set to 90s — wait before investigating.

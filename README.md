<div align="center">

# 🌺 Hibiscus Docker Server

**Self-hosted HBCI/FinTS online banking — containerized, hardened, ready to ship.**

[![CI](https://github.com/DominikLudwig1995/Hibiscus-Docker-Server/actions/workflows/docker-image.yml/badge.svg)](https://github.com/DominikLudwig1995/Hibiscus-Docker-Server/actions/workflows/docker-image.yml)
[![GHCR](https://img.shields.io/badge/ghcr.io-dominikludwig1995%2Fhibiscus-blue?logo=github&logoColor=white)](https://github.com/DominikLudwig1995/Hibiscus-Docker-Server/pkgs/container/hibiscus)
[![Ubuntu 26.04](https://img.shields.io/badge/ubuntu-26.04-E95420?logo=ubuntu&logoColor=white)](https://hub.docker.com/_/ubuntu)
[![Hibiscus](https://img.shields.io/badge/hibiscus--server-2.12.4-green)](https://www.willuhn.de/products/hibiscus-server/)
[![Platforms](https://img.shields.io/badge/platforms-amd64%20%7C%20arm64-lightgrey)](#image-tags)

[**Pull the image**](#quick-start) · [**Image tags**](#image-tags) · [**Configuration**](#configuration) · [**Provisioning**](#provisioning-cli)

</div>

---

## What is this?

[Hibiscus Server](https://www.willuhn.de/products/hibiscus-server/) is an open-source HBCI/FinTS server that lets you access your bank accounts programmatically — fetch transactions, make transfers, and more — without relying on third-party services.

This project packages it as a production-ready Docker image with:

- **Zero secret files in the image** — all config is provisioned at startup from environment variables
- **Multi-arch** — native `linux/amd64` and `linux/arm64` (Raspberry Pi, Apple Silicon, cloud VMs)
- **3-stage build** — build tools never reach the final image; minimal attack surface
- **Jinja2 provisioner** — typed, validated, testable config rendering with a beautiful CLI
- **Security scanning** — Trivy CVE scan on every push, results in the GitHub Security tab
- **Dependabot** — automatic PRs for base image, GitHub Actions, and Python dependency updates

---

## Quick Start

```bash
# 1. Pull the image
docker pull ghcr.io/dominikludwig1995/hibiscus:main

# 2. Create secret files (one value per file)
mkdir -p secrets
echo "your-master-password" > secrets/hibiscus_password
echo "db_user"              > secrets/db_username
echo "db_pass"              > secrets/db_password

# 3. Start
SECRETS_PATH=./secrets docker compose up -d

# 4. Open http://localhost:8888
```

> **First time?** Copy the dummy secrets for a local smoke-test:
> ```bash
> cp secrets/HBCIDBService.properties.dummy secrets/HBCIDBService.properties
> cp secrets/PinTanConfig.properties.dummy  secrets/PinTanConfig.properties
> cp secrets/pwd.dummy                      secrets/pwd
> ```

---

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│  GitHub Actions CI                                              │
│                                                                 │
│  test-provision ──► build (amd64 + arm64) ──► security-scan    │
│       │                    │                        │           │
│  32 pytest tests    push to GHCR            Trivy → SARIF      │
└────────────────────────────────────────────────────────────────-┘

Docker image — 3-stage build
┌──────────────────┐   ┌──────────────────┐
│  hibiscus-fetch  │   │  python-venv     │
│  ubuntu:26.04    │   │  ubuntu:26.04    │
│                  │   │                  │
│  wget Hibiscus   │   │  pip install     │
│  wget MariaDB    │   │  into /opt/venv  │
│  jar             │   │                  │
└────────┬─────────┘   └────────┬─────────┘
         │                      │
         └──────────┬───────────┘
                    ▼
         ┌──────────────────────┐
         │  runtime             │
         │  ubuntu:26.04        │
         │                      │
         │  JRE-headless +      │
         │  python3 only        │
         │                      │
         │  ENTRYPOINT:         │
         │  1. provision render │  ← Jinja2 → .properties files
         │     --from-env       │
         │  2. exec hibiscus    │  ← PID 1, signals forwarded
         └──────────────────────┘
```

---

## Image Tags

Images are published to **`ghcr.io/dominikludwig1995/hibiscus`**.

| Tag | Stability | Use case |
|-----|-----------|----------|
| `main` | Mutable | Latest passing build from `main` |
| `sha-<commit>` | **Immutable** | Pin this in production |
| `v2.12.4` | **Immutable** | Semver release tag |
| `2.12` / `2` | Mutable alias | Minor / major version tracking |

```bash
# Always pin to an immutable tag in production
docker pull ghcr.io/dominikludwig1995/hibiscus:sha-7effa6b

# Or use the branch tag for non-critical environments
docker pull ghcr.io/dominikludwig1995/hibiscus:main
```

---

## Configuration

### Environment Variables

#### Required

| Variable | `_FILE` variant | Description |
|---|---|---|
| `HIBISCUS_PASSWORD` | `HIBISCUS_PASSWORD_FILE` | Hibiscus master password (unlocks keystore) |
| `HIBISCUS_DB_USERNAME` | `HIBISCUS_DB_USERNAME_FILE` | Database username |
| `HIBISCUS_DB_PASSWORD` | `HIBISCUS_DB_PASSWORD_FILE` | Database password |

#### Optional

| Variable | Default | Description |
|---|---|---|
| `HIBISCUS_DB_HOST` | `127.0.0.1` | Database host |
| `HIBISCUS_DB_PORT` | `3306` | Database port |
| `HIBISCUS_DB_NAME` | `hibiscus` | Database name |
| `HIBISCUS_HTTP_PORT` | `8888` | Web interface port |
| `HIBISCUS_HTTP_AUTH` | `true` | Enable HTTP basic auth |
| `HIBISCUS_HTTP_SSL` | `true` | Enable SSL |
| `HIBISCUS_ACCOUNTS_FILE` | — | Path to YAML file with bank account entries |

#### `_FILE` convention (Docker secrets)

Every secret variable supports a `_FILE` variant that reads from a mounted file — the standard Docker secrets pattern:

```yaml
environment:
  HIBISCUS_PASSWORD_FILE: /run/secrets/hibiscus_password
secrets:
  - hibiscus_password
```

### Example `.env`

```env
SECRETS_PATH=/opt/hibiscus/secrets
JAMEICA_DATA_PATH=/opt/hibiscus/data
HIBISCUS_PORT=8888
HIBISCUS_DB_HOST=mariadb
HIBISCUS_DB_PORT=3306
HIBISCUS_DB_NAME=hibiscus
```

---

## Provisioning CLI

Config is provisioned at container startup, but the same script works standalone for local dev and CI validation.

```bash
cd provision
pip install -r requirements.txt

# Validate before deploying
python provision.py validate --config config.example.yml

# Preview what would be written (nothing is touched)
python provision.py render --config config.example.yml --dry-run

# Write secrets directory
python provision.py render --config config.example.yml --out ./secrets

# From env vars (same as what the container does at startup)
HIBISCUS_PASSWORD=secret \
HIBISCUS_DB_USERNAME=admin \
HIBISCUS_DB_PASSWORD=pass \
  python provision.py render --from-env --dry-run

# Show resolved config with secrets masked
python provision.py show --config config.example.yml
```

### Jinja2 templates

| Template | Rendered output | Controls |
|---|---|---|
| `HBCIDBService.properties.j2` | `HBCIDBService.properties` | DB driver, JDBC URL, credentials |
| `PinTanConfig.properties.j2` | `PinTanConfig.properties` | Bank account / PIN-TAN entries |
| `Plugin.properties.j2` | `Plugin.properties` | Web interface port, auth, SSL |

### Bank accounts

For PIN/TAN accounts, mount a YAML file:

```yaml
# accounts.yml
- name: mybank
  server: hbci.mybank.de
  blz: "12345678"
  userid: myuserid
  hbciversion: "300"     # optional
  port: 443              # optional, default 443
```

```yaml
environment:
  HIBISCUS_ACCOUNTS_FILE: /run/secrets/accounts.yml
```

---

## Building Locally

```bash
# Standard build
docker build -t hibiscus:local .

# Specific Hibiscus version
docker build --build-arg HIBISCUS_VERSION=2.12.4 -t hibiscus:2.12.4 .

# Multi-platform (requires Buildx)
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t hibiscus:local .
```

---

## Testing

### Unit tests (pytest)

```bash
pip install -r provision/requirements.txt pytest
pytest tests/test_provision.py -v
```

32 tests — config loading, env var parsing, `_FILE` secrets, all three templates, validation, full CLI surface including `render` / `validate` / `show`.

### Container structure tests

```bash
docker build -t hibiscus:test .
container-structure-test test \
  --image hibiscus:test \
  --config tests/container-structure-test.yml
```

Checks: port exposure, Java + Python available, provisioner importable, all templates present, no Windows artefacts, `update.check=false`.

Both suites run automatically in CI — provisioning tests gate the Docker build.

---

## Upgrading Hibiscus

Change `HIBISCUS_VERSION` in `docker-compose.yml`, then rebuild:

```bash
docker compose build --no-cache
docker compose up -d
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Container exits immediately | Run `docker logs hibiscus` — the provisioner prints exactly which env vars are missing |
| Port already in use | Set `HIBISCUS_HTTP_PORT` and `HIBISCUS_PORT` in your `.env` |
| Health check failing | Server needs ~90s to start; `start_period` is 90s — wait before investigating |
| arm64 / Raspberry Pi issues | Use the GHCR image — it ships native `linux/arm64` layers, no emulation |
| `update.check` warning | Disabled by design; updates are handled by rebuilding the image |

---

## Security

- Trivy CVE scan runs on every push; results appear in the [Security tab](https://github.com/DominikLudwig1995/Hibiscus-Docker-Server/security/code-scanning)
- Dependabot keeps the base image, GitHub Actions, and Python deps up to date automatically
- No secrets are baked into the image — all sensitive values are injected at runtime
- Container runs as a non-root user (`hibiscus`, UID 1000)
- Mend/WhiteSource SCA configured via `.whitesource`

---

<div align="center">

Built with ❤️ · [Hibiscus Server](https://www.willuhn.de/products/hibiscus-server/) by [willuhn.de](https://www.willuhn.de)

</div>

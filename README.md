# Hibiscus Docker Server

[![Build & Publish Docker Image](https://github.com/DominikLudwig1995/Hibiscus-Docker-Server/actions/workflows/docker-image.yml/badge.svg)](https://github.com/DominikLudwig1995/Hibiscus-Docker-Server/actions/workflows/docker-image.yml)
[![GitHub Container Registry](https://img.shields.io/badge/ghcr.io-dominikludwig1995%2Fhibiscus-blue?logo=github)](https://github.com/DominikLudwig1995/Hibiscus-Docker-Server/pkgs/container/hibiscus)
[![Ubuntu 24.04](https://img.shields.io/badge/ubuntu-24.04-orange?logo=ubuntu)](https://hub.docker.com/_/ubuntu)

Dockerized [Hibiscus Server](https://www.willuhn.de/products/hibiscus-server/) — a self-hosted HBCI/FinTS online banking server.  
Runs on `linux/amd64` and `linux/arm64` (Raspberry Pi, Apple Silicon).  
Pre-built images are published to the GitHub Container Registry on every push to `main` and on git version tags.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Image Tags](#image-tags)
- [Provisioning](#provisioning)
- [Configuration](#configuration)
- [Building Locally](#building-locally)
- [Testing](#testing)
- [Environment Variables](#environment-variables)
- [Secrets](#secrets)
- [Upgrading Hibiscus](#upgrading-hibiscus)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

Pull the image and start the server with dummy secrets for local testing:

```bash
# Copy dummy secrets
cp secrets/HBCIDBService.properties.dummy  secrets/HBCIDBService.properties
cp secrets/PinTanConfig.properties.dummy   secrets/PinTanConfig.properties
cp secrets/pwd.dummy                       secrets/pwd

# Start
SECRETS_PATH=./secrets JAMEICA_DATA_PATH=./.jameica docker compose up -d
```

Open `http://localhost:8888` in your browser.

---

## Prerequisites

- Docker >= 24.0
- Docker Compose >= 2.0

---

## Image Tags

Images are published to `ghcr.io/dominikludwig1995/hibiscus`.

| Tag | Description |
|-----|-------------|
| `main` | Latest build from the `main` branch |
| `sha-<commit>` | Immutable build pinned to a specific commit |
| `v2.10.7` | Full semver tag (on git release tags) |
| `2.10` | Minor version alias (on git release tags) |
| `2` | Major version alias (on git release tags) |

**Recommendation:** pin to a specific `sha-` or semver tag in production — never rely on a mutable branch tag for stability.

```bash
# Pull a specific immutable version
docker pull ghcr.io/dominikludwig1995/hibiscus:sha-abc1234

# Pull latest main branch build (mutable)
docker pull ghcr.io/dominikludwig1995/hibiscus:main
```

---

## Provisioning

The `provision/` directory contains a Python script that renders Jinja2 templates into ready-to-use secret files.  
This replaces manual editing of `.properties` files and is safe to run in CI or as part of your deployment pipeline.

### Setup

```bash
pip install -r provision/requirements.txt
```

### Usage

```bash
# Copy and edit the example config
cp provision/config.example.yml provision/config.yml
$EDITOR provision/config.yml

# Dry run — prints rendered output without writing files
python provision/provision.py --config provision/config.yml --dry-run

# Write files to ./secrets/
python provision/provision.py --config provision/config.yml --out ./secrets
```

### Templates

| Template | Output file | Purpose |
|----------|-------------|---------|
| `HBCIDBService.properties.j2` | `HBCIDBService.properties` | Database connection |
| `PinTanConfig.properties.j2` | `PinTanConfig.properties` | Bank account / PIN-TAN config |
| `Plugin.properties.j2` | `Plugin.properties` | Web interface settings |

`config.example.yml` documents every available variable with defaults and comments.

---

## Configuration

### Production

1. Copy your secrets to the server:

```bash
scp -r secrets/ user@<your-server>:/opt/hibiscus/secrets/
```

2. Create a `.env` file on the server (see [Environment Variables](#environment-variables)).

3. Start the stack:

```bash
docker compose --env-file .env up -d
```

---

## Building Locally

```bash
# Build with default Hibiscus version
docker build -t hibiscus:local .

# Build with a specific version
docker build --build-arg HIBISCUS_VERSION=2.10.7 -t hibiscus:2.10.7 .

# Multi-platform build (requires Buildx)
docker buildx build --platform linux/amd64,linux/arm64 -t hibiscus:local .
```

---

## Testing

### Provisioning script (pytest)

```bash
pip install -r provision/requirements.txt pytest
pytest tests/test_provision.py -v
```

### Container structure tests

Requires [container-structure-test](https://github.com/GoogleContainerTools/container-structure-test).

```bash
docker build -t hibiscus:test .
container-structure-test test --image hibiscus:test --config tests/container-structure-test.yml
```

Both test suites run automatically in CI on every push and pull request.

---

## Environment Variables

| Variable            | Default                  | Description                              |
|---------------------|--------------------------|------------------------------------------|
| `SECRETS_PATH`      | `/opt/hibiscus/secrets`  | Host directory containing secret files   |
| `JAMEICA_DATA_PATH` | `/opt/hibiscus/data`     | Host directory for persistent Jameica data |
| `HIBISCUS_PORT`     | `8888`                   | Host port to expose                      |

Example `.env` file:

```env
SECRETS_PATH=/opt/hibiscus/secrets
JAMEICA_DATA_PATH=/opt/hibiscus/data
HIBISCUS_PORT=8888
```

---

## Secrets

The following files must be present in `SECRETS_PATH` and are mounted read-only:

| File                          | Purpose                             |
|-------------------------------|-------------------------------------|
| `pwd`                         | Hibiscus master password            |
| `HBCIDBService.properties`    | HBCI database connection settings  |
| `PinTanConfig.properties`     | PIN/TAN passport configuration      |

Dummy templates are provided in the `secrets/` directory of this repository.

---

## Upgrading Hibiscus

Update `HIBISCUS_VERSION` in `docker-compose.yml`, then rebuild:

```bash
docker compose build --no-cache
docker compose up -d
```

Or pass the version directly at build time:

```bash
docker build --build-arg HIBISCUS_VERSION=2.10.8 -t hibiscus:2.10.8 .
```

---

## Troubleshooting

**Container exits immediately**
- Verify all three secret files exist and are correctly mounted.
- Run `docker logs hibiscus` for details.

**Port already in use**
- Set `HIBISCUS_PORT` in your `.env` file to a free port.

**Arm64 / Raspberry Pi issues**
- Use the pre-built multi-arch image from GHCR — it includes native `linux/arm64` layers and does not require emulation.

**Health check failing**
- The server needs ~60 seconds to start. The health check has a `start_period` of 60s — give it time before investigating.

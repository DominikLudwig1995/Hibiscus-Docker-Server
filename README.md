# Hibiscus Docker Server

[![Build & Publish Docker Image](https://github.com/DominikLudwig1995/Hibiscus-Docker-Server/actions/workflows/docker-image.yml/badge.svg)](https://github.com/DominikLudwig1995/Hibiscus-Docker-Server/actions/workflows/docker-image.yml)
[![GitHub Container Registry](https://img.shields.io/badge/ghcr.io-dominikludwig1995%2Fhibiscus-blue?logo=github)](https://github.com/DominikLudwig1995/Hibiscus-Docker-Server/pkgs/container/hibiscus)
[![License](https://img.shields.io/github/license/DominikLudwig1995/Hibiscus-Docker-Server)](LICENSE)
[![Ubuntu 24.04](https://img.shields.io/badge/ubuntu-24.04-orange?logo=ubuntu)](https://hub.docker.com/_/ubuntu)

Dockerized [Hibiscus Server](https://www.willuhn.de/products/hibiscus-server/) — a self-hosted HBCI/FinTS online banking server.  
Runs on `linux/amd64` and `linux/arm64` (Raspberry Pi, Apple Silicon).  
Pre-built images are published to the GitHub Container Registry on every push to `main`.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [Building Locally](#building-locally)
- [Environment Variables](#environment-variables)
- [Secrets](#secrets)
- [Upgrading Hibiscus](#upgrading-hibiscus)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

Pull the pre-built image and start the server with dummy secrets for local testing:

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

## Configuration

### Production (Raspberry Pi / home server)

1. Copy your secrets to the server:

```bash
scp secrets/ pi@<your-server>:/home/pi/secrets/
```

2. Start the stack:

```bash
docker compose up -d
```

The default volume paths expect secrets at `/home/pi/secrets/` and Jameica data at `/home/pi/.jameica`.  
Override them with environment variables — see [Environment Variables](#environment-variables).

---

## Building Locally

```bash
# Build with default Hibiscus version
docker build -t hibiscus:latest .

# Build with a specific version
docker build --build-arg HIBISCUS_VERSION=2.10.7 -t hibiscus:2.10.7 .

# Multi-platform build (requires Buildx)
docker buildx build --platform linux/amd64,linux/arm64 -t hibiscus:latest .
```

---

## Environment Variables

| Variable            | Default              | Description                            |
|---------------------|----------------------|----------------------------------------|
| `SECRETS_PATH`      | `/home/pi/secrets`   | Host directory containing secret files |
| `JAMEICA_DATA_PATH` | `/home/pi/.jameica`  | Host directory for persistent Jameica data |
| `HIBISCUS_PORT`     | `8888`               | Host port to expose                    |

Example `.env` file:

```env
SECRETS_PATH=/opt/hibiscus/secrets
JAMEICA_DATA_PATH=/opt/hibiscus/data
HIBISCUS_PORT=8888
```

---

## Secrets

The following files must be mounted as volumes:

| File                          | Purpose                              |
|-------------------------------|--------------------------------------|
| `pwd`                         | Hibiscus master password             |
| `HBCIDBService.properties`    | HBCI database connection settings   |
| `PinTanConfig.properties`     | PIN/TAN passport configuration       |

Dummy templates are provided in the `secrets/` directory.

---

## Upgrading Hibiscus

Update the `HIBISCUS_VERSION` build arg in `docker-compose.yml`, then rebuild:

```bash
docker compose build --no-cache
docker compose up -d
```

Or set the version via the build arg directly:

```bash
docker build --build-arg HIBISCUS_VERSION=2.10.8 -t hibiscus:2.10.8 .
```

---

## Troubleshooting

**Container exits immediately**
- Check that all three secret files are present and correctly mounted.
- Run `docker logs hibiscus` for details.

**Port already in use**
- Change `HIBISCUS_PORT` in your `.env` file.

**Arm64 / Raspberry Pi issues**
- Use the pre-built multi-arch image from GHCR — it includes native `linux/arm64` layers.

**Health check failing**
- The server needs ~60 seconds to start. The health check has a `start_period` of 60s.

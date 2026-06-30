# ── Stage 1: hibiscus-fetch ───────────────────────────────────────────────────
FROM ubuntu:26.04 AS hibiscus-fetch

ARG HIBISCUS_VERSION=2.12.4
ARG MARIADB_CONNECTOR_VERSION=3.5.3
ARG POSTGRES_DRIVER_VERSION=42.7.7

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends wget unzip ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /build

RUN wget -q \
        "https://www.willuhn.de/products/hibiscus-server/releases/hibiscus-server-${HIBISCUS_VERSION}.zip" \
        -O hibiscus.zip && \
    unzip -q hibiscus.zip && \
    rm hibiscus.zip && \
    rm -f hibiscus-server/jameicaserver.exe hibiscus-server/jameica-win32.jar

# Replace bundled MySQL jars with MariaDB + PostgreSQL JDBC drivers
RUN rm -f hibiscus-server/lib/mysql/* && \
    wget -q \
        "https://repo1.maven.org/maven2/org/mariadb/jdbc/mariadb-java-client/${MARIADB_CONNECTOR_VERSION}/mariadb-java-client-${MARIADB_CONNECTOR_VERSION}.jar" \
        -P hibiscus-server/lib/mysql/ && \
    wget -q \
        "https://repo1.maven.org/maven2/org/postgresql/postgresql/${POSTGRES_DRIVER_VERSION}/postgresql-${POSTGRES_DRIVER_VERSION}.jar" \
        -P hibiscus-server/lib/mysql/

# ── Stage 2: python-venv ──────────────────────────────────────────────────────
FROM ubuntu:26.04 AS python-venv

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends python3 python3-venv python3-pip && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY provision/requirements.txt /tmp/requirements.txt

RUN python3 -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt

# ── Stage 3: runtime ──────────────────────────────────────────────────────────
FROM ubuntu:26.04

ARG USERNAME=hibiscus
ARG USER_UID=1000
ARG USER_GID=1000

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

LABEL org.opencontainers.image.title="Hibiscus Server" \
      org.opencontainers.image.description="Dockerized HBCI/FinTS online banking server" \
      org.opencontainers.image.source="https://github.com/DominikLudwig1995/Hibiscus-Docker-Server" \
      org.opencontainers.image.licenses="MIT"

# Ubuntu 26.04 ships an 'ubuntu' user at UID/GID 1000; remove it so we can
# claim those IDs for the hibiscus service user.
RUN userdel -r ubuntu 2>/dev/null || true && \
    groupdel ubuntu  2>/dev/null || true && \
    groupadd --gid  "$USER_GID" "$USERNAME" && \
    useradd  --uid  "$USER_UID" --gid "$USER_GID" --create-home --no-log-init "$USERNAME"

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        default-jre-headless \
        python3 \
        wget \
        ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY --from=python-venv /opt/venv /opt/venv
COPY --chown=$USERNAME:$USERNAME provision/ /opt/provision/
COPY --from=hibiscus-fetch --chown=$USERNAME:$USERNAME /build/hibiscus-server \
    /home/$USERNAME/hibiscus-server
COPY --chown=$USERNAME:$USERNAME files/UpdateService.properties \
    /home/$USERNAME/hibiscus-server/cfg/de.willuhn.jameica.services.UpdateService.properties

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh \
              /home/$USERNAME/hibiscus-server/jameicaserver.sh

USER $USERNAME
WORKDIR /home/$USERNAME

EXPOSE 8888

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD wget -qO- http://localhost:8888/ || exit 1

ENTRYPOINT ["/entrypoint.sh"]

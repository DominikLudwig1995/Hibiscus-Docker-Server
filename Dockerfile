# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM ubuntu:24.04 AS builder

ARG HIBISCUS_VERSION=2.10.7
ARG MARIADB_CONNECTOR_VERSION=3.4.1

RUN apt-get update && \
    apt-get install -y --no-install-recommends wget unzip ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Download and unpack Hibiscus
RUN wget -q "https://www.willuhn.de/products/hibiscus-server/releases/hibiscus-server-${HIBISCUS_VERSION}.zip" \
        -O hibiscus.zip && \
    unzip -q hibiscus.zip && \
    rm hibiscus.zip

# Remove Windows-only artefacts
RUN rm -f hibiscus-server/jameicaserver.exe \
          hibiscus-server/jameica-win32.jar

# Replace bundled MySQL jars with a single up-to-date MariaDB connector
RUN rm -f hibiscus-server/lib/mysql/* && \
    wget -q "https://repo1.maven.org/maven2/org/mariadb/jdbc/mariadb-java-client/${MARIADB_CONNECTOR_VERSION}/mariadb-java-client-${MARIADB_CONNECTOR_VERSION}.jar" \
        -P hibiscus-server/lib/mysql/

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM ubuntu:24.04

ARG USERNAME=hibiscus
ARG USER_UID=1000
ARG USER_GID=1000

# Create non-root user
RUN groupadd --gid $USER_GID $USERNAME && \
    useradd --uid $USER_UID --gid $USER_GID -m $USERNAME

# Runtime dependencies only — no build tools
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        default-jre-headless \
        wget \
        ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

USER $USERNAME
WORKDIR /home/$USERNAME

# Copy prepared Hibiscus installation from builder
COPY --from=builder --chown=$USERNAME:$USERNAME /build/hibiscus-server ./hibiscus-server

# Bake in static configuration (non-secret)
COPY --chown=$USERNAME:$USERNAME files/UpdateService.properties \
    hibiscus-server/cfg/de.willuhn.jameica.services.UpdateService.properties
COPY --chown=$USERNAME:$USERNAME files/Plugin.properties \
    hibiscus-server/cfg/de.willuhn.jameica.webadmin.Plugin.properties

RUN chmod +x hibiscus-server/jameicaserver.sh

EXPOSE 8888

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD wget -qO- http://localhost:8888/ || exit 1

CMD ["./hibiscus-server/jameicaserver.sh", "-w", "/run/secret/pwd"]

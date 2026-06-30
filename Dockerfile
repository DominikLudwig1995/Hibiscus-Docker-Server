FROM ubuntu:24.04

# Use the following image for arm-based systems
# FROM arm64v8/ubuntu:24.04

# Variables
ARG HIBISCUS_VERSION=2.10.7
ARG MARIADB_CONNECTOR_VERSION=3.4.1
ARG USERNAME=hibiscus
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# Create the user
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME

# Install packages
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        default-jre \
        wget \
        unzip \
        libmariadb-java && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Switch to hibiscus user
USER $USERNAME
WORKDIR /home/hibiscus/

# Install hibiscus server
RUN wget -q https://www.willuhn.de/products/hibiscus-server/releases/hibiscus-server-${HIBISCUS_VERSION}.zip -P /home/hibiscus/ && \
    unzip -q hibiscus-server-${HIBISCUS_VERSION}.zip -d /home/hibiscus/ && \
    rm hibiscus-server-${HIBISCUS_VERSION}.zip && \
    rm -f hibiscus-server/lib/mysql/* && \
    wget -q https://repo1.maven.org/maven2/org/mariadb/jdbc/mariadb-java-client/${MARIADB_CONNECTOR_VERSION}/mariadb-java-client-${MARIADB_CONNECTOR_VERSION}.jar \
        -P hibiscus-server/lib/mysql && \
    rm -f hibiscus-server/jameicaserver.exe \
          hibiscus-server/jameica-win32.jar

# Add hibiscus configuration
COPY files/UpdateService.properties hibiscus-server/cfg/de.willuhn.jameica.services.UpdateService.properties
COPY files/Plugin.properties hibiscus-server/cfg/de.willuhn.jameica.webadmin.Plugin.properties

# Run hibiscus
RUN chmod +x hibiscus-server/jameicaserver.sh

EXPOSE 8888

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD wget -qO- http://localhost:8888/ || exit 1

CMD ["./hibiscus-server/jameicaserver.sh", "-w", "/run/secret/pwd"]

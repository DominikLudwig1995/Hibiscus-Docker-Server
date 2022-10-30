#FROM ubuntu:22.04
FROM tianon/raspbian:buster-slim

# Variables
ARG HIBISCUS_VERSION=2.10.7
ARG USERNAME=hibiscus
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# Create the user
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME 

# Install packages
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y default-jre wget unzip vim libmariadb-java 

# Switch to hibiscus user
USER $USERNAME
WORKDIR /home/hibiscus/

# Install hibiscus server
RUN wget https://www.willuhn.de/products/hibiscus-server/releases/hibiscus-server-${HIBISCUS_VERSION}.zip -P /home/hibiscus/ && \
    unzip hibiscus-server-${HIBISCUS_VERSION}.zip -d /home/hibiscus/  && rm hibiscus-server-${HIBISCUS_VERSION}.zip && \
     rm hibiscus-server/lib/mysql/* && \
     wget https://repo1.maven.org/maven2/org/mariadb/jdbc/mariadb-java-client/3.0.4/mariadb-java-client-3.0.4.jar -P hibiscus-server/lib/mysql && \
     wget https://repo1.maven.org/maven2/org/mariadb/jdbc/mariadb-java-client/2.4.4/mariadb-java-client-2.4.4.jar -P hibiscus-server/lib/mysql  && \
     wget https://repo1.maven.org/maven2/mysql/mysql-connector-java/5.1.49/mysql-connector-java-5.1.49.jar -P hibiscus-server/lib/mysql

# Add hibiscus configuration
ADD files/UpdateService.properties hibiscus-server/cfg/de.willuhn.jameica.services.UpdateService.properties
ADD files/Plugin.properties hibiscus-server/cfg/de.willuhn.jameica.webadmin.Plugin.properties

# Remove windows bin
RUN rm hibiscus-server/jameicaserver.exe && \
    rm hibiscus-server/jameica-win32.jar

# Run hibiscus
RUN chmod +x "hibiscus-server/jameicaserver.sh"
CMD ["./hibiscus-server/jameicaserver.sh","-w","/run/secret/pwd"]

# Expose new hibiscus port
EXPOSE 8888
#FROM ubuntu:22.04
FROM tianon/raspbian:buster-slim

ARG HIBISCUS_VERSION=2.10.7

RUN apt update && \
    apt install -y default-jre wget unzip

RUN wget https://www.willuhn.de/products/hibiscus-server/releases/hibiscus-server-${HIBISCUS_VERSION}.zip && \
    unzip hibiscus-server-${HIBISCUS_VERSION}.zip -d / && rm hibiscus-server-${HIBISCUS_VERSION}.zip && \
    wget https://repo1.maven.org/maven2/org/mariadb/jdbc/mariadb-java-client/3.0.8/mariadb-java-client-3.0.8.jar -P hibiscus-server/lib/mysql/  && \
    wget https://repo1.maven.org/maven2/com/mysql/mysql-connector-j/8.0.31/mysql-connector-j-8.0.31.jar -P hibiscus-server/lib/mysql

ADD files/UpdateService.properties hibiscus-server/cfg/de.willuhn.jameica.services.UpdateService.properties
ADD files/Plugin.properties hibiscus-server/cfg/de.willuhn.jameica.webadmin.Plugin.properties

RUN rm hibiscus-server/jameicaserver.exe
RUN rm hibiscus-server/jameica-win32.jar
RUN chmod +x "/hibiscus-server/jameicaserver.sh"

CMD ["./hibiscus-server/jameicaserver.sh","-w","/run/secret/pwd"]

EXPOSE 8888
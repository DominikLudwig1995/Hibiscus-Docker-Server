#FROM ubuntu:22.04
FROM tianon/raspbian:buster-slim

ARG HIBISCUS_VERSION=2.10.7

RUN apt update && \
    apt install -y default-jre wget unzip vim libmariadb-java 
RUN wget https://www.willuhn.de/products/hibiscus-server/releases/hibiscus-server-${HIBISCUS_VERSION}.zip && \
     unzip hibiscus-server-${HIBISCUS_VERSION}.zip -d / && rm hibiscus-server-${HIBISCUS_VERSION}.zip && \
     rm hibiscus-server/lib/mysql/* && \
     wget https://repo1.maven.org/maven2/org/mariadb/jdbc/mariadb-java-client/3.0.4/mariadb-java-client-3.0.4.jar -P hibiscus-server/lib/mysql && \
     wget https://repo1.maven.org/maven2/org/mariadb/jdbc/mariadb-java-client/2.4.4/mariadb-java-client-2.4.4.jar -P hibiscus-server/lib/mysql  && \
     wget https://repo1.maven.org/maven2/mysql/mysql-connector-java/5.1.49/mysql-connector-java-5.1.49.jar -P hibiscus-server/lib/mysql

ADD files/UpdateService.properties hibiscus-server/cfg/de.willuhn.jameica.services.UpdateService.properties
ADD files/Plugin.properties hibiscus-server/cfg/de.willuhn.jameica.webadmin.Plugin.properties

RUN rm hibiscus-server/jameicaserver.exe && \
    rm hibiscus-server/jameica-win32.jar

WORKDIR /hibiscus-server/

RUN chmod +x "jameicaserver.sh"
RUN groupadd -r hibiscus && useradd --no-log-init -r -g hibiscus hibiscus

USER hibiscus

CMD ["./jameicaserver.sh","-w","/run/secret/pwd"]

EXPOSE 8888
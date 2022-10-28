FROM ubuntu:22.04

ARG HIBISCUS_VERSION=2.10.7
ENV PASSWORD 123

RUN apt update && \
    apt install -y default-jre wget unzip

RUN wget https://www.willuhn.de/products/hibiscus-server/releases/hibiscus-server-${HIBISCUS_VERSION}.zip
RUN unzip hibiscus-server-${HIBISCUS_VERSION}.zip -d / && rm hibiscus-server-${HIBISCUS_VERSION}.zip

ADD files/HBCIDBService.properties hibiscus-server/cfg/de.willuhn.jameica.hbci.rmi.HBCIDBService.properties
ADD files/UpdateService.properties hibiscus-server/cfg/de.willuhn.jameica.services.UpdateService.properties
ADD files/Plugin.properties hibiscus-server/cfg/de.willuhn.jameica.webadmin.Plugin.properties

RUN rm hibiscus-server/jameicaserver.exe

ENTRYPOINT ["echo ${PASSWORD} | ./hibiscus-server/jameicaserver.sh"]

EXPOSE 8888
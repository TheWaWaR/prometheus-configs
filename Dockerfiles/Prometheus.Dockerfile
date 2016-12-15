FROM ubuntu:16.04

ENV VERSION="1.4.1"

RUN apt-get update \
    && apt-get install -y wget \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* \
    && cd /mnt \
    && wget https://github.com/prometheus/prometheus/releases/download/v${VERSION}/prometheus-${VERSION}.linux-amd64.tar.gz \
    && tar -xf prometheus-${VERSION}.linux-amd64.tar.gz \
    && mv prometheus-${VERSION}.linux-amd64 /opt/prometheus \
    && rm /mnt/*.tar.gz

VOLUME /etc/prometheus
VOLUME /mnt/data

CMD ["/opt/prometheus/prometheus", \
     "-config.file=/etc/prometheus/prometheus.yml", \
     "-storage.local.path=/mnt/data"]

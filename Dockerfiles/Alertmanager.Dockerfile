FROM ubuntu:16.04

ENV VERSION="0.5.1"

RUN apt-get update \
    && apt-get install -y wget \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* \
    && cd /mnt \
    && wget https://github.com/prometheus/alertmanager/releases/download/v${VERSION}/alertmanager-${VERSION}.linux-amd64.tar.gz \
    && tar -xf alertmanager-${VERSION}.linux-amd64.tar.gz \
    && mv alertmanager-${VERSION}.linux-amd64 /opt/alertmanager \
    && rm /mnt/*.tar.gz

VOLUME /etc/alertmanager
VOLUME /mnt/data

CMD ["/opt/alertmanager/alertmanager", \
     "-config.file=/etc/alertmanager/alertmanager.yml", \
     "-storage.path=/mnt/data"]

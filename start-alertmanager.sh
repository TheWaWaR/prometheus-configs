docker run -v `pwd`/data/alertmanager:/mnt/data -v `pwd`:/etc/alertmanager -p 0.0.0.0:9093:9093 -d alertmanager:v1

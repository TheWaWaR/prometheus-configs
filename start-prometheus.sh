docker run -v `pwd`/data/prometheus:/mnt/data -v `pwd`:/etc/prometheus -p 0.0.0.0:9099:9090 -d prometheus:v1

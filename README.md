# hibiscus-docker-server

Build
```
docker build -t hibiscus:latest .
or
docker-compose build
```

Configure
```
cp ./secret /home/pi/secrets
```

Run
```
docker-compose up -d
or
docker run -it hibiscus bash
```
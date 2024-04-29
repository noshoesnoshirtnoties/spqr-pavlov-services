# SPQR Pavlov Services

## description
this repo contains everything needed to rollout and run pavlov vr custom servers for SPQR, as well as a discord bot, using docker.

## requirements
* a debian or ubuntu server with docker, accessible as root or with root privs
* a mysqldb (see database_template.sql)

## config
### pavlov-server
before deployment, each server requires a folder named after its "server number" or "slot", which can be 0-9.

this is an example folder structure for 2 servers (0+1):
```
pavlov-server/
├── conf.d
│   ├── 0
│   │   └── Game.ini
│   ├── 1
│   │   └── Game.ini
│   ├── blacklist.txt
│   ├── mods.txt
│   ├── RconSettings.txt
│   └── whitelist.txt
```

### praefectus
the monitoring service can be configured via its config file "pavlov-server/praefectus/config.json".

an example configuriation for 2 servers (0+1) can be found in "pavlov-server/praefectus/config.json.example".

### servus-publicus
the discord bot can be configured via its config file "servus-publicus/config.json".

an example configuration can be found in "servus-publicus/config.json".

## deployment
### pavlov-server-deploy.sh
a server (0 in this example) and its monitoring service named "praefectus" can be deployed to a target server like this:
```
./pavlov-server-deploy.sh -d spqr-server -s 0 -u root -v
```

### servus-publicus-deploy.sh
the discord bot can be deployed to a target server like this:
```
./servus-publicus-deploy.sh -d spqr-server -u root -v
```

## example commands for service handling
### general
```
docker stats
watch -n 1 'docker ps --format "{{.ID}} {{.Status}} {{.Names}}"'
```

### pavlov-server #0
```
docker exec -it pavlov-server-0 bash
docker exec -it pavlov-server-0 bash -c 'tail -f /home/steam/pavlovserver/Pavlov/Saved/Logs/Pavlov.log'

```

### pavlov-server-praefectus #0
```
docker exec -it pavlov-server-praefectus-0 bash
docker exec -it pavlov-server-praefectus-0 bash -c 'tail -f /opt/pavlov-server/praefectus/praefectus.log'
docker exec -it pavlov-server-praefectus-0 bash -c 'tail -f /opt/pavlov-server/praefectus/praefectus.log | grep -v "RCON\|DEBUG\|heartbeat"'
```

### servus-publicus
```
docker exec -it servus-publicus bash
docker exec -it servus-publicus bash -c 'tail -f /opt/servus-publicus/servus-publicus.log'
```
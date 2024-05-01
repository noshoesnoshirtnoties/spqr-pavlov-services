# SPQR Pavlov Services

## description
this repo contains everything needed to rollout and run pavlov vr custom servers for SPQR, as well as a discord bot, using docker.

* "pavlov-server" is the pavlov vr custom server
* "praefectus" is the monitoring service for the game servers
* "servus-publicus" is the discord bot

## requirements
* a debian or ubuntu server with docker, accessible as root or with root privs
* a mysqldb (see database_template.sql)

## config
### pavlov-server
before deployment, each server requires a folder named after its "server number" or "slot", which can be 0-9.

an example configuriation for 1 server (0) can be found in "pavlov-server/conf.d.example/".

this is an example folder structure for 2 servers (0+1):
```
pavlov-server
├── conf.d
│   ├── 0
│   │   ├── Game.ini
│   │   └── RconSettings.txt
│   ├── 1
│   │   ├── Game.ini
│   │   └── RconSettings.txt
│   ├── blacklist.txt
│   ├── mods.txt
│   └── whitelist.txt
```

### praefectus
the monitoring service can be configured via its config file "pavlov-server/praefectus/config.json".

an example configuriation for 2 servers (0+1) can be found in "pavlov-server/praefectus/config.json.example".

### servus-publicus
the discord bot can be configured via its config file "servus-publicus/config.json".

an example configuration can be found in "servus-publicus/config.json.example".

## deployment
### pavlov-server-deploy.sh
a server (0 in this example) and its monitoring service named "praefectus" can be deployed to a target server like this:
```
./pavlov-server-deploy.sh -d spqr-server -s 0 -u root
```

this is an example for deploying multiple servers in one go (and without being asked for confirmation each time):
```
./pavlov-server-deploy.sh -d spqr-server -s 0 -u root -y; \
./pavlov-server-deploy.sh -d spqr-server -s 1 -u root -y; \
./pavlov-server-deploy.sh -d spqr-server -s 2 -u root -y; \
./pavlov-server-deploy.sh -d spqr-server -s 3 -u root -y; \
./pavlov-server-deploy.sh -d spqr-server -s 4 -u root -y; \
./pavlov-server-deploy.sh -d spqr-server -s 5 -u root -y; \
./pavlov-server-deploy.sh -d spqr-server -s 6 -u root -y;
```

#### praefectus only
to only deploy the praefectus service, not touching the pavlov-server, use the "-p" flag like this:
```
./pavlov-server-deploy.sh -d spqr-server -s 0 -u root -p
```

### servus-publicus-deploy.sh
the discord bot can be deployed to a target server like this:
```
./servus-publicus-deploy.sh -d spqr-server -u root
```

## example commands for service handling
### general
```
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
docker exec -it pavlov-server-praefectus-0 bash -c 'tail -f /opt/pavlov-server/praefectus/praefectus-0.log'
```

### servus-publicus
```
docker exec -it servus-publicus bash
docker exec -it servus-publicus bash -c 'tail -f /opt/servus-publicus/servus-publicus.log'
```

## todo
* logrotate
* cron-triggered pav-server update
* cron-triggered weekly container redeploy / image recreate / volume recreate

## more info
* http://pavlovwiki.com/index.php/Setting_up_a_dedicated_server
* http://pavlovwiki.com/index.php/Rcon_Overview_and_Commands
* https://mod.io/g/pavlov/m/rcon-plus
* https://mod.io/g/pavlov/m/mod-hc-pavlov
* https://github.com/noshoesnoshirtnoties/PavlovVRBalancingTable
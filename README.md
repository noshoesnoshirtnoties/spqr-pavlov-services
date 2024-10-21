# SPQR Pavlov Services

## description
this repo contains everything needed to rollout and run pavlov vr custom servers, as well as a discord bot. to get started, clone this repo to your system and keep reading in order to use it :)

* "pavlov-server" is the pavlov vr custom server
* "praefectus" is the monitoring service for the game servers
* "servus-publicus" is the discord bot

## requirements
* a debian or ubuntu server, accessible as root or with root privs
* a mysqldb (see database_template.sql)
* python3

## config
### pavlov-server
before deployment, each server requires a folder named after its "server number" (#), which can be 0-9.

an example configuriation for 1 server (#0) can be found in "pavlov-server/conf.d.example/".

this is an example folder structure for 2 servers (#0 + #1):
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

an example configuriation for 2 servers (#0 + #1) can be found in "pavlov-server/praefectus/config.json.example".

### servus-publicus
the discord bot can be configured via its config file "servus-publicus/config.json".

an example configuration can be found in "servus-publicus/config.json.example".

## deployment
### pavlov-server-deploy.sh
a server - #0 in this example - and its monitoring service named "praefectus" can be deployed to a target server like this:
```
./pavlov-server-deploy.sh -d myfancyserver.com -s 0
```

this is an example for deploying multiple servers in one go (and without being asked for confirmation each time):
```
./pavlov-server-deploy.sh -d myfancyserver.com -s 0 -y; \
./pavlov-server-deploy.sh -d myfancyserver.com -s 1 -y; \
./pavlov-server-deploy.sh -d myfancyserver.com -s 2 -y; \
./pavlov-server-deploy.sh -d myfancyserver.com -s 3 -y; \
./pavlov-server-deploy.sh -d myfancyserver.com -s 4 -y; \
./pavlov-server-deploy.sh -d myfancyserver.com -s 5 -y; \
./pavlov-server-deploy.sh -d myfancyserver.com -s 6 -y; \
./pavlov-server-deploy.sh -d myfancyserver.com -s 7 -y; \
./pavlov-server-deploy.sh -d myfancyserver.com -s 8 -y; \
./pavlov-server-deploy.sh -d myfancyserver.com -s 9 -y;
```

#### praefectus only
to only deploy the praefectus service, not touching the pavlov-server, use the "-p" flag like this:
```
./pavlov-server-deploy.sh -d myfancyserver.com -s 0 -p
```

### servus-publicus-deploy.sh
the discord bot can be deployed to a target server like this:
```
./servus-publicus-deploy.sh -d myfancyserver.com
```

## todo
* general
  * cron-triggered restart
  * top ranks in #stats
  * extended playerstats (another service for stats log?)
    * pull steamusers details
    * ace-detection
  * add elo/mmr
* pavlov-server
  * enable demo
* praefectus
  * fix playercount with demo / get demo via rcon
* servus-publicus
  * ...

## more
### info
* https://github.com/noshoesnoshirtnoties/PavlovVRBalancingTable
* http://pavlovwiki.com/index.php/Setting_up_a_dedicated_server
* http://pavlovwiki.com/index.php/Rcon_Overview_and_Commands
* https://mod.io/g/pavlov/m/rcon-plus

### additional mods
* https://mod.io/g/pavlov/m/pavlovartists-weapon-skin-pack
* https://mod.io/g/pavlov/m/skins-kennithhs-usmc
* https://mod.io/g/pavlov/m/skins-kennithhs-raf
* https://mod.io/g/pavlov/m/skins-kennithhs-vietnam-us
* https://mod.io/g/pavlov/m/skins-kennithhs-vietnam-nva
* https://mod.io/g/pavlov/m/colonists-ww2-avatars
* https://mod.io/g/pavlov/m/gun-kennithhs-modern-weapons
* https://mod.io/g/pavlov/m/gun-kennithhs-vietnam-weapons
* https://mod.io/g/pavlov/m/gun-kennithhs-wwii-weapons-pack1
* https://mod.io/g/pavlov/m/colonists-ww1-guns-pack
* https://mod.io/g/pavlov/m/colonists-ww2-pack
* https://mod.io/g/pavlov/m/colonists-guns-pack
* https://mod.io/g/pavlov/m/gun-thompson-and-ppsh-with-drummags
* https://mod.io/g/pavlov/m/minigun
* https://mod.io/g/pavlov/m/msbs
* https://mod.io/g/pavlov/m/random-gun-on-kill1
* https://mod.io/g/pavlov/m/chicken-on-death
* https://mod.io/g/pavlov/m/mod-team-arm-band
* https://mod.io/g/pavlov/m/fullcash
* https://mod.io/g/pavlov/m/regen
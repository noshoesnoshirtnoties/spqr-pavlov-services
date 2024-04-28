#!/usr/bin/env bash

VERSION=1.0
USAGE="
Usage: $0 -d <dsthost> -n <numsrv> -u <sshuser> -v\n
-d destination host\n
-n number of servers (0-9)\n
-u ssh/scp user\n
-v verbose output"


# --- options processing ---

if [ $# == 0 ] ; then
    echo -e $USAGE; exit 1;
fi

while getopts ":d:n:u:v" optname
  do
    case "$optname" in
      "v")
        echo "[INFO] verbose mode active"
        VERBOSE=true
        ;;
      "d")
        DSTHOST=$OPTARG
        ;;
      "n")
        NUMSRV=$OPTARG
        ;;
      "u")
        SSHUSER=$OPTARG
        ;;
      "?")
        echo "[ERROR] unknown option $OPTARG - exiting"
        exit 1;
        ;;
      ":")
        echo "[ERROR] no argument value for option $OPTARG - exiting"
        exit 1;
        ;;
      *)
        echo "[ERROR] unknown error while processing options - exiting"
        exit 1;
        ;;
    esac
  done

shift $(($OPTIND - 1))


# --- body ---

read -s -n 1 -p "[WAIT] press any key to continue..." && echo ""
if [ $VERBOSE ]; then echo "[INFO] starting deployment"; fi

if [ -z $DSTHOST ]; then
  echo "[WARN] destination host is invalid - assuming 'spqr-server'"
  DSTHOST="spqr-server"
fi

if (( $NUMSRV < 1 )); then
  echo "[ERROR] given number of servers is invalid - exiting"; exit 1
elif (( $NUMSRV > 9 )); then
  echo "[ERROR] given number of servers is invalid - exiting"; exit 1
fi

if [ -z $SSHUSER ]; then
  echo "[WARN] ssh user is invalid - assuming 'root'"
  SSHUSER="root"
fi

SSHCMD="$(which ssh) -q -o StrictHostKeyChecking=no -A -F /home/${USER}/.ssh/config -l ${SSHUSER} "
SCPCMD="$(which scp) -r -F /home/${USER}/.ssh/config "


# --- pavlov-server ---

if [ $VERBOSE ]; then echo "[INFO] copying files for pavlov-server..."; fi
$SCPCMD -r "pavlov-server" "${SSHUSER}@${DSTHOST}:"

SRV=0
while [ $SRV -le $(( $NUMSRV - 1 )) ]; do

  PORT1=$((x=7777, y=$SRV, x+y))
  PORT2=$((x=$PORT1, y=400, x+y))
  PORTRCON=$((x=9100, y=$SRV, x+y))

  if [ $VERBOSE ]; then echo "[INFO] stopping running container..."; fi
  $SSHCMD $DSTHOST "docker stop pavlov-server-${SRV}"

  if [ $VERBOSE ]; then echo "[INFO] removing old container..."; fi
  $SSHCMD $DSTHOST "docker container rm pavlov-server-${SRV}"

  if [ $VERBOSE ]; then echo "[INFO] building docker image..."; fi
  $SSHCMD $DSTHOST "cd ~/pavlov-server && docker build -t pavlov-server ."

  if [ $VERBOSE ]; then echo "[INFO] starting docker container for pavlov-server-${SRV}..."; fi
  $SSHCMD $DSTHOST "docker run --name pavlov-server-${SRV} -d \
    -p ${PORT1}:7777/udp \
    -p ${PORT2}:8177/udp \
    -p ${PORTRCON}:9100/tcp \
    -v ~/pavlov-server/${SRV}/Game.ini:/home/steam/pavlovserver/Pavlov/Saved/Config/LinuxServer/Game.ini \
    -v ~/pavlov-server/${SRV}/mods.txt:/home/steam/pavlovserver/Pavlov/Saved/Config/mods.txt \
    -v ~/pavlov-server/${SRV}/RconSettings.txt:/home/steam/pavlovserver/Pavlov/Saved/Config/RconSettings.txt \
    -v ~/pavlov-server/${SRV}/blacklist.txt:/home/steam/pavlovserver/Pavlov/Saved/Config/blacklist.txt \
    -v ~/pavlov-server/${SRV}/whitelist.txt:/home/steam/pavlovserver/Pavlov/Saved/Config/whitelist.txt \
    --restart unless-stopped \
    pavlov-server"

  SRV=$(( $SRV + 1 ))

done


# --- servus-publicus ---

if [ $VERBOSE ]; then echo "[INFO] copying files for servus-publicus..."; fi
$SCPCMD -r "servus-publicus" "${SSHUSER}@${DSTHOST}:"


# --- done ---
if [ $VERBOSE ]; then echo "[INFO] exiting successfully"; fi
exit 0

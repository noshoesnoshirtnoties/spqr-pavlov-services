#!/usr/bin/env bash

VERSION=1.1
USAGE="
Usage: $0 -d <dsthost> -s <srv> -u <sshuser> -p -y\n
-d destination host\n
-s server number (0-9)\n
-u ssh/scp user\n
-p praefectus only\n
-y dont ask\n"


# --- options processing ---

if [ $# == 0 ] ; then
    echo -e $USAGE; exit 1;
fi

while getopts ":d:s:u:yp" optname
  do
    case "$optname" in
      "d")
        DSTHOST=$OPTARG
        ;;
      "s")
        SRV=$OPTARG
        ;;
      "u")
        SSHUSER=$OPTARG
        ;;
      "p")
        echo "[INFO] praefectus_only has been set"
        PRAEFECTUS_ONLY=true
        ;;
      "y")
        DONT_ASK=true
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

INSTALLDIR="/opt/"
SSHCMD="$(which ssh) -q -o StrictHostKeyChecking=no -A -F /home/${USER}/.ssh/config -l ${SSHUSER} "
SCPCMD="$(which scp) -r -F /home/${USER}/.ssh/config "

if [ -z $DSTHOST ]; then
  echo "[WARN] destination host is invalid - assuming 'spqr-server'"
  DSTHOST="spqr-server"
fi

if [ -z $SRV ]; then
  echo "[ERROR] server number is invalid - exiting"; exit 1
fi

if [ -z $SSHUSER ]; then
  echo "[WARN] ssh user is invalid - assuming 'root'"
  SSHUSER="root"
fi

PORT1=$((x=7777, y=$SRV, x+y))
PORT2=$((x=$PORT1, y=400, x+y))
PORTRCON=$((x=9100, y=$SRV, x+y))

if [ "$DONT_ASK" != true ]; then
  read -s -n 1 -p "[WAIT] press any key to continue..." && echo ""
fi
echo "[INFO] starting deployment"


# --- pavlov-server + praefectus ---

echo "[INFO] copying files..."
$SCPCMD -r "pavlov-server" "${SSHUSER}@${DSTHOST}:${INSTALLDIR}/"

echo "[INFO] chmod-ing Game.ini files..."
$SSHCMD $DSTHOST "find ${INSTALLDIR}pavlov-server/conf.d/ -type f -name 'Game.ini' -exec chmod 666 {} \;"

echo "[INFO] creating data volumes..."
$SSHCMD $DSTHOST "docker volume create pavlov-server-logs-${SRV}"
$SSHCMD $DSTHOST "docker volume create pavlov-server-maps"

echo "[INFO] stopping running containers..."
if [ "$PRAEFECTUS_ONLY" != true ]; then $SSHCMD $DSTHOST "docker stop pavlov-server-${SRV}"; fi
$SSHCMD $DSTHOST "docker stop pavlov-server-praefectus-${SRV}"

echo "[INFO] removing old containers..."
if [ "$PRAEFECTUS_ONLY" != true ]; then $SSHCMD $DSTHOST "docker container rm pavlov-server-${SRV}"; fi
$SSHCMD $DSTHOST "docker container rm pavlov-server-praefectus-${SRV}"

echo "[INFO] checking if ufw is active"
RESPONSE=$($SSHCMD $DSTHOST "ufw status")
if [[ $RESPONSE == *"active"* ]]; then
  echo "[INFO] ufw is active - setting rules now"
  $SSHCMD $DSTHOST "ufw allow ${PORT1}"
  $SSHCMD $DSTHOST "ufw allow ${PORT2}"
  $SSHCMD $DSTHOST "ufw allow ${PORTRCON}"
else
  echo "[WARN] ufw is inactive - please check if this is what you want"
fi

echo "[INFO] building docker image for praefectus..."
$SSHCMD $DSTHOST "cd ${INSTALLDIR}/pavlov-server/praefectus && docker build -t pavlov-server-praefectus ."

echo "[INFO] starting docker container..."
$SSHCMD $DSTHOST "docker run --name pavlov-server-praefectus-${SRV} -d \
  -v pavlov-server-logs-${SRV}:/opt/pavlov-server/praefectus/logs/ \
  -e SRV=${SRV} \
  --restart unless-stopped \
  --net=host \
  pavlov-server-praefectus"

if [ "$PRAEFECTUS_ONLY" != true ]; then 
  echo "[INFO] building docker image for pavlov-server..."
  $SSHCMD $DSTHOST "cd ${INSTALLDIR}/pavlov-server && docker build -t pavlov-server ."

  echo "[INFO] starting docker container..."
  $SSHCMD $DSTHOST "docker run --name pavlov-server-${SRV} -d \
    -p 0.0.0.0:${PORT1}:${PORT1}/udp \
    -p 0.0.0.0:${PORT2}:${PORT2}/udp \
    -p 0.0.0.0:${PORTRCON}:${PORTRCON}/tcp \
    -v ${INSTALLDIR}/pavlov-server/conf.d/$SRV/Game.ini:/home/steam/pavlovserver/Pavlov/Saved/Config/LinuxServer/Game.ini \
    -v ${INSTALLDIR}/pavlov-server/conf.d/$SRV/RconSettings.txt:/home/steam/pavlovserver/Pavlov/Saved/Config/RconSettings.txt \
    -v pavlov-server-logs-${SRV}:/home/steam/pavlovserver/Pavlov/Saved/Logs \
    -v pavlov-server-maps:/home/steam/pavlovserver/Pavlov/Saved/maps \
    -e SRV=${SRV} \
    -e PORT=${PORT1} \
    --restart unless-stopped \
    pavlov-server"
fi


# --- done ---

echo "[INFO] exiting successfully"
exit 0

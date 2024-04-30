#!/usr/bin/env bash

VERSION=1.0
USAGE="
Usage: $0 -d <dsthost> -u <sshuser> -y\n
-d destination host\n
-u ssh/scp user\n
-y dont ask\n"


# --- options processing ---

if [ $# == 0 ] ; then
    echo -e $USAGE; exit 1;
fi

while getopts ":d:u:y" optname
  do
    case "$optname" in
      "d")
        DSTHOST=$OPTARG
        ;;
      "u")
        SSHUSER=$OPTARG
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

if [ -z $SSHUSER ]; then
  echo "[WARN] ssh user is invalid - assuming 'root'"
  SSHUSER="root"
fi

if [ "$DONT_ASK" != true ]; then
  read -s -n 1 -p "[WAIT] press any key to continue..." && echo ""
fi
echo "[INFO] starting deployment"


# --- servus-publicus ---

echo "[INFO] stopping running container..."
$SSHCMD $DSTHOST "docker stop servus-publicus"

echo "[INFO] removing old container..."
$SSHCMD $DSTHOST "docker container rm servus-publicus"

echo "[INFO] copying files..."
$SCPCMD -r "servus-publicus" "${SSHUSER}@${DSTHOST}:${INSTALLDIR}/"

echo "[INFO] building docker image..."
$SSHCMD $DSTHOST "cd ${INSTALLDIR}/servus-publicus && docker build -t servus-publicus ."

echo "[INFO] starting docker container..."
$SSHCMD $DSTHOST "docker run --name servus-publicus -d \
  --restart unless-stopped \
  --net=host \
  servus-publicus"


# --- done ---

echo "[INFO] exiting successfully"
exit 0

#!/usr/bin/env bash

VERSION=1.0
USAGE="
Usage: $0 -d <dsthost> -u <sshuser> -v\n
-d destination host\n
-u ssh/scp user\n
-v verbose output\n"


# --- options processing ---

if [ $# == 0 ] ; then
    echo -e $USAGE; exit 1;
fi

while getopts ":d:u:v" optname
  do
    case "$optname" in
      "v")
        echo "[INFO] verbose mode active"
        VERBOSE=true
        ;;
      "d")
        DSTHOST=$OPTARG
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

read -s -n 1 -p "[WAIT] press any key to continue..." && echo ""
if [ $VERBOSE ]; then echo "[INFO] starting deployment"; fi


# --- servus-publicus ---

if [ $VERBOSE ]; then echo "[INFO] stopping running container..."; fi
$SSHCMD $DSTHOST "docker stop servus-publicus"

if [ $VERBOSE ]; then echo "[INFO] removing old container..."; fi
$SSHCMD $DSTHOST "docker container rm servus-publicus"

if [ $VERBOSE ]; then echo "[INFO] copying files..."; fi
$SCPCMD -r "servus-publicus" "${SSHUSER}@${DSTHOST}:${INSTALLDIR}/"

if [ $VERBOSE ]; then echo "[INFO] building docker image..."; fi
$SSHCMD $DSTHOST "cd ${INSTALLDIR}/servus-publicus && docker build -t servus-publicus ."

if [ $VERBOSE ]; then echo "[INFO] starting docker container..."; fi
$SSHCMD $DSTHOST "docker run --name servus-publicus -d \
  --restart unless-stopped \
  --net=host \
  servus-publicus"


# --- done ---

if [ $VERBOSE ]; then echo "[INFO] exiting successfully"; fi
exit 0

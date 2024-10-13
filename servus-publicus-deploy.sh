#!/usr/bin/env bash

VERSION=1.0
USAGE="
Usage: $0 -d <dsthost> -u <sshuser> -y\n
-d destination host\n
-u ssh/scp user\n
-y dont ask\n"


# --- args ---
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


# --- prep ---
INSTALLDIR="/opt/"
SERVICENAME="servus-publicus"
SERVICEUSER="steam"
SSHCMD="$(which ssh) -q -o StrictHostKeyChecking=no -A -F /home/${USER}/.ssh/config -l ${SSHUSER} "
SCPCMD="$(which scp) -r -F /home/${USER}/.ssh/config "

if [ -z $DSTHOST ]; then
  echo "[WARN] destination host is invalid - assuming 'pavlovserver'"
  DSTHOST="pavlovserver"
fi

if [ -z $SSHUSER ]; then
  echo "[WARN] ssh user is invalid - assuming 'root'"
  SSHUSER="root"
fi

if [ "$DONT_ASK" != true ]; then
  read -s -n 1 -p "[WAIT] press any key to continue..." && echo ""
fi
echo "[INFO] starting deployment"


# --- install ---
echo "[INFO] stopping running service..."
$SSHCMD $DSTHOST "systemctl stop ${SERVICENAME}.service"

echo "[INFO] creating service user..."
$SSHCMD $DSTHOST "adduser ${SERVICEUSER}"

echo "[INFO] creating base path..."
$SSHCMD $DSTHOST "mkdir ${INSTALLDIR}"

echo "[INFO] copying files..."
$SCPCMD -r "${SERVICENAME}" "${SSHUSER}@${DSTHOST}:${INSTALLDIR}/"

echo "[INFO] chown-ing files..."
$SSHCMD $DSTHOST "/usr/bin/chown -R ${SERVICEUSER}:${SERVICEUSER} ${INSTALLDIR}/${SERVICENAME}"

echo "[INFO] installing pip requirements..."
$SSHCMD $DSTHOST "sudo su ${SERVICEUSER} -c 'pip install -r ${INSTALLDIR}/${SERVICENAME}/requirements.txt'"

echo "[INFO] creating cronjobs..."
$SSHCMD $DSTHOST "cp \
${INSTALLDIR}/${SERVICENAME}/cron/${SERVICENAME}-events-cron \
${INSTALLDIR}/${SERVICENAME}/cron/${SERVICENAME}-ranks-cron \
${INSTALLDIR}/${SERVICENAME}/cron/${SERVICENAME}-reminder-cron \
${INSTALLDIR}/${SERVICENAME}/cron/${SERVICENAME}-stats-cron \
/etc/cron.d/"

echo "[INFO] creating logrotate config..."
$SSHCMD $DSTHOST "cp ${INSTALLDIR}/${SERVICENAME}/${SERVICENAME}-logrotate /etc/logrotate.d/"

echo "[INFO] creating service file..."
$SSHCMD $DSTHOST "cp ${INSTALLDIR}/${SERVICENAME}/${SERVICENAME}.service /etc/systemd/system/"

echo "[INFO] resetting possibly failed service..."
$SSHCMD $DSTHOST "/usr/bin/systemctl reset-failed ${SERVICENAME}.service"

echo "[INFO] enabling service..."
$SSHCMD $DSTHOST "/usr/bin/systemctl enable ${SERVICENAME}.service"

echo "[INFO] starting service..."
$SSHCMD $DSTHOST "systemctl start ${SERVICENAME}.service"


# --- done ---
echo "[INFO] exiting successfully"
exit 0

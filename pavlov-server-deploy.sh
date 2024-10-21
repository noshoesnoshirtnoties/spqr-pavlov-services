#!/usr/bin/env bash

VERSION=1.2
USAGE="
Usage: $0 -d <dsthost> -u <sshuser> -s <srv> -p -y\n
-d destination host\n
-u ssh/scp user\n
-s server number (0-9)\n
-p praefectus only\n
-y dont ask\n"


# --- args ---
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


# --- prep ---
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

INSTALLDIR="/opt"
SERVICENAME1="pavlovserver"
SERVICENAME2="praefectus"
SERVICEUSER="steam"
SSHCMD="$(which ssh) -q -o StrictHostKeyChecking=no -A -F /home/${USER}/.ssh/config -l ${SSHUSER} "
SCPCMD="$(which scp) -r -F /home/${USER}/.ssh/config "

PAVBASEPATH="/home/steam/${SERVICENAME1}-${SRV}"
PORT1=$((x=7777, y=$SRV, x+y))
PORT2=$((x=$PORT1, y=400, x+y))
PORTRCON=$((x=9100, y=$SRV, x+y))

if [ "$DONT_ASK" != true ]; then
  read -s -n 1 -p "[WAIT] press any key to continue..." && echo ""
fi
echo "[INFO] starting deployment"


# --- install ---
echo "[INFO] stopping running services"
$SSHCMD $DSTHOST "systemctl stop ${SERVICENAME2}-${SRV}.service"
if [ "$PRAEFECTUS_ONLY" != true ]; then
  $SSHCMD $DSTHOST "systemctl stop ${SERVICENAME1}-${SRV}.service"
fi

echo "[INFO] checking if service user exists"
RESPONSE=$($SSHCMD $DSTHOST "grep '^${SERVICEUSER}:' /etc/passwd")
if [ -z $RESPONSE ]; then
  if [ $VERBOSE ]; then echo "[INFO] could not find service user - trying to create it"; fi
  $SSHCMD $DSTHOST "useradd -m -N -s /bin/bash -u 1000 -p 'spqr9678' ${SERVICEUSER}"
fi

echo "[INFO] creating base path"
$SSHCMD $DSTHOST "mkdir ${INSTALLDIR}"

echo "[INFO] copying files"
$SCPCMD -r "${SERVICENAME2}" "${SSHUSER}@${DSTHOST}:${INSTALLDIR}/"
if [ "$PRAEFECTUS_ONLY" != true ]; then
  $SCPCMD -r "${SERVICENAME1}" "${SSHUSER}@${DSTHOST}:${INSTALLDIR}/"
fi

echo "[INFO] chown-ing files..."
$SSHCMD $DSTHOST "/usr/bin/chown -R ${SERVICEUSER}:${SERVICEUSER} ${INSTALLDIR}/${SERVICENAME2}"

echo "[INFO] creating log folder path"
$SSHCMD $DSTHOST "mkdir ${INSTALLDIR}/${SERVICENAME2}/logs"

echo "[INFO] installing requirements"
$SSHCMD $DSTHOST "apt update && apt upgrade -y && apt install -y -q lsb-release gdb curl lib32gcc-s1 libc++-dev unzip python3 python3-pip"

echo "[INFO] installing pip requirements"
<<<<<<< HEAD
$SSHCMD $DSTHOST "sudo su ${SERVICEUSER} -c \"pip install --break-system-packages -r ${INSTALLDIR}/${SERVICENAME2}/requirements.txt\""
=======
$SSHCMD $DSTHOST "sudo su ${SERVICEUSER} -c \"pip install -r ${INSTALLDIR}/${SERVICENAME2}/requirements.txt --break-system-packages\""
>>>>>>> 7db5cfb13a83ee116af6c56ae9f6fb017600cd11

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

echo "[INFO] creating praefectus cronjob"
CRONCMD0='echo "'
CRONCMD1='" > /etc/cron.d/praefectus-cron-'
CRON="* * * * * ${SERVICEUSER} cd /opt/${SERVICENAME2} && python3 cron/praefectus-cron.py ${SRV} >/dev/null 2>&1"
$SSHCMD $DSTHOST "${CRONCMD0}${CRON}${CRONCMD1}${SRV}"

echo "[INFO] checking if service file exist for ${SERVICENAME2}-${SRV}"
if $SSHCMD $DSTHOST "[ ! -f /etc/systemd/system/${SERVICENAME2}-${SRV}.service ]"; then
  echo "[INFO] could not find service file for ${SERVICENAME2}-${SRV} - trying to create it"
  $SSHCMD $DSTHOST "cat > /etc/systemd/system/${SERVICENAME2}-${SRV}.service <<EOL
[Unit]
Description=${SERVICENAME2}-${SRV}

[Service]
Type=simple
WorkingDirectory=/opt/praefectus
ExecStart=/usr/bin/python3 main.py ${SRV}
RestartSec=1
Restart=always
User=${SERVICEUSER}
Group=${SERVICEUSER}

[Install]
WantedBy=multi-user.target
EOL"
  $SSHCMD $DSTHOST "/usr/bin/chmod 664 /etc/systemd/system/${SERVICENAME2}-${SRV}.service"
  $SSHCMD $DSTHOST "/usr/bin/chown root:root /etc/systemd/system/${SERVICENAME2}-${SRV}.service"
fi

if [ "$PRAEFECTUS_ONLY" != true ]; then
  echo "[INFO] checking if service file exist for ${SERVICENAME1}-${SRV}"
  if $SSHCMD $DSTHOST "[ ! -f /etc/systemd/system/${SERVICENAME1}-${SRV}.service ]"; then
    echo "[INFO] could not find service file for ${SERVICENAME1}-${SRV} - trying to create it"
    $SSHCMD $DSTHOST "cat > /etc/systemd/system/${SERVICENAME1}-${SRV}.service <<EOL
[Unit]
Description=${SERVICENAME1}-${SRV}

[Service]
Type=simple
WorkingDirectory=${PAVBASEPATH}
ExecStart=${PAVBASEPATH}/PavlovServer.sh -PORT=${PORT1}
RestartSec=1
Restart=always
User=${SERVICEUSER}
Group=${SERVICEUSER}

[Install]
WantedBy=multi-user.target
EOL"
    $SSHCMD $DSTHOST "/usr/bin/chmod 664 /etc/systemd/system/${SERVICENAME1}-${SRV}.service"
    $SSHCMD $DSTHOST "/usr/bin/chown root:root /etc/systemd/system/${SERVICENAME1}-${SRV}.service"
  fi
fi

echo "[INFO] checking if logrotate config exists for ${SERVICENAME2}-${SRV}"
if $SSHCMD $DSTHOST "[ ! -f /etc/logrotate.d/${SERVICENAME2}-logrotate-${SRV} ]"; then
  echo "[INFO] could not find logrotate config for ${SERVICENAME2}-${SRV} - trying to create it"
  $SSHCMD $DSTHOST "cat > /etc/logrotate.d/${SERVICENAME2}-logrotate-${SRV} <<EOL
/opt/${SERVICENAME2}/${SERVICENAME2}-${SRV}.log {
  daily
  missingok
  rotate 7
  compress
  delaycompress
  notifempty
  create 0640 ${SERVICEUSER} ${SERVICEUSER}
  postrotate
    /bin/systemctl restart ${SERVICENAME2}-${SRV}.service
  endscript
}
EOL"
  $SSHCMD $DSTHOST "/usr/bin/chmod 644 /etc/logrotate.d/${SERVICENAME2}-logrotate-${SRV}"
  $SSHCMD $DSTHOST "/usr/bin/chown root:root /etc/logrotate.d/${SERVICENAME2}-logrotate-${SRV}"
fi

if [ "$PRAEFECTUS_ONLY" != true ]; then
  echo "[INFO] checking for service users home folder"
  if $SSHCMD $DSTHOST "[ ! -d /home/${SERVICEUSER} ]"; then
    echo "[INFO] could not find service users home folder - trying to create it"
    $SSHCMD $DSTHOST "mkdir /home/${SERVICEUSER}"
  fi

  echo "[INFO] setting owner of service user home before installing stuff"
  $SSHCMD $DSTHOST "chown -R ${SERVICEUSER}:${SERVICEUSER} /home/${SERVICEUSER}/"

  echo "[INFO] checking if steam is installed"
  if $SSHCMD $DSTHOST "[ ! -d /home/${SERVICEUSER}/Steam ]"; then
    echo "[INFO] could not find steam - trying to install it"
    $SSHCMD $DSTHOST "sudo su ${SERVICEUSER} -c 'mkdir ~/Steam && cd ~/Steam && curl -sqL https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz | tar zxvf -'"

    echo "[INFO] updating the steamclient"
    $SSHCMD $DSTHOST "sudo su ${SERVICEUSER} -c 'cd ~/Steam && ~/Steam/steamcmd.sh +login anonymous +app_update 1007 +quit'"
  fi

  echo "[INFO] checking if a pavlovserver is installed"
  if $SSHCMD $DSTHOST "[ ! -d \"${PAVBASEPATH}/Pavlov\" ]"; then
    echo "[WARN] could not find a pavlovserver - trying to install it"
    $SSHCMD $DSTHOST "sudo su ${SERVICEUSER} -c \"~/Steam/steamcmd.sh +force_install_dir ${PAVBASEPATH} +login anonymous +app_update 622970 +exit\""
  fi

  # this breaks install...
  #echo "[INFO] doing some weird shit with steamclient.so"
  #$SSHCMD $DSTHOST "sudo su ${SERVICEUSER} -c 'mkdir -p /home/${SERVICEUSER}/.steam/sdk64'"
  #$SSHCMD $DSTHOST "sudo su ${SERVICEUSER} -c 'mkdir -p ${PAVBASEPATH}/Pavlov/Binaries/Linux/'"
  #$SSHCMD $DSTHOST "sudo su ${SERVICEUSER} -c 'cp \"/home/${SERVICEUSER}/Steam/steamapps/common/Steamworks SDK Redist/linux64/steamclient.so\" /home/${SERVICEUSER}/.steam/sdk64/steamclient.so'"
  #$SSHCMD $DSTHOST "sudo su ${SERVICEUSER} -c \"cp '/home/${SERVICEUSER}/Steam/steamapps/common/Steamworks SDK Redist/linux64/steamclient.so' ${PAVBASEPATH}/Pavlov/Binaries/Linux/steamclient.so\""

  echo "[INFO] doing some weird shit with libc++.so"
  $SSHCMD $DSTHOST "mv /usr/lib/x86_64-linux-gnu/libc++.so /usr/lib/x86_64-linux-gnu/libc++.so.backup"
  $SSHCMD $DSTHOST "ln -s /usr/lib/x86_64-linux-gnu/libc++.so.1 /usr/lib/x86_64-linux-gnu/libc++.so"

  echo "[INFO] making start script executable"
  $SSHCMD $DSTHOST "chmod +x ${PAVBASEPATH}/PavlovServer.sh"

  echo "[INFO] creating some folders and files"
  $SSHCMD $DSTHOST "mkdir -p ${PAVBASEPATH}/Pavlov/Saved/Config/LinuxServer"
  $SSHCMD $DSTHOST "mkdir -p ${PAVBASEPATH}/Pavlov/Saved/Logs"
  $SSHCMD $DSTHOST "mkdir -p ${PAVBASEPATH}/Pavlov/Saved/maps"
  $SSHCMD $DSTHOST "mkdir -p ${PAVBASEPATH}/Pavlov/Saved/Config/ModSave/WeaponSkinPack"
  $SSHCMD $DSTHOST "touch \
  ${PAVBASEPATH}/Pavlov/Saved/Config/mods.txt \
  ${PAVBASEPATH}/Pavlov/Saved/Config/blacklist.txt \
  ${PAVBASEPATH}/Pavlov/Saved/Config/whitelist.txt \
  ${PAVBASEPATH}/Pavlov/Saved/Config/RconSettings.txt \
  ${PAVBASEPATH}/Pavlov/Saved/Config/LinuxServer/Game.ini"

  echo "[INFO] deploying configs"
  $SSHCMD $DSTHOST "cp \
  ${INSTALLDIR}/${SERVICENAME1}/conf.d/blacklist.txt \
  ${INSTALLDIR}/${SERVICENAME1}/conf.d/whitelist.txt \
  ${INSTALLDIR}/${SERVICENAME1}/conf.d/mods.txt \
  ${INSTALLDIR}/${SERVICENAME1}/conf.d/${SRV}/RconSettings.txt \
  ${PAVBASEPATH}/Pavlov/Saved/Config/"

  $SSHCMD $DSTHOST "cp \
  ${INSTALLDIR}/${SERVICENAME1}/conf.d/${SRV}/Game.ini \
  ${PAVBASEPATH}/Pavlov/Saved/Config/LinuxServer/"

  $SSHCMD $DSTHOST "cp \
  ${INSTALLDIR}/${SERVICENAME1}/conf.d/ModSave_WeaponSkinPack_serverconfig.json \
  ${PAVBASEPATH}/Pavlov/Saved/Config/ModSave/WeaponSkinPack/serverconfig.json"

  echo "[INFO] making configs writable for everyone"
  $SSHCMD $DSTHOST "chmod +w \
  ${PAVBASEPATH}/Pavlov/Saved/Config/LinuxServer/Game.ini \
  ${PAVBASEPATH}/Pavlov/Saved/Config/blacklist.txt \
  ${PAVBASEPATH}/Pavlov/Saved/Config/whitelist.txt \
  ${PAVBASEPATH}/Pavlov/Saved/Config/mods.txt"

  echo "[INFO] setting owner of /home/steam to steam:steam (again...)"
  $SSHCMD $DSTHOST "chown -R steam:steam /home/steam/"
fi

echo "[INFO] resetting possibly failed service..."
$SSHCMD $DSTHOST "/usr/bin/systemctl reset-failed ${SERVICENAME2}-${SRV}.service"
if [ "$PRAEFECTUS_ONLY" != true ]; then
  $SSHCMD $DSTHOST "/usr/bin/systemctl reset-failed ${SERVICENAME1}-${SRV}.service"
fi

echo "[INFO] enabling service..."
$SSHCMD $DSTHOST "/usr/bin/systemctl enable ${SERVICENAME2}-${SRV}.service"
if [ "$PRAEFECTUS_ONLY" != true ]; then
  $SSHCMD $DSTHOST "/usr/bin/systemctl enable ${SERVICENAME1}-${SRV}.service"
fi

echo "[INFO] starting service..."
$SSHCMD $DSTHOST "/usr/bin/systemctl start ${SERVICENAME2}-${SRV}.service"
if [ "$PRAEFECTUS_ONLY" != true ]; then
  $SSHCMD $DSTHOST "/usr/bin/systemctl start ${SERVICENAME1}-${SRV}.service"
fi


# --- done ---
echo "[INFO] exiting successfully"
exit 0

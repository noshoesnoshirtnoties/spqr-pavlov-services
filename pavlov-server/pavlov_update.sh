#!/bin/bash

/home/steam/Steam/steamcmd.sh +force_install_dir "/home/steam/pavlovserver" +login anonymous +app_update 622970 -beta default +exit
/home/steam/Steam/steamcmd.sh +login anonymous +app_update 1007 +quit
cp "/home/steam/Steam/steamapps/common/Steamworks SDK Redist/linux64/steamclient.so" "/home/steam/.steam/sdk64/steamclient.so"
cp "/home/steam/Steam/steamapps/common/Steamworks SDK Redist/linux64/steamclient.so" "/home/steam/pavlovserver/Pavlov/Binaries/Linux/steamclient.so"

exit 0
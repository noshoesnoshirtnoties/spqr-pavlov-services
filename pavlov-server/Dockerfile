FROM ubuntu:22.04

RUN apt update && apt upgrade -y && apt install -y -q gdb curl lib32gcc-s1 libc++-dev unzip

RUN useradd -m -N -s /bin/bash -u 1000 -p 'password' steam
USER steam

RUN mkdir /home/steam/Steam && cd /home/steam/Steam && curl -sqL "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz" | tar zxvf -
RUN /home/steam/Steam/steamcmd.sh +login anonymous +force_install_dir /home/steam/pavlovserver +app_update 622970 -beta default +exit && chmod +x /home/steam/pavlovserver/PavlovServer.sh
RUN cd ~/Steam && ~/Steam/steamcmd.sh +login anonymous +app_update 1007 +quit
#RUN mkdir -p /home/steam/.steam/sdk64
#RUN cp /home/steam/Steam/steamapps/common/Steamworks\ SDK\ Redist/linux64/steamclient.so /home/steam/.steam/sdk64/steamclient.so
#RUN cp /home/steam/Steam/steamapps/common/Steamworks\ SDK\ Redist/linux64/steamclient.so /home/steam/pavlovserver/Pavlov/Binaries/Linux/steamclient.so

USER root
RUN mv /lib/x86_64-linux-gnu/libc++.so /lib/x86_64-linux-gnu/libc++.so.backup
RUN ln -s /lib/x86_64-linux-gnu/libc++.so.1 /lib/x86_64-linux-gnu/libc++.so

COPY pavlov_start.sh /home/steam/pavlov_start.sh
COPY pavlov_update.sh /home/steam/pavlov_update.sh
COPY pavlov_update_cron /etc/cron.d/pavlov_update_cron
RUN chown -R steam:root /home/steam

USER steam
CMD ["/home/steam/pavlov_start.sh"]
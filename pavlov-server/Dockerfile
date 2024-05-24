FROM ubuntu:22.04

ENV SRV=0
ENV PORT=7777

RUN apt update && apt upgrade -y && apt install -y -q gdb curl lib32gcc-s1 libc++-dev unzip

RUN useradd -m -N -s /bin/bash -u 1000 -p 'password' steam

USER steam
RUN mkdir -p /home/steam/pavlovserver/Pavlov/Saved/Config/LinuxServer
#RUN mkdir -p /home/steam/pavlovserver/Pavlov/Saved/maps
RUN mkdir -p /home/steam/pavlovserver/Pavlov/Saved/Logs

USER steam
RUN mkdir /home/steam/Steam && cd /home/steam/Steam && curl -sqL "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz" | tar zxvf -
RUN /home/steam/Steam/steamcmd.sh +login anonymous +force_install_dir /home/steam/pavlovserver +app_update 622970 -beta default +exit && chmod +x /home/steam/pavlovserver/PavlovServer.sh
RUN cd ~/Steam && ~/Steam/steamcmd.sh +login anonymous +app_update 1007 +quit

USER root
RUN mv /lib/x86_64-linux-gnu/libc++.so /lib/x86_64-linux-gnu/libc++.so.backup
RUN ln -s /lib/x86_64-linux-gnu/libc++.so.1 /lib/x86_64-linux-gnu/libc++.so

COPY pavlov_start.sh /home/steam/pavlov_start.sh
COPY pavlov_update.sh /home/steam/pavlov_update.sh
COPY pavlov_update_cron /etc/cron.d/pavlov_update_cron

COPY conf.d/blacklist.txt /home/steam/pavlovserver/Pavlov/Saved/Config/blacklist.txt
COPY conf.d/whitelist.txt /home/steam/pavlovserver/Pavlov/Saved/Config/whitelist.txt
COPY conf.d/mods.txt /home/steam/pavlovserver/Pavlov/Saved/Config/mods.txt
COPY conf.d/ModSave_WeaponSkinPack_serverconfig.json /home/steam/pavlovserver/Pavlov/Saved/Config/ModSave/WeaponSkinPack/serverconfig.json
RUN chmod +w /home/steam/pavlovserver/Pavlov/Saved/Config/blacklist.txt
RUN chmod +w /home/steam/pavlovserver/Pavlov/Saved/Config/whitelist.txt
RUN chmod +w /home/steam/pavlovserver/Pavlov/Saved/Config/mods.txt

RUN chown -R steam:users /home/steam

USER steam
CMD ["/home/steam/pavlov_start.sh"]
import os
import re
import sys
import json
import time
import logging
import inspect
import random
import asyncio
import mysql.connector
from pathlib import Path
from pavlov import PavlovRCON
from datetime import datetime,timezone

if __name__ == '__main__':
    if str(sys.argv[1])!='': srv=str(sys.argv[1])
    else: srv='0'

    config=json.loads(open('config.json').read())

    if bool(config['debug'])==True: level=logging.DEBUG
    else: level=logging.INFO
    logging.basicConfig(
        filename='cron/praefectus-cron-'+str(srv)+'.log',
        filemode='a',
        format='%(asctime)s,%(msecs)d [%(levelname)s] %(message)s',
        datefmt='%m/%d/%Y %H:%M:%S',
        level=level)
    logfile=logging.getLogger('logfile')


    def logmsg(lvl,msg):
        match lvl.lower():
            case 'debug': logfile.debug(msg)
            case 'info': logfile.info(msg)
            case 'warn': logfile.warning(msg)
            case _: logfile.debug(msg)


    def dbquery(query,values):
        logmsg('debug','dbquery called')
        conn=mysql.connector.connect(
            host=config['mysql']['host'],
            port=config['mysql']['port'],
            user=config['mysql']['user'],
            password=config['mysql']['pass'],
            database=config['mysql']['database'])
        cursor=conn.cursor(buffered=True,dictionary=True)
        cursor.execute(query,(values))
        conn.commit()
        data={}
        data['rowcount']=cursor.rowcount
        query_type0=query.split(' ',2)
        query_type=str(query_type0[0])
        if query_type.upper()=="SELECT": data['rows']=cursor.fetchall()
        else: data['rows']=False
        cursor.close()
        conn.close()
        return data


    async def pin_limit(conn,serverinfo):
        logmsg('debug','pin_limit called')
        if config['pinlimit'][srv]!=0:
            logmsg('debug','pinlimit is enabled')
            try:
                limit=config['pinlimit'][srv]
                si=serverinfo['ServerInfo']
                roundstate=si['RoundState']
                gamemode=str(si['GameMode'].upper()).strip()
                playercount_split=si['PlayerCount'].split('/',2)
                numberofplayers=int(playercount_split[0])
                maxplayers=int(playercount_split[1])
                
                demo_enabled=False # get this via rcon
                if demo_enabled is True: # demo rec counts as 1 player
                    if int(numberofplayers)>0: numberofplayers=(numberofplayers-1) # demo only exists if there are players
            
                if gamemode=="SND": # for whatever reason SND has 1 additional player (with comp mode off and demo off)
                    if int(numberofplayers)>0: numberofplayers=(numberofplayers-1)

                if roundstate=='Started':
                    if numberofplayers>=limit: # limit reached
                        logmsg('debug','limit ('+str(limit)+') reached - setting pin '+str(config['pin']))
                        cmd='SetPin '+str(config['pin'])
                        try:
                            data=await conn.send(cmd)
                            if data['Successful'] is True: logmsg('debug','setpin has set the pin')
                            else: logmsg('error','setpin has NOT set the pin for some reason')
                        except Exception as e:
                            if str(e)!='': logmsg('error','EXCEPTION in '+fx+': '+str(e))
                    else: # below limit
                        logmsg('debug','below limit ('+str(limit)+') - removing pin')
                        cmd='SetPin '
                        try:
                            data=await conn.send(cmd)
                            if data['Successful'] is True: logmsg('debug','setpin has emptied the pin')
                            else: logmsg('error','setpin has NOT emptied the pin for some reason')
                        except Exception as e:
                            if str(e)!='': logmsg('error','EXCEPTION in '+fx+': '+str(e))
                else: logmsg('warn','not touching pin because of roundstate '+str(roundstate))

            except Exception as e:
                if str(e)!='': logmsg('error','EXCEPTION: '+str(e))
        else: logmsg('info','pinlimit canceled because pinlimit is disabled')


    async def ping_limit(conn,serverinfo):
        logmsg('debug','ping_limit called')
        if config['rconplus'][srv] is True:
            logmsg('debug','rconplus is enabled')
            if config['pinglimit'][srv]['enabled'] is True:
                logmsg('debug','pinglimit is enabled')
                try:
                    si=serverinfo['ServerInfo']
                    roundstate=si['RoundState']
                    if roundstate=='Started':
                        data=await conn.send('RefreshList')
                        data_json=json.dumps(data)
                        refreshlist=json.loads(data_json)
                        for player in refreshlist['PlayerList']:
                            steamid64=str(player['UniqueId']).strip()
                            notify_player=False
                            kick_player=False

                            cmd='InspectPlayer '+str(steamid64)
                            data=await conn.send(cmd)
                            data_json=json.dumps(data)
                            inspectplayer=json.loads(data_json)

                            kda=inspectplayer['PlayerInfo']['KDA'].split('/',3)
                            kills=kda[0]
                            deaths=kda[1]
                            assists=kda[2]
                            score=inspectplayer['PlayerInfo']['Score']
                            current_ping=inspectplayer['PlayerInfo']['Ping']

                            if int(kills)!=0 or int(deaths)!=0 or int(score)!=0: # make sure player is actually here

                                # add the current sample for the current player...
                                if int(current_ping)!=0:
                                    logmsg('debug',str(steamid64)+': adding entry for player')
                                    timestamp=datetime.now(timezone.utc)
                                    query="INSERT INTO pings ("
                                    query+="steamid64,ping,timestamp"
                                    query+=") VALUES (%s,%s,%s)"
                                    values=[steamid64,current_ping,timestamp]
                                    dbquery(query,values)

                                # get averages for current player
                                query="SELECT steamid64,ping,"
                                query+="AVG(ping) as avg_ping,"
                                query+="MIN(ping) as min_ping,"
                                query+="MAX(ping) as max_ping,"
                                query+="COUNT(id) as cnt_ping "
                                query+="FROM pings "
                                query+="WHERE steamid64 = %s"
                                values=[]
                                values.append(steamid64)
                                pings=dbquery(query,values)

                                avg_ping=pings['rows'][0]['avg_ping']
                                min_ping=pings['rows'][0]['min_ping']
                                max_ping=pings['rows'][0]['max_ping']
                                cnt_ping=pings['rows'][0]['cnt_ping']

                                # check if there are enough samples
                                if cnt_ping>=config['pinglimit']['minentries']:
                                    avg=int(avg_ping)
                                    delta=int(max_ping)-int(min_ping)
                                    limit_delta=int(config['pinglimit'][srv]['delta'])
                                    limit_soft=int(config['pinglimit'][srv]['soft'])
                                    limit_hard=int(config['pinglimit'][srv]['hard'])

                                    # check delta
                                    if delta>limit_delta:
                                        logmsg('info',str(steamid64)+': players ping delta ('+str(delta)+') exceeds delta limit ('+str(limit_delta)+')')
                                        msg='ping delta warning :(\n\nconnection seems unstable'
                                        notify_player=True
                                    else: logmsg('debug',str(steamid64)+': players ping delta ('+str(delta)+') is within delta limit ('+str(limit_delta)+')')

                                    # check avg ping against soft limit
                                    if avg>limit_soft:
                                        logmsg('info',str(steamid64)+': players ping avg ('+str(avg)+') exceeds soft limit ('+str(limit_soft)+')')
                                        msg='ping exceeds soft limit ('+str(limit_soft)+') for this server :('
                                        notify_player=True
                                    else: logmsg('debug',str(steamid64)+': players ping avg ('+str(avg)+') is within soft limit ('+str(limit_soft)+')')

                                    # check avg ping against hard limit
                                    if avg>limit_hard:
                                        logmsg('info',str(steamid64)+': players ping avg ('+str(avg)+') exceeds hard limit ('+str(limit_hard)+')')
                                        msg='ping exceeds hard limit ('+str(limit_hard)+') for this server :('
                                        notify_player=True
                                        kick_player=True
                                    else: logmsg('debug',str(steamid64)+': players ping avg ('+str(avg)+') is within hard limit ('+str(limit_hard)+')')

                                    # notify
                                    if notify_player is True:
                                        if config['pinglimit'][srv]['notify'] is True:
                                            if config['pinglimit'][srv]['kick'] is True and kick_player is True: msg+='\n\nauto-kick is enabled'
                                            cmd='Notify '+str(steamid64)+' '+msg
                                            try: await conn.send(cmd)
                                            except Exception as e:
                                                if str(e)!='': logmsg('error','EXCEPTION: while trying to notify: '+str(e))
                                            logmsg('info',str(steamid64)+': player has probably been notified by pinglimit')
                                        else: logmsg('info',str(steamid64)+': player would have been notified, but notify is disabled')

                                    # kick
                                    if kick_player is True:
                                        if config['pinglimit'][srv]['kick'] is True:
                                            cmd='Kick '+str(steamid64)
                                            try:
                                                time.sleep(4)
                                                await conn.send(cmd)
                                                logmsg('info',str(steamid64)+': player has been kicked by pinglimit')
                                            except Exception as e:
                                                if str(e)!='': logmsg('error','EXCEPTION: while trying to kick: '+str(e))
                                        else: logmsg('info',str(steamid64)+': player would have been kicked, but kick is disabled')

                                    # delete accumulated entries, but keep some recent ones
                                    logmsg('debug',str(steamid64)+': deleting entries because limits have been retained')
                                    query="DELETE FROM pings WHERE steamid64 = %s ORDER BY id ASC LIMIT %s"
                                    values=[]
                                    values.append(steamid64)
                                    values.append(cnt_ping - int(config['pinglimit']['keepentries']))
                                    dbquery(query,values)

                                else: logmsg('debug',str(steamid64)+': skipping because not enough data')
                            else: logmsg('debug',str(steamid64)+': skipping because not alive yet')
                    else: logmsg('debug','skipping this pinglimit run because of roundstate '+str(roundstate))

                except Exception as e:
                    if str(e)!='': logmsg('error','EXCEPTION: '+str(e))
            else: logmsg('info','pinglimit canceled because pinglimit is disabled')
        else: logmsg('info','pinglimit canceled because rconplus is disabled')


    async def praefectus_cron(rnd_sleep):
        logmsg('debug','praefectus_cron called')
        time.sleep(rnd_sleep)

        try:
            port=config['rcon']['port']+int(srv)
            conn=PavlovRCON(config['rcon']['ip'],port,config['rcon']['pass'])
            
            data=await conn.send('ServerInfo')
            data_json=json.dumps(data)
            serverinfo=json.loads(data_json)

            await pin_limit(conn,serverinfo)

            i=0
            runs=3
            while i<runs:
                logmsg('debug','starting run #: '+str(i))
                await ping_limit(conn,serverinfo)
                i+=1
                time.sleep(2)
            await conn.send('Disconnect')
            logmsg('debug','rcon disconnected ')
        except Exception as e:
            if str(e)!='': logmsg('error','EXCEPTION: '+str(e))
    

    asyncio.run(praefectus_cron(random.randint(1,20)))
    logmsg('debug','end of praefectus-cron reached')

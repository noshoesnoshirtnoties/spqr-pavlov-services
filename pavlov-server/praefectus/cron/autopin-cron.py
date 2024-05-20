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

    rnd_sleep=random.randint(30,40)
    time.sleep(rnd_sleep)

    config=json.loads(open('/opt/pavlov-server/praefectus/config.json').read())

    if bool(config['debug'])==True: level=logging.DEBUG
    else: level=logging.INFO
    logging.basicConfig(
        filename='/opt/pavlov-server/praefectus/cron/autopin-cron-'+str(srv)+'.log',
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


    async def autopin():
        logmsg('debug','autopin called')
        if config['autopin_limits'][srv]!=0:
            logmsg('debug','autopin is enabled')
            limit=config['autopin_limits'][srv]
            try:
                port=config['rcon']['port']+int(srv)
                conn=PavlovRCON(config['rcon']['ip'],port,config['rcon']['pass'])

                data=await conn.send('ServerInfo')
                data_json=json.dumps(data)
                serverinfo=json.loads(data_json)
                si=serverinfo['ServerInfo']
                maplabel=str(si['MapLabel'].lower()).strip()
                gamemode=str(si['GameMode'].upper()).strip()
                roundstate=str(si['RoundState']).strip()

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
                        logmsg('debug','limit ('+str(limit)+') reached - setting pin '+str(config['autopin']))
                        cmd='SetPin '+str(config['autopin'])
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

        else: logmsg('info','autopin canceled because autopin is disabled')

        await conn.send('Disconnect')
        logmsg('info','rcon disconnected ')

    asyncio.run(autopin())
    logmsg('info','end of autopin-cron reached')

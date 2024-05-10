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

def run_praefectus(meta,config,srv):

    if bool(config['debug'])==True: level=logging.DEBUG
    else: level=logging.INFO
    logging.basicConfig(
        filename='praefectus-'+str(srv)+'.log',
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
        fx=inspect.stack()[0][3]
        logmsg('debug',fx+' called')
        #logmsg('debug','query: '+str(query))
        #logmsg('debug','values: '+str(values))
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


    async def init_server():
        fx=inspect.stack()[0][3]
        logmsg('debug',fx+' called')

        time.sleep(1)
        
        port=config['rcon']['port']+int(srv)
        conn=PavlovRCON(config['rcon']['ip'],port,config['rcon']['pass'])

        # LOAD RCONPLUS
        if config['rconplus'][srv] is True:
            cmd='UGCAddMod'
            params={'0':'UGC3462586'}
            i=0
            while i<len(params):
                cmd+=' '+str(params[str(i)])
                i+=1
            try:
                data=await conn.send(cmd)
                if data['Successful'] is True: logmsg('info','rconplus has been loaded')
                else: logmsg('error','rconplus has NOT been loaded for some reason')
            except Exception as e:
                if str(e)!='': logmsg('error','EXCEPTION in '+fx+': '+str(e))
        else: logmsg('info','rconplus is disabled')

        # LOAD HARDCORE
        if config['hardcore'][srv] is True:
            cmd='UGCAddMod'
            params={'0':'UGC3951330'}
            i=0
            while i<len(params):
                cmd+=' '+str(params[str(i)])
                i+=1
            try:
                data=await conn.send(cmd)
                if data['Successful'] is True: logmsg('info','hardcore has been loaded')
                else: logmsg('error','hardcore has NOT been loaded for some reason')
            except Exception as e:
                if str(e)!='': logmsg('error','EXCEPTION in '+fx+': '+str(e))
        else: logmsg('info','hardcore is disabled')

        await conn.send('Disconnect')


    async def init_round():
        fx=inspect.stack()[0][3]
        logmsg('debug',fx+' called')
        
        port=config['rcon']['port']+int(srv)
        conn=PavlovRCON(config['rcon']['ip'],port,config['rcon']['pass'])

        try:
            data=await conn.send('ServerInfo')
            data_json=json.dumps(data)
            serverinfo=json.loads(data_json)
            si=serverinfo['ServerInfo']
            maplabel=str(si['MapLabel'].lower()).strip()
            gamemode=str(si['GameMode'].upper()).strip()
            is_first_round=False # for snd
            if 'Team0Score' in si or 'Team1Score' in si:
                if int(si['Team0Score'])==0 and int(si['Team1Score'])==0: is_first_round=True

            # INIT WORKAROUND
            if maplabel=='datacenter' and gamemode=='CUSTOM':
                logmsg('info','init workaround detected')
                logmsg('debug','maplabel: '+maplabel)
                logmsg('debug','gamemode: '+gamemode)
                try: # immediately rotate to next map
                    data=await conn.send('RotateMap')
                    data_json=json.dumps(data)
                    rotatemap=json.loads(data_json)
                    if rotatemap['Successful'] is True: logmsg('info','rotatemap has been successful')
                    else: logmsg('error','rotatemap has NOT been successful for some reason')
                except Exception as e:
                    if str(e)!='': logmsg('error','EXCEPTION in '+fx+' when rotating map: '+str(e))
                time.sleep(1)
                try: # remove datacenter custom from the pool
                    cmd='RemoveMapRotation'
                    params={"0":"datacenter","1":"CUSTOM"}
                    i=0
                    while i<len(params):
                        cmd+=' '+str(params[str(i)])
                        i+=1
                    data=await conn.send(cmd)
                    data_json=json.dumps(data)
                    removemap=json.loads(data_json)
                    if removemap['Successful'] is True: logmsg('info','removemap has been successful')
                    else: logmsg('error','removemap has NOT been successful for some reason')
                except Exception as e:
                    if str(e)!='': logmsg('error','EXCEPTION in '+fx+' when removing map: '+str(e))

            # MAP INIT
            else:
                logmsg('info','map init reached')
                logmsg('debug','maplabel: '+maplabel)
                logmsg('debug','gamemode: '+gamemode)
                logmsg('debug','is_first_round: '+str(is_first_round))

                if config['rconplus'][srv] is True:
                    time.sleep(1)

                    # ADD BOTS
                    amount=int(config['bots'][srv]['amount'])
                    if amount!=0:
                        if gamemode=="TDM" or gamemode=="TANKTDM" or gamemode=="WW2TDM":

                            # red team
                            cmd='AddBot'
                            params={'0':str(amount//2),'1':'RedTeam'}
                            i=0
                            while i<len(params):
                                cmd+=' '+str(params[str(i)])
                                i+=1
                            try:
                                await conn.send(cmd)
                            except Exception as e:
                                if str(e)!='': logmsg('error','EXCEPTION in '+fx+' when adding bots to RedTeam: '+str(e))
                            logmsg('info','probably added '+str(amount//2)+' bot(s) to RedTeam')

                            # blue team
                            params={'0':str(amount//2),'1':'BlueTeam'}
                            i=0
                            while i<len(params):
                                cmd+=' '+str(params[str(i)])
                                i+=1
                            try:
                                await conn.send(cmd)
                            except Exception as e:
                                if str(e)!='': logmsg('error','EXCEPTION in '+fx+' when adding bots to BlueTeam: '+str(e))
                            logmsg('info','probably added '+str(amount//2)+' bot(s) to BlueTeam')

                        elif gamemode=="DM" or gamemode=="CUSTOM":

                            # teamless
                            cmd='AddBot'
                            params={'0':str(amount)}
                            i=0
                            while i<len(params):
                                cmd+=' '+str(params[str(i)])
                                i+=1
                            try:
                                await conn.send(cmd)
                            except Exception as e:
                                if str(e)!='': logmsg('error','EXCEPTION in '+fx+' when adding bots: '+str(e))
                            logmsg('info','probably added '+str(amount)+' bot(s)')

                        elif gamemode=="SND":
                            #if is_first_round is True:
                            logmsg('warn','not adding bots because gamemode is SND')
                        else:
                            logmsg('warn','not adding bots because gamemode "'+gamemode+'" is not supported atm')

                    else: logmsg('info','bots amount is 0')

                    # ADD CHICKEN
                    amount=int(config['chickens'][srv])
                    if amount!=0:
                        cmd='SpawnChickens'
                        params={'0':str(amount)}
                        j=0
                        while j<len(params):
                            cmd+=' '+str(params[str(j)])
                            j+=1
                        try:
                            await conn.send(cmd)
                        except Exception as e:
                                if str(e)!='': logmsg('error','EXCEPTION in '+fx+' when adding chickens: '+str(e))
                        logmsg('info','probably added '+str(amount)+' chicken(s)')

                    else: logmsg('info','chickens amount is 0')

                    # ADD ZOMBIES
                    amount=int(config['zombies'][srv])
                    if amount!=0:
                        cmd='SpawnZombies'
                        params={'0':str(amount)}
                        j=0
                        while j<len(params):
                            cmd+=' '+str(params[str(j)])
                            j+=1
                        try:
                            await conn.send(cmd)
                        except Exception as e:
                            if str(e)!='': logmsg('error','EXCEPTION in '+fx+' when adding zombies: '+str(e))
                        logmsg('info','probably added '+str(amount)+' zombie(s)')

                    else: logmsg('info','zombies amount is 0')

                    # ENABLE PRONE
                    if config['prone'][srv] is True:
                        cmd='EnableProne'
                        params={'0':'1'}
                        j=0
                        while j<len(params):
                            cmd+=' '+str(params[str(j)])
                            j+=1
                        try:
                            await conn.send(cmd)
                        except Exception as e:
                            if str(e)!='': logmsg('error','EXCEPTION in '+fx+' when enabling prone: '+str(e))
                        logmsg('info','prone has probably been enabled')
                    else: logmsg('info','prone is disabled')

                    # ENABLE TRAILS
                    if config['trails'][srv] is True:
                        cmd='EnableTrails'
                        params={'0':'1'}
                        j=0
                        while j<len(params):
                            cmd+=' '+str(params[str(j)])
                            j+=1
                        try:
                            await conn.send(cmd)
                        except Exception as e:
                            if str(e)!='': logmsg('error','EXCEPTION in '+fx+' when enabling trails: '+str(e))
                        logmsg('info','trails have probably been enabled')
                    else: logmsg('info','trails are disabled')

                    # ENABLE NOFALLDMG
                    if config['nofalldmg'][srv] is True:
                        cmd='FallDamage'
                        params={'0':False}
                        j=0
                        while j<len(params):
                            cmd+=' '+str(params[str(j)])
                            j+=1
                        try:
                            await conn.send(cmd)
                        except Exception as e:
                            if str(e)!='': logmsg('error','EXCEPTION in '+fx+' when enabling nofalldmg: '+str(e))
                        logmsg('info','nofalldamage has probably been enabled')
                    else: logmsg('info','nofalldamage is disabled')

                else: logmsg('warn','not doing stuff (bots, zombies, chicken, prone, trails, nofalldamage, etc.) because rconplus is disabled')

        except Exception as e:
            if str(e)!='': logmsg('error','EXCEPTION in '+fx+': '+str(e))
        await conn.send('Disconnect')


    async def player_joined(joinuser):
        fx=inspect.stack()[0][3]
        logmsg('debug',fx+' called')

        time.sleep(5)

        port=config['rcon']['port']+int(srv)
        conn=PavlovRCON(config['rcon']['ip'],port,config['rcon']['pass'])

        try:
            data=await conn.send('ServerInfo')
            data_json=json.dumps(data)
            serverinfo=json.loads(data_json)
            si=serverinfo['ServerInfo']
            maplabel=str(si['MapLabel'].lower()).strip()
            gamemode=str(si['GameMode'].upper()).strip()
            roundstate=str(si['RoundState']).strip()

            nop0=si['PlayerCount'].split('/',2)
            nop1=nop0[0]

            # demo rec counts as 1 player in SND
            if gamemode=="SND":
                # demo only exists if there is players
                if int(nop1)>0: nop2=(int(nop1)-1)
                else: nop2=(nop0[0])

                maxplayers=nop0[1]
                si['PlayerCount']=str(nop2)+'/'+str(maxplayers)

            playercount=int(si['PlayerCount'].split('/',2)[0])

            # WELCOME PLAYER
            if config['rconplus'][srv] is True:
                if roundstate=='Starting' or roundstate=='Started' or roundstate=='StandBy':
                    try:
                        data=await conn.send('InspectAll')
                        data_json=json.dumps(data)
                        inspectall=json.loads(data_json)

                        data=await conn.send('ModeratorList')
                        data_json=json.dumps(data)
                        modlist=json.loads(data_json)
                        for player in inspectall['InspectList']:
                            steamid64=str(player['UniqueId'])
                            if str(joinuser)==str(player['PlayerName']):
                                for mod in modlist['ModeratorList']:
                                    mod0=mod.split('#',2)
                                    mod1=mod0[0].strip()
                                    if str(steamid64)==str(mod1):
                                        cmd='GiveMenu'
                                        params={'0':steamid64}
                                        j=0
                                        while j<len(params):
                                            cmd+=' '+str(params[str(j)])
                                            j+=1
                                        try:
                                            await conn.send(cmd)
                                        except Exception as e:
                                            if str(e)!='': logmsg('error','EXCEPTION in '+fx+' when giving menu to spqr agent: '+str(e))
                                        logmsg('info','givemenu has probably been set for '+steamid64+' ('+joinuser+')')

                                        #if str(mod1)=='76561199476460201':
                                        #    cmd='Visibility'
                                        #    params={'0':steamid64,'1':False}
                                        #    j=0
                                        #    while j<len(params):
                                        #        cmd+=' '+str(params[str(j)])
                                        #        j+=1
                                        #    try:
                                        #        await conn.send(cmd)
                                        #    except Exception as e:
                                        #        if str(e)!='': logmsg('error','EXCEPTION in '+fx+' when setting visibility for spqr agent: '+str(e))
                                        #    logmsg('info','visibility has probably been set to false for '+steamid64+' ('+joinuser+')')

                                msg=str(si['ServerName'])+'\n\n'
                                msg+='WELCOME, '+joinuser+' :)'
                                cmd='Notify'
                                params={'0':steamid64,'1':msg}
                                j=0
                                while j<len(params):
                                    cmd+=' '+str(params[str(j)])
                                    j+=1
                                try:
                                    await conn.send(cmd)
                                except Exception as e:
                                    if str(e)!='': logmsg('error','EXCEPTION in '+fx+' when welcoming player: '+str(e))
                                logmsg('info','player '+steamid64+' has been welcomed')
                    except Exception as e:
                        if str(e)!='': logmsg('error','EXCEPTION in '+fx+': '+str(e))
                else: logmsg('warn','not welcoming player because roundstate is '+roundstate)
            else: logmsg('info','not welcoming player because rconplus is disabled')

            # CHECK AUTOPIN
            if config['autopin_limits'][srv]!=0:
                limit=config['autopin_limits'][srv]

                if roundstate=='Starting' or roundstate=='StandBy' or roundstate=='Started':
                    if int(playercount)>=limit: # limit reached
                        logmsg('debug','limit ('+str(limit)+') reached - setting pin '+str(config['autopin']))
                        cmd='SetPin'
                        params={'0':config['autopin']}
                        i=0
                        while i<len(params):
                            cmd+=' '+str(params[str(i)])
                            i+=1
                        try:
                            data=await conn.send(cmd)
                            if data['Successful'] is True: logmsg('debug','setpin has set the pin')
                            else: logmsg('error','setpin has NOT set the pin for some reason')
                        except Exception as e:
                            if str(e)!='': logmsg('error','EXCEPTION in '+fx+' when setting pin: '+str(e))
                    else: # below limit
                        logmsg('debug','below limit ('+str(limit)+') - removing pin')
                        cmd='SetPin'
                        params={'0':' '}
                        i=0
                        while i<len(params):
                            cmd+=' '+str(params[str(i)])
                            i+=1
                        try:
                            data=await conn.send(cmd)
                            if data['Successful'] is True: logmsg('debug','setpin has emptied the pin')
                            else: logmsg('error','setpin has NOT emptied the pin for some reason')
                        except Exception as e:
                            if str(e)!='': logmsg('error','EXCEPTION in '+fx+' when setting pin: '+str(e))
                else: logmsg('warn','not touching pin because of roundstate '+str(roundstate))
            else: logmsg('info','not touching pin because autopin is disabled')

            # MANAGE BOTS (REMOVE)
            if config['rconplus'][srv] is True:
                if config['bots'][srv]['managed'] is True:
                    amount=int(config['bots'][srv]['amount'])
                    if amount!=0:
                        if roundstate=='Started':

                            logmsg('debug','this is the time to manage bots... but that code is missing atm')

                            #elif mode=="remove":
                            #    if gamemode=="TDM" or gamemode=="TANKTDM" or gamemode=="WW2TDM":
                            #        await rcon('RemoveBot',{'0':'1','1':'RedTeam'},True)
                            #        logmsg('info',RemoveBot+' probably removed 1 bot to RedTeam')
                            #        await rcon('RemoveBot',{'0':'1','1':'BlueTeam'},True)
                            #        logmsg('info',fx+' probably removed 1 bot to BlueTeam')
                            #    elif gamemode=="DM" or gamemode=="CUSTOM":
                            #        await rcon('RemoveBot',{'0':'1'},True)
                            #        logmsg('info',fx+' probably removed 1 bot')
                            #    elif gamemode=="SND":
                            #        logmsg('warn',fx+' skipped because gamemode is SND')

                        else: logmsg('warn','not managing bots because of roundstate '+str(roundstate))
                    else: logmsg('info','not managing bots because amount is 0')
                else: logmsg('info','not managing bots because "managed" is not true')
            else: logmsg('info','not managing bots because rconplus is disabled')

        except Exception as e:
            if str(e)!='': logmsg('error','EXCEPTION in '+fx+': '+str(e))
        await conn.send('Disconnect')


    async def player_left():
        fx=inspect.stack()[0][3]
        logmsg('debug',fx+' called')

        time.sleep(1)

        port=config['rcon']['port']+int(srv)
        conn=PavlovRCON(config['rcon']['ip'],port,config['rcon']['pass'])

        try:
            data=await conn.send('ServerInfo')
            data_json=json.dumps(data)
            serverinfo=json.loads(data_json)
            si=serverinfo['ServerInfo']
            maplabel=str(si['MapLabel'].lower()).strip()
            gamemode=str(si['GameMode'].upper()).strip()
            roundstate=str(si['RoundState']).strip()

            nop0=si['PlayerCount'].split('/',2)
            nop1=nop0[0]

            # demo rec counts as 1 player in SND
            if gamemode=="SND":
                # demo only exists if there is players
                if int(nop1)>0: nop2=(int(nop1)-1)
                else: nop2=(nop0[0])

                maxplayers=nop0[1]
                si['PlayerCount']=str(nop2)+'/'+str(maxplayers)

            playercount=int(si['PlayerCount'].split('/',2)[0])

            # CHECK AUTPIN
            if config['autopin_limits'][srv]!=0:
                limit=config['autopin_limits'][srv]

                if roundstate=='Starting' or roundstate=='StandBy' or roundstate=='Started':
                    if playercount>=limit: # limit reached
                        logmsg('debug','limit ('+str(limit)+') reached - setting pin '+str(config['autopin']))
                        cmd='SetPin'
                        params={'0':config['autopin']}
                        i=0
                        while i<len(params):
                            cmd+=' '+str(params[str(i)])
                            i+=1
                        try:
                            data=await conn.send(cmd)
                            if data['Successful'] is True: logmsg('debug','setpin has set the pin')
                            else: logmsg('error','setpin has NOT set the pin for some reason')
                        except Exception as e:
                            if str(e)!='': logmsg('error','EXCEPTION in '+fx+': '+str(e))
                    else: # below limit
                        logmsg('debug','below limit ('+str(limit)+') - removing pin')
                        cmd='SetPin'
                        params={'0':' '}
                        i=0
                        while i<len(params):
                            cmd+=' '+str(params[str(i)])
                            i+=1
                        try:
                            data=await conn.send(cmd)
                            if data['Successful'] is True: logmsg('debug','setpin has emptied the pin')
                            else: logmsg('error','setpin has NOT emptied the pin for some reason')
                        except Exception as e:
                            if str(e)!='': logmsg('error','EXCEPTION in '+fx+' when emptying pin: '+str(e))
                else: logmsg('warn','not touching pin because of roundstate '+str(roundstate))
            else: logmsg('info','not touching pin because autopin is disabled')

            # MANAGE BOTS (ADD)
            if config['rconplus'][srv] is True:
                if config['bots'][srv]['managed'] is True:
                    amount=int(config['bots'][srv]['amount'])
                    if amount!=0:
                        if roundstate=='Started':

                            logmsg('debug','this is the time to manage bots... but that code is missing atm')

                            #if mode=="add":
                            #    if gamemode=="TDM" or gamemode=="TANKTDM" or gamemode=="WW2TDM":
                            #        await rcon('AddBot',{'0':'1','1':'RedTeam'},True)
                            #        logmsg('info',fx+' probably added 1 bot to RedTeam')
                            #        await rcon('AddBot',{'0':'1','1':'BlueTeam'},True)
                            #        logmsg('info',fx+' probably added 1 bot to BlueTeam')
                            #    elif gamemode=="DM" or gamemode=="CUSTOM":
                            #        await rcon('AddBot',{'0':'1'},True)
                            #        logmsg('info',fx+' probably added 1 bot')

                        else: logmsg('warn','not managing bots because of roundstate '+str(roundstate))
                    else: logmsg('info','not managing bots because amount is 0')
                else: logmsg('info','not managing bots because "managed" is not true')
            else: logmsg('info','not managing bots because rconplus is disabled')

        except Exception as e:
            if str(e)!='': logmsg('error','EXCEPTION in '+fx+': '+str(e))
        await conn.send('Disconnect')


    async def pullstats():
        fx=inspect.stack()[0][3]
        logmsg('debug','pullstats called')

        port=config['rcon']['port']+int(srv)
        conn=PavlovRCON(config['rcon']['ip'],port,config['rcon']['pass'])

        try:
            data=await conn.send('ServerInfo')
            data_json=json.dumps(data)
            serverinfo=json.loads(data_json)
            si=serverinfo['ServerInfo']
            maplabel=str(si['MapLabel'].lower()).strip()
            gamemode=str(si['GameMode'].upper()).strip()
            roundstate=str(si['RoundState']).strip()

            # demo rec counts as 1 player in SND
            if gamemode=="SND":
                numberofplayers0=si['PlayerCount'].split('/',2)
                numberofplayers1=numberofplayers0[0]

                # demo only exists if there is players
                if int(numberofplayers1)>0: numberofplayers2=(int(numberofplayers1)-1)
                else: numberofplayers2=(numberofplayers0[0])

                maxplayers=numberofplayers0[1]
                playercount=str(numberofplayers2)+'/'+str(maxplayers)
            else: playercount=si['PlayerCount']

            # for SND get info if match has ended and which team won
            si['MatchEnded']=False
            si['WinningTeam']='none'
            if si['GameMode']=="SND" and si['Teams'] is True:
                if int(si['Team0Score'])==10:
                    si['MatchEnded']=True
                    si['WinningTeam']='team0'
                elif int(si['Team1Score'])==10:
                    si['MatchEnded']=True
                    si['WinningTeam']='team1'
            else:
                si['Team0Score']=0
                si['Team1Score']=0    

            # only pull stats if match ended and gamemode is SND
            if si['MatchEnded'] is True and si=="SND":
                logmsg('debug','actually pulling stats now')

                # pull scoreboard
                try:
                    data=await conn.send('InspectAll')
                    data_json=json.dumps(data)
                    inspectall=json.loads(data_json)
                    for player in inspectall['InspectList']:
                        kda=player['KDA'].split('/',3)
                        kills=kda[0]
                        deaths=kda[1]
                        assists=kda[2]
                        score=player['Score']
                        ping=player['Ping']

                        logmsg('debug','player: '+str(player))
                        logmsg('debug','player[PlayerName]: '+str(player['PlayerName']))
                        logmsg('debug','player[UniqueId]: '+str(player['UniqueId']))
                        logmsg('debug','player[KDA]: '+str(player['KDA']))
                        logmsg('debug','kills: '+str(kills))
                        logmsg('debug','deaths: '+str(deaths))
                        logmsg('debug','assists: '+str(assists))
                        logmsg('debug','score: '+str(score))
                        logmsg('debug','ping: '+str(ping))
                        if str(player['TeamId'])!='':
                            logmsg('debug','player[TeamId]: '+str(player['TeamId']))

                        # check if user exists in steamusers
                        logmsg('debug','checking if user exists in db')
                        query="SELECT * FROM steamusers WHERE steamid64 = %s LIMIT 1"
                        values=[]
                        values.append(str(player['UniqueId']))
                        steamusers=dbquery(query,values)

                        # if user does not exist, add user
                        if steamusers['rowcount']==0:
                            logmsg('debug','adding user to db because not found')
                            query="INSERT INTO steamusers (steamid64) VALUES (%s)"
                            values=[]
                            values.append(str(player['UniqueId']))
                            dbquery(query,values)
                        else:
                            logmsg('debug','steam user already in db: '+str(player['UniqueId']))

                        # read steamuser id
                        logmsg('debug','getting steamusers id from db')
                        query="SELECT id FROM steamusers WHERE steamid64=%s LIMIT 1"
                        values=[]
                        values.append(str(player['UniqueId']))
                        steamusers=dbquery(query,values)
                        steamuser_id=steamusers['rows'][0]['id']

                        # add stats for user
                        logmsg('info','adding stats for user')
                        timestamp=datetime.now(timezone.utc)            
                        query="INSERT INTO stats ("
                        query+="steamusers_id,kills,deaths,assists,score,ping,servername,playercount,mapugc,"
                        query+="gamemode,matchended,teams,team0score,team1score,timestamp"
                        query+=") VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                        values=[
                            steamuser_id,kills,deaths,assists,score,ping,si['ServerName'],si['PlayerCount'],
                            si['MapLabel'],si['GameMode'],si['MatchEnded'],
                            si['Teams'],si['Team0Score'],si['Team1Score'],timestamp]
                        dbquery(query,values)
                except Exception as e:
                    if str(e)!='': logmsg('error','EXCEPTION in '+fx+': '+str(e))
                logmsg('info',fx+' has processed all current players')
            else: logmsg('info','not pulling stats because either gamemode is not SND or the match did not end yet')
        except Exception as e:
            if str(e)!='': logmsg('error','EXCEPTION in '+fx+': '+str(e))
        await conn.send('Disconnect')


    def process_found_keyword(line,keyword):
        match keyword:
            case 'LogHAL': logmsg('info','server is starting')

            case 'Server Status Helper':
                logmsg('info','server is now online')
                asyncio.run(init_server())

            case 'Rotating map':
                logmsg('info','map rotation called')

            case 'PavlovLog: StartPlay': logmsg('info','map started')

            case 'KillData': logmsg('debug','a player died...')

            case 'LogLoad: LoadMap':
                if '/Game/Maps/ServerIdle' in line: logmsg('info','map switch called')

            case '"State":':
                roundstate0=line.split('": "',1)
                roundstate1=roundstate0[1].split('"',1)
                roundstate=roundstate1[0]
                logmsg('info','round state changed to: '+str(roundstate).strip())
                match roundstate:
                    case 'Starting': asyncio.run(init_round())
                    #case 'StandBy':
                    #case 'Started':
                    case 'Ended': asyncio.run(pullstats())

            case 'Join succeeded':
                joinuser0=line.split('succeeded: ',2)
                joinuser=str(joinuser0[1]).strip()
                logmsg('info','join successful for user: '+joinuser)
                asyncio.run(player_joined(joinuser))

            case 'LogNet: UChannel::Close':
                leaveuser0=line.split('RemoteAddr: ',2)
                leaveuser1=leaveuser0[1].split(',',2)
                leaveuser=leaveuser1[0]
                logmsg('info','user left the server: '+str(leaveuser).strip())
                asyncio.run(player_left())

            case 'LogTemp: Rcon: KickPlayer':
                kickplayer0=line.split('KickPlayer ',2)
                kickplayer=kickplayer0[1]
                logmsg('info','player kicked: '+str(kickplayer).strip())
                asyncio.run(player_left())

            case 'LogTemp: Rcon: BanPlayer':
                banplayer0=line.split('BanPlayer ',2)
                banplayer=banplayer0[1]
                logmsg('info','player banned: '+str(banplayer).strip())
                asyncio.run(player_left())
                
            case 'Critical error': logmsg('error','server crashed: critical error')
                
            case 'Fatal error': logmsg('error','server crashed: fatal error')

            case 'Preparing to exit': logmsg('warn','server is shutting down')


    def find_keyword_in_line(line,keywords):
        for keyword in keywords:
            if keyword in line: return keyword


    def follow_log(target_log):
        seek_end=True
        while True:
            with open(target_log) as f:
                if seek_end: f.seek(0,2)
                while True:
                    line=f.readline()
                    if not line:
                        try:
                            if f.tell() > os.path.getsize(target_log):
                                f.close()
                                seek_end = False
                                break
                        except FileNotFoundError: pass
                        time.sleep(1)
                    yield line


    target_log=config['target_log']
    logmsg('info',meta['name']+' '+meta['version']+' is now active ('+target_log+')')
    loglines=follow_log(target_log)
    for line in loglines:
        if line!="":
            found_keyword=find_keyword_in_line(line,[
                'Rotating map',
                'LogLoad: LoadMap',
                'StartPlay',
                '"State":',
                'Preparing to exit',
                'LogHAL',
                'Server Status Helper',
                'Rcon: User',
                'Join succeeded',
                'LogNet: UChannel::Close',
                'KillData',
                'LogTemp: Rcon: KickPlayer',
                'LogTemp: Rcon: BanPlayer',
                'Critical error',
                'Fatal error'])
            if found_keyword!='': process_found_keyword(line,found_keyword)
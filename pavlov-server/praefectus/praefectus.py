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

        if config['rconplus'][srv] is True:
            try:
                port=config['rcon']['port']+int(srv)
                conn=PavlovRCON(config['rcon']['ip'],port,config['rcon']['pass'])

                # INIT WORKAROUND TO MAKE SURE RCONPLUS IS AVAILABLE
                roundstate=''
                while roundstate!='Started' and roundstate!='Starting':
                    data=await conn.send('ServerInfo')
                    data_json=json.dumps(data)
                    serverinfo=json.loads(data_json)
                    si=serverinfo['ServerInfo']
                    maplabel=str(si['MapLabel'])
                    gamemode=str(si['GameMode'].upper()).strip()
                    roundstate=str(si['RoundState']).strip()

                    if 'UGC' in maplabel: maplabel=str(si['MapLabel'].upper()).strip()
                    else: maplabel=str(si['MapLabel'].lower()).strip()
                    gamemode=str(si['GameMode'].upper()).strip()

                    if roundstate=='Started' or roundstate=='Starting':

                        # LOAD RCONPLUS
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

                        # RELOAD CURRENT MAP
                        cmd='SwitchMap'
                        params={'0':maplabel,'1':gamemode}
                        i=0
                        while i<len(params):
                            cmd+=' '+str(params[str(i)])
                            i+=1
                        try:
                            data=await conn.send(cmd)
                            data_json=json.dumps(data)
                            rotatemap=json.loads(data_json)
                            if rotatemap['Successful'] is True:
                                logmsg('info','init workaround switchmap has been called successfully')
                            else: logmsg('error','init workaround switchmap has NOT been called successfully for some reason')
                        except Exception as e:
                                if str(e)!='': logmsg('error','EXCEPTION in '+fx+' when reloading current map: '+str(e))

                    else:
                        logmsg('debug','init workaround switchmap has to wait for roundstate "Started" or "Starting"')
                        time.sleep(3)
                
                await conn.send('Disconnect')
                logmsg('debug','rcon conn disconnected')
            except Exception as e:
                if str(e)!='': logmsg('error','EXCEPTION in '+fx+': '+str(e))
        else: logmsg('info','rconplus is disabled - no need for init workaround')


    async def init_round_map():
        fx=inspect.stack()[0][3]
        logmsg('debug',fx+' called')
        if config['rconplus'][srv] is True:
            try:
                port=config['rcon']['port']+int(srv)
                conn=PavlovRCON(config['rcon']['ip'],port,config['rcon']['pass'])

                data=await conn.send('ServerInfo')
                data_json=json.dumps(data)
                serverinfo=json.loads(data_json)
                si=serverinfo['ServerInfo']
                maplabel=str(si['MapLabel'])
                gamemode=str(si['GameMode'].upper()).strip()

                if 'UGC' in maplabel: maplabel=str(si['MapLabel'].upper()).strip()
                else: maplabel=str(si['MapLabel'].lower()).strip()
                gamemode=str(si['GameMode'].upper()).strip()

                is_first_round=True
                if 'Teams' in si:
                    if 'Team0Score' in si or 'Team1Score' in si:
                        if gamemode=='SND' and (int(si['Team0Score'])!=0 or int(si['Team1Score'])!=0): is_first_round=False

                # INIT ROUND
                if is_first_round is True:
                    logmsg('info','initiating round/map now...')
                    logmsg('info','maplabel: '+maplabel)
                    logmsg('info','gamemode: '+gamemode)
                    logmsg('info','is_first_round: '+str(is_first_round))

                    # ADD BOTS
                    amount=int(config['bots'][srv]['amount'])
                    if amount!=0:
                        if gamemode in gamemodes_teams:
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

                            time.sleep(0.5)
                            # blue team
                            cmd='AddBot'
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
                        elif gamemode in gamemodes_teamless:
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
                        elif gamemode in gamemodes_unsupported:
                            logmsg('warn','not adding bots because "'+gamemode+'" is not supported atm')
                        else:
                            logmsg('error','not adding bots because gamemode: "'+gamemode+' is unknown')
                    else: logmsg('info','bots amount is 0')

                    # ADD CHICKEN
                    amount=int(config['chickens'][srv])
                    if amount!=0:
                        cmd='SpawnChickens'
                        params={'0':str(amount)}
                        i=0
                        while i<len(params):
                            cmd+=' '+str(params[str(i)])
                            i+=1
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
                        i=0
                        while i<len(params):
                            cmd+=' '+str(params[str(i)])
                            i+=1
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
                        i=0
                        while i<len(params):
                            cmd+=' '+str(params[str(i)])
                            i+=1
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
                        i=0
                        while i<len(params):
                            cmd+=' '+str(params[str(i)])
                            i+=1
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
                        i=0
                        while i<len(params):
                            cmd+=' '+str(params[str(i)])
                            i+=1
                        try:
                            await conn.send(cmd)
                        except Exception as e:
                            if str(e)!='': logmsg('error','EXCEPTION in '+fx+' when enabling nofalldmg: '+str(e))
                        logmsg('info','nofalldamage has probably been enabled')
                    else: logmsg('info','nofalldamage is disabled')

                else: logmsg('info','not initiating round because is_first_round not true')
                await conn.send('Disconnect')
                logmsg('debug','rcon conn disconnected')
            except Exception as e:
                if str(e)!='': logmsg('error','EXCEPTION in '+fx+': '+str(e))
        else: logmsg('info','not initiating round because rconplus is disabled')


    async def player_joined(joinuser):
        fx=inspect.stack()[0][3]
        logmsg('debug',fx+' called')
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

            if 'UGC' in maplabel: maplabel=str(si['MapLabel'].upper()).strip()
            else: maplabel=str(si['MapLabel'].lower()).strip()
            gamemode=str(si['GameMode'].upper()).strip()

            playercount_split=si['PlayerCount'].split('/',2)
            numberofplayers=int(playercount_split[0])
            maxplayers=int(playercount_split[1])
            
            demo_enabled=False # get this via rcon
            if demo_enabled is True: # demo rec counts as 1 player
                if int(numberofplayers)>0: numberofplayers=(numberofplayers-1) # demo only exists if there are players
            
            if gamemode=="SND": # for whatever reason SND has 1 additional player (with comp mode off and demo off)
                if int(numberofplayers)>0: numberofplayers=(numberofplayers-1)

            # WELCOME PLAYER
            if config['rconplus'][srv] is True:
                if roundstate=='Starting' or roundstate=='Started' or roundstate=='StandBy':
                    try:
                        data=await conn.send('RefreshList')
                        data_json=json.dumps(data)
                        refreshlist=json.loads(data_json)

                        data=await conn.send('ModeratorList')
                        data_json=json.dumps(data)
                        modlist=json.loads(data_json)

                        for player in refreshlist['PlayerList']:
                            steamid64=str(player['UniqueId']).strip()

                            cmd='InspectPlayer'
                            params={'0':steamid64}
                            i=0
                            while i<len(params):
                                cmd+=' '+str(params[str(i)])
                                i+=1
                            data=await conn.send(cmd)
                            data_json=json.dumps(data)
                            inspectplayer=json.loads(data_json)

                            kda=inspectplayer['PlayerInfo']['KDA'].split('/',3)
                            kills=kda[0]
                            deaths=kda[1]
                            assists=kda[2]
                            score=inspectplayer['PlayerInfo']['Score']
                            current_ping=inspectplayer['PlayerInfo']['Ping']
                            playername=str(inspectplayer['PlayerInfo']['PlayerName']).strip()

                            steamid64_of_joinuser=''
                            if str(joinuser)==playername:
                                steamid64_of_joinuser=steamid64

                                for mod in modlist['ModeratorList']:
                                    mod_split=mod.split('#',2)
                                    mod_steamid64=str(mod_split[0]).strip()
                                    if steamid64_of_joinuser==mod_steamid64:
                                        cmd='GiveMenu'
                                        params={'0':steamid64_of_joinuser}
                                        i=0
                                        while i<len(params):
                                            cmd+=' '+str(params[str(i)])
                                            i+=1
                                        try:
                                            await conn.send(cmd)
                                        except Exception as e:
                                            if str(e)!='': logmsg('error','EXCEPTION in '+fx+' when giving menu to spqr agent: '+str(e))
                                        logmsg('info','givemenu has probably been set for '+steamid64_of_joinuser+' ('+joinuser+')')

                            if steamid64_of_joinuser!='':
                                time.sleep(1)

                                msg=str(si['ServerName'])+'\n\n'
                                msg+='WELCOME, '+joinuser+' :)'
                                cmd='Notify'
                                params={'0':steamid64_of_joinuser,'1':msg}
                                i=0
                                while i<len(params):
                                    cmd+=' '+str(params[str(i)])
                                    i+=1
                                try:
                                    await conn.send(cmd)
                                except Exception as e:
                                    if str(e)!='': logmsg('error','EXCEPTION in '+fx+' when welcoming player: '+str(e))
                                logmsg('info','player '+steamid64_of_joinuser+' has been welcomed')
                            else: logmsg('error','steamid64 was emtpy when trying to welcome player')

                    except Exception as e:
                        if str(e)!='': logmsg('error','EXCEPTION in '+fx+': '+str(e))
                else: logmsg('warn','not welcoming player because roundstate is '+roundstate)
            else: logmsg('info','not welcoming player because rconplus is disabled')

            await conn.send('Disconnect')
            logmsg('debug','rcon conn disconnected')

        except Exception as e:
            if str(e)!='': logmsg('error','EXCEPTION in '+fx+': '+str(e))


    async def player_left():
        fx=inspect.stack()[0][3]
        logmsg('debug',fx+' called')
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

            # MANAGE BOTS (ADD)
            if config['rconplus'][srv] is True:
                if config['bots'][srv]['managed'] is True:
                    amount=int(config['bots'][srv]['amount'])
                    if amount!=0:
                        if roundstate=='Started':

                            if gamemode in gamemodes_teams:
                                
                                team=random.randint(0,1)
                                cmd='AddBot'
                                params={'0':'1','1':team}
                                i=0
                                while i<len(params):
                                    cmd+=' '+str(params[str(i)])
                                    i+=1
                                try:
                                    await conn.send(cmd)
                                except Exception as e:
                                    if str(e)!='': logmsg('error','EXCEPTION in '+fx+' when adding 1 bot: '+str(e))
                                logmsg('info','probably added 1 bot to team: '+str(team))

                            elif gamemode in gamemodes_teamless:
                                cmd='AddBot'
                                params={'0':'1'}
                                i=0
                                while i<len(params):
                                    cmd+=' '+str(params[str(i)])
                                    i+=1
                                try:
                                    await conn.send(cmd)
                                except Exception as e:
                                    if str(e)!='': logmsg('error','EXCEPTION in '+fx+' when adding 1 bot: '+str(e))
                                logmsg('info','probably added 1 bot')
                            elif gamemode in gamemodes_unsupported:
                                logmsg('warn','not adding bot because "'+gamemode+'" is not supported atm')
                            else:
                                logmsg('error','not adding bot because gamemode: "'+gamemode+' is unknown')

                        else: logmsg('warn','not managing bots because of roundstate '+str(roundstate))
                    else: logmsg('info','not managing bots because amount is 0')
                else: logmsg('info','not managing bots because "managed" is not true')
            else: logmsg('info','not managing bots because rconplus is disabled')

            await conn.send('Disconnect')
            logmsg('debug','rcon conn disconnected')

        except Exception as e:
            if str(e)!='': logmsg('error','EXCEPTION in '+fx+': '+str(e))


    async def pullstats():
        fx=inspect.stack()[0][3]
        logmsg('debug','pullstats called')
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

            # get info if match has ended and which team won
            si['MatchEnded']=False
            si['WinningTeam']='none'
            if gamemode in gamemodes_teams and si['Teams'] is True:
                if int(si['Team0Score'])==10:
                    si['MatchEnded']=True
                    si['WinningTeam']='team0'
                elif int(si['Team1Score'])==10:
                    si['MatchEnded']=True
                    si['WinningTeam']='team1'
            else:
                si['Team0Score']=0
                si['Team1Score']=0    

            # pull stats if match ended
            if gamemode in gamemodes_teams or gamemode in gamemodes_teamless:
                if (gamemode=="SND" and si['MatchEnded'] is True) or gamemode!="SND":
                    logmsg('debug','pulling stats now')

                    try:
                        data=await conn.send('RefreshList')
                        data_json=json.dumps(data)
                        refreshlist=json.loads(data_json)

                        for player in refreshlist['PlayerList']:
                            steamid64=str(player['UniqueId']).strip()

                            cmd='InspectPlayer'
                            params={'0':steamid64}
                            i=0
                            while i<len(params):
                                cmd+=' '+str(params[str(i)])
                                i+=1
                            data=await conn.send(cmd)
                            data_json=json.dumps(data)
                            inspectplayer=json.loads(data_json)

                            kda=inspectplayer['PlayerInfo']['KDA'].split('/',3)
                            kills=kda[0]
                            deaths=kda[1]
                            assists=kda[2]
                            score=inspectplayer['PlayerInfo']['Score']
                            ping=inspectplayer['PlayerInfo']['Ping']
                            playername=str(inspectplayer['PlayerInfo']['PlayerName']).strip()

                            logmsg('debug','player: '+str(player))
                            logmsg('debug','playername: '+str(playername))
                            logmsg('debug','steamid64: '+str(steamid64))
                            logmsg('debug','kills: '+str(kills))
                            logmsg('debug','deaths: '+str(deaths))
                            logmsg('debug','assists: '+str(assists))
                            logmsg('debug','score: '+str(score))
                            logmsg('debug','ping: '+str(ping))
                            if 'TeamId' in inspectplayer['PlayerInfo']:
                                logmsg('debug','inspectplayer[PlayerInfo][TeamId]: '+str(inspectplayer['PlayerInfo']['TeamId']))

                            # check if user exists in steamusers
                            logmsg('debug','checking if user exists in db')
                            query="SELECT * FROM steamusers WHERE steamid64 = %s LIMIT 1"
                            values=[]
                            values.append(str(steamid64))
                            steamusers=dbquery(query,values)

                            # if user does not exist, add user
                            if steamusers['rowcount']==0:
                                logmsg('debug','adding user to db because not found')
                                query="INSERT INTO steamusers (steamid64) VALUES (%s)"
                                values=[]
                                values.append(str(steamid64))
                                dbquery(query,values)
                            else:
                                logmsg('debug','steam user already in db: '+str(steamid64))

                            # read steamuser id
                            logmsg('debug','getting steamusers id from db')
                            query="SELECT id FROM steamusers WHERE steamid64=%s LIMIT 1"
                            values=[]
                            values.append(str(steamid64))
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
                                steamuser_id,kills,deaths,assists,score,ping,si['ServerName'],numberofplayers,
                                si['MapLabel'],si['GameMode'],si['MatchEnded'],
                                si['Teams'],si['Team0Score'],si['Team1Score'],timestamp]
                            dbquery(query,values)
                    except Exception as e:
                        if str(e)!='': logmsg('error','EXCEPTION in '+fx+': '+str(e))
                    logmsg('info',fx+' has processed all current players')
                else: logmsg('debug','not pulling stats because gamemode is SND, but its not the last round yet')
            else: logmsg('debug','not pulling stats because gamemode is not supported')

            await conn.send('Disconnect')
            logmsg('debug','rcon conn disconnected')

        except Exception as e:
            if str(e)!='': logmsg('error','EXCEPTION in '+fx+': '+str(e))


    def process_found_keyword(line,keyword):
        try:
            if line!='':
                if keyword!='':
                    match keyword:

                        case 'PavlovLog: Starting depot http server':
                            port=str(line.split('port: ',2)[1])
                            logmsg('info','http server is now online on port: '+port)

                        case 'LogTemp: Rcon Started Successfully':
                            logmsg('info','rcon server is now online')
                            asyncio.run(init_server())

                        case 'LogTemp: Scanning ...':
                            mod=str(line.split('UGC',2)[1])
                            logmsg('info','scanning mod: '+mod)

                        case 'PavlovLog: Initiating rotation, index':
                            index=str(line.split(' = ',2)[1])
                            logmsg('info','initializing map switch to index: '+index)

                        case 'LogTemp: Switching to Map':
                            newmap=str(line.split('Map ',2)[1])
                            logmsg('info','switching to new map: '+newmap)

                        case 'LogLoad: LoadMap: /UGC':
                            mapugc=line.split('/',3)[1]
                            mapname=str(mapugc[2].split('??',2)[0])
                            mapmode=str(mapname[1].split('=',1)[1])
                            logmsg('info','map has been downloaded: '+mapugc+' ('+mapname+') as '+mapmode)

                        case 'LogLoad: LoadMap: /Game/Maps/download':
                            line_split=line.split('=',2)
                            mapugc=str(line_split[1].split('?',1)[0])
                            mapmode=str(line_split[2])
                            logmsg('info','downloading next map now: '+mapugc+' as '+mapmode)

                        case 'LogGameState: Match State Changed':
                            line_split=line.split(' from ',1)[1]
                            statefrom=str(line_split.split(' to ',1)[0])
                            stateto=str(line_split.split(' to ',1)[1])
                            logmsg('info','match state changed from '+statefrom+' to '+stateto)

                        case '"State":':
                            roundstate0=line.split('": "',1)
                            roundstate1=roundstate0[1].split('"',1)
                            roundstate=roundstate1[0]
                            logmsg('info','round state changed to '+roundstate)
                            match roundstate:
                                case 'Starting': asyncio.run(init_round_map())
                                #case 'StandBy':
                                #case 'Started':
                                case 'Ended': asyncio.run(pullstats())

                        case 'Join succeeded':
                            joinuser=str(line.split('succeeded: ',2)[1]).strip()
                            logmsg('info','user joined the server: '+joinuser)
                            asyncio.run(player_joined(joinuser))

                        case 'LogNet: UChannel::Close':
                            leaveuser0=line.split('RemoteAddr: ',2)
                            leaveuser1=leaveuser0[1].split(',',2)
                            leaveuser=str(leaveuser1[0]).strip()
                            logmsg('info','user left the server: '+leaveuser)
                            asyncio.run(player_left())

                        case 'LogTemp: Rcon: KickPlayer':
                            kickplayer0=line.split('KickPlayer ',2)
                            kickplayer=str(kickplayer0[1]).strip()
                            logmsg('info','player has been kicked: '+kickplayer)
                            asyncio.run(player_left())

                        case 'LogTemp: Rcon: BanPlayer':
                            banplayer0=line.split('BanPlayer ',2)
                            banplayer=str(banplayer0[1]).strip()
                            logmsg('info','player has been banned: '+banplayer)
                            asyncio.run(player_left())

                        case 'LogHAL': logmsg('info','pavlovserver is starting')
                        case 'LogTemp: Starting Server Status Helper': logmsg('info','status helper is now online')
                        case 'StatManagerLog: Stat Manager Started': logmsg('info','statmanager is now online')
                        case 'PavlovLog: Updating blacklist/whitelist/mods': logmsg('info','updating blacklist/whitelist/mods')
                        case 'LogTemp: Scanning Dir': logmsg('info','scanning for mods to load')
                        case 'LogLoad: LoadMap: /Game/Maps/ServerIdle': logmsg('info','server is waiting for next map')
                        case 'PavlovLog: Successfully downloaded all mods': logmsg('info','downloaded all mods required for switching map')
                        case 'PavlovLog: StartPlay was called': logmsg('info','startplay was called')
                        case 'KillData': logmsg('debug','a player died')
                        case 'Critical error': logmsg('error','server crashed: critical error')
                        case 'Fatal error': logmsg('error','server crashed: fatal error')
                        case 'Preparing to exit': logmsg('warn','server is shutting down')
                        #case _:
                        #    logmsg('debug','keyword doesnt match line')
                        #    logmsg('debug','keyword: '+str(keyword).strip())
                        #    logmsg('debug','line: '+str(line).strip())
                else: logmsg('warn','keyword was empty - wtf')
            else: logmsg('warn','line has been empty - wtf')
        except Exception as e:
            if str(e)!='': logmsg('error','EXCEPTION in '+fx+': '+str(e))


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


    gamemodes_teamless=['DM','GUN','OITC','WW2GUN','CUSTOM']
    gamemodes_teams=['PUSH','SND','TANKTDM','TDM','WW2TDM']
    gamemodes_unsupported=['HIDE','PH','INFECTION','KOTH','TTT']
    target_log=config['target_log']
    logmsg('info',meta['name']+' '+meta['version']+' is now active ('+target_log+')')
    loglines=follow_log(target_log)
    for line in loglines:
        line=str(line.strip())
        if line!='':
            found_keyword=find_keyword_in_line(line,[
                'LogTemp: Rcon Started Successfully',
                'LogTemp: Scanning Dir',
                'LogTemp: Scanning ...',
                'PavlovLog: Starting depot http server',
                'PavlovLog: Initiating rotation, index',
                'LogTemp: Switching to Map',
                'PavlovLog: Successfully downloaded all mods'
                'LogLoad: LoadMap: /UGC',
                'LogLoad: LoadMap: /Game/Maps/download',
                'LogGameState: Match State Changed from',
                'PavlovLog: StartPlay was called',
                'LogTemp: Starting Server Status Helper',
                'PavlovLog: Updating blacklist/whitelist/mods',
                'StatManagerLog: Stat Manager Started',
                'LogHAL',
                'LogLoad: LoadMap',
                '"State":',
                'Preparing to exit',
                'Join succeeded',
                'LogNet: UChannel::Close',
                'KillData',
                'LogTemp: Rcon: KickPlayer',
                'LogTemp: Rcon: BanPlayer',
                'Critical error',
                'Fatal error'])
            if found_keyword!='':
                process_found_keyword(line,found_keyword)
import os
import re
import sys
import json
import time
import logging
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


    async def rcon(rconcmd,rconparams,srv):
        port=config['rcon']['port']+int(srv)
        conn=PavlovRCON(config['rcon']['ip'],port,config['rcon']['pass'])
        i=0
        while i<len(rconparams):
            rconcmd+=' '+str(rconparams[str(i)])
            i+=1
        try:
            data=await conn.send(rconcmd)
            data_json=json.dumps(data)
            data=json.loads(data_json)
            await conn.send('Disconnect')
        except:
            data={}
            data['Successful']=False
        return data


    async def get_serverinfo(srv):
        logmsg('debug','get_serverinfo called')
        data=await rcon('ServerInfo',{},srv)
        if data['Successful'] is True:
            # unless during rotation, analyze and if necessary modify serverinfo before returning it
            if data['ServerInfo']['RoundState']!='Rotating':
                serverinfo=data['ServerInfo']

                # make sure gamemode is uppercase
                serverinfo['GameMode']=serverinfo['GameMode'].upper()

                # demo rec counts as 1 player in SND
                if serverinfo['GameMode']=="SND":
                    numberofplayers0=serverinfo['PlayerCount'].split('/',2)
                    numberofplayers1=numberofplayers0[0]

                    # demo only exists if there is players
                    if int(numberofplayers1)>0: numberofplayers2=(int(numberofplayers1)-1)
                    else: numberofplayers2=(numberofplayers0[0])

                    maxplayers=numberofplayers0[1]
                    numberofplayers=str(numberofplayers2)+'/'+str(maxplayers)
                else: numberofplayers=serverinfo['PlayerCount']
                serverinfo['PlayerCount']=numberofplayers

                # for SND get info if match has ended and which team won
                serverinfo['MatchEnded']=False
                serverinfo['WinningTeam']='none'
                if serverinfo['GameMode']=="SND" and serverinfo['Teams'] is True:
                    if int(serverinfo['Team0Score'])==10:
                        serverinfo['MatchEnded']=True
                        serverinfo['WinningTeam']='team0'
                    elif int(serverinfo['Team1Score'])==10:
                        serverinfo['MatchEnded']=True
                        serverinfo['WinningTeam']='team1'
                else:
                    serverinfo['Team0Score']=0
                    serverinfo['Team1Score']=0    
                data['ServerInfo']=serverinfo
            else:
                data['Successful']=False
                data['ServerInfo']=False
        else: data['ServerInfo']=False
        return data


    async def action_serverinfo(srv):
        logmsg('debug','action_serverinfo called')
        data=await get_serverinfo(srv)
        if data['Successful'] is True:
            if data['ServerInfo']['RoundState']!='Rotating':
                logmsg('info','srvname:     '+str(data['ServerInfo']['ServerName']))
                logmsg('info','playercount: '+str(data['ServerInfo']['PlayerCount']))
                logmsg('info','mapugc:      '+str(data['ServerInfo']['MapLabel']))
                logmsg('info','gamemode:    '+str(data['ServerInfo']['GameMode']))
                logmsg('info','roundstate:  '+str(data['ServerInfo']['RoundState']))
                logmsg('info','teams:       '+str(data['ServerInfo']['Teams']))
                if data['ServerInfo']['Teams']==True:
                    logmsg('info','team0score:  '+str(data['ServerInfo']['Team0Score']))
                    logmsg('info','team1score:  '+str(data['ServerInfo']['Team1Score']))
            else: logmsg('warn','cant complete action_serverinfo because map is rotating')
        else: logmsg('warn','get_serverinfo returned unsuccessful')


    async def action_autopin(srv):
        logmsg('debug','action_autopin called')
        if config['autopin_limits'][srv]!=0:
            data=await get_serverinfo(srv)
            if data['Successful'] is True:
                roundstate=data['ServerInfo']['RoundState']
                if roundstate=='Starting' or roundstate!='Started' or roundstate!='Standby':
                    limit=config['autopin_limits'][srv]
                    playercount_split=data['ServerInfo']['PlayerCount'].split('/',2)
                    if (int(playercount_split[0]))>=limit:
                        logmsg('debug','limit ('+str(limit)+') reached - setting pin '+str(config['autopin'])+' for server '+str(srv))
                        data=await rcon('SetPin',{'0':config['autopin']},srv)
                    else:
                        logmsg('debug','below limit ('+str(limit)+') - removing pin for server '+str(srv))
                        data=await rcon('SetPin',{'0':' '},srv)
                else: logmsg('warn','cant complete action_autopin because of roundstate '+str(roundstate)+' for server '+str(srv))
            else: logmsg('warn','action_autopin canceled because get_serverinfo failed for server '+str(srv))
        else: logmsg('warn','action_autopin is disabled for server '+str(srv))


    async def action_pullstats(srv):
        logmsg('debug','action_pullstats called')
        data=await get_serverinfo(srv)
        if data['Successful'] is True:

            # drop maxplayers from playercount
            numberofplayers0=data['ServerInfo']['PlayerCount'].split('/',2)
            numberofplayers=numberofplayers0[0]
            data['ServerInfo']['PlayerCount']=numberofplayers

            # only pull stats if match ended, gamemode is SND and state is not rotating
            if data['ServerInfo']['MatchEnded'] is True:
                if data['ServerInfo']['GameMode']=="SND":
                    logmsg('debug','actually pulling stats now')

                    # pull scoreboard
                    inspectall=await rcon('InspectAll',{},srv)
                    inspectlist=inspectall['InspectList']
                    for player in inspectlist:
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
                            steamuser_id,kills,deaths,assists,score,ping,data['ServerInfo']['ServerName'],data['ServerInfo']['PlayerCount'],
                            data['ServerInfo']['MapLabel'],data['ServerInfo']['GameMode'],data['ServerInfo']['MatchEnded'],
                            data['ServerInfo']['Teams'],data['ServerInfo']['Team0Score'],data['ServerInfo']['Team1Score'],timestamp]
                        dbquery(query,values)

                    logmsg('info','processed all current players')
                else: logmsg('warn','not pulling stats because gamemode is not SND')
            else: logmsg('warn','not pulling stats because matchend is not True')
        else: logmsg('warn','not pulling stats because serverinfo returned unsuccessful')


    async def action_autokickhighping(srv):
        logmsg('debug','action_checkpings called')
        data=[]
        data=await rcon('InspectAll',{},srv)
        if data['Successful'] is True:
            try:
                for player in data['InspectList']:
                    steamid64=player['UniqueId']
                    current_ping=player['Ping']

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
                        logmsg('debug','rowcount ('+str(cnt_ping)+') >= minentries ('+str(config['pinglimit']['minentries'])+')')

                        # check avg ping against soft limit
                        if int(avg_ping)>int(config['pinglimit'][srv]['soft']):
                            logmsg('warn','ping avg ('+str(int(avg_ping))+') exceeds the soft limit ('+str(config['pinglimit'][srv]['soft'])+') for player: '+str(steamid64))
                            if config['pinglimit'][srv]['enabled'] is True:
                                msg='YOUR PING ('+str(int(avg_ping))+') IS TOO HIGH - PLEASE FIX THIS'
                                await rcon('Notify',{'0':steamid64,'1':msg},srv)
                            else: logmsg('warn','player ('+str(steamid64)+') would have been notified by auto-kick-high-ping, but config says "no"')
                        else: logmsg('debug','ping avg ('+str(int(avg_ping))+') is within the soft limit ('+str(config['pinglimit'][srv]['soft'])+') for player: '+str(steamid64))

                        # check avg ping against hard limit
                        if int(avg_ping)>int(config['pinglimit'][srv]['hard']):
                            logmsg('warn','ping avg ('+str(int(avg_ping))+') exceeds the hard limit ('+str(config['pinglimit'][srv]['hard'])+') for player: '+str(steamid64))
                            if config['pinglimit'][srv]['enabled'] is True:
                                msg='YOUR PING ('+str(int(avg_ping))+') IS TOO HIGH - YOU WILL BE KICKED AUTOMATICALLY'
                                await rcon('Notify',{'0':steamid64,'1':msg},srv)
                                time.sleep(1)
                                await rcon('Kick',{'0':steamid64},srv)
                                logmsg('warn','player ('+str(steamid64)+') has been kicked by auto-kick-high-ping')
                            else: logmsg('warn','player ('+str(steamid64)+') would have been kicked by auto-kick-high-ping, but config says "no"')
                        else: logmsg('debug','ping avg ('+str(int(avg_ping))+') is within the hard limit ('+str(config['pinglimit'][srv]['hard'])+') for player: '+str(steamid64))

                        # check min-max-delta
                        min_max_delta=int(max_ping)-int(min_ping)
                        if int(min_max_delta)>int(config['pinglimit'][srv]['delta']):
                            logmsg('warn','ping min-max-delta ('+str(int(min_max_delta))+') exceeds the delta limit ('+str(config['pinglimit'][srv]['delta'])+') for player: '+str(steamid64))
                            if config['pinglimit'][srv]['enabled'] is True:
                                msg='YOUR PING DELTA ('+str(int(min_max_delta))+') IS TOO HIGH - PLEASE FIX THIS'
                                await rcon('Notify',{'0':steamid64,'1':msg},srv)
                            else: logmsg('warn','player ('+str(steamid64)+') would have been notified by auto-kick-high-ping, but config says "no"')
                        else: logmsg('debug','ping min-max-delta ('+str(int(min_max_delta))+') is within the delta limit ('+str(config['pinglimit'][srv]['delta'])+') for player: '+str(steamid64))

                        # delete accumulated entries, but keep some recent ones
                        logmsg('debug','deleting entries for player in pings db')
                        query="DELETE FROM pings WHERE steamid64 = %s ORDER BY id ASC LIMIT %s"
                        values=[]
                        values.append(steamid64)
                        values.append(cnt_ping - int(config['pinglimit']['keepentries']))
                        dbquery(query,values)
                    else: logmsg('debug','not enough data on pings yet')

                    # add the current sample for the current player
                    if str(current_ping)=='0': # not sure yet what these are
                        logmsg('warn','ping is 0 - simply gonna ignore this for now')
                    else:
                        logmsg('debug','adding entry in pings db for player: '+str(steamid64))
                        timestamp=datetime.now(timezone.utc)            
                        query="INSERT INTO pings ("
                        query+="steamid64,ping,timestamp"
                        query+=") VALUES (%s,%s,%s)"
                        values=[steamid64,current_ping,timestamp]
                        dbquery(query,values)

            except Exception as e:
                logmsg('warn','action_autokickhighping failed: '+str(e))
        else: logmsg('warn','action_autokickhighping canceled because InspectAll failed for server '+str(srv))


    async def action_enablerconplus(srv):
        logmsg('debug','action_enablerconplus called')
        if config['rconplus_enabled'][srv]==True:
            await rcon('UGCAddMod',{'0':'UGC3462586'},srv)
            logmsg('info','rconplus has been enabled for server '+str(srv))
        else: logmsg('debug','action_enablerconplus canceled because rconplus is disabled for server '+str(srv))


    async def action_enableprone(srv):
        logmsg('debug','action_enableprone called')
        if config['rconplus_enabled'][srv]==True:
            if config['prone_enabled'][srv]==True:
                await rcon('EnableProne',{'0':'1'},srv)
                logmsg('info','prone has been enabled for server '+str(srv))
            else: logmsg('debug','action_enableprone is disabled for server '+str(srv))
        else: logmsg('debug','action_enableprone canceled because rconplus is disabled for server '+str(srv))


    async def action_enabletrails(srv):
        logmsg('debug','action_enabletrails called')
        if config['rconplus_enabled'][srv]==True:
            if config['trails_enabled'][srv]==True:
                await rcon('UtilityTrails',{'0':'1'},srv)
                logmsg('info','trails have been enabled for server '+str(srv))
            else: logmsg('debug','action_enabletrails is disabled for server '+str(srv))
        else: logmsg('debug','action_enabletrails canceled because rconplus is disabled for server '+str(srv))


    async def action_autobot(srv,mode):
        logmsg('debug','action_autobot called with mode: '+str(mode))
        if config['rconplus_enabled'][srv]==True:


            limit=int(config['autobot_limits'][srv])
            if limit!=0:
                data=await get_serverinfo(srv)
                if data['Successful'] is True:
                    gamemode=data['ServerInfo']['GameMode']
                    roundstate=data['ServerInfo']['RoundState']
                    if roundstate=='Starting' or roundstate!='Started' or roundstate!='Standby':

                        if mode=="init":
                            if gamemode=="TDM" or gamemode=="TANKTDM" or gamemode=="SND":
                                #add_red=limit//2
                                #add_blue=(limit//2)+1
                                #await rcon('AddBot',{'0':str(add_red),'1':'0'},srv)
                                #logmsg('info','action_autobot added '+str(add_red)+' bots to RedTeam')
                                #await rcon('AddBot',{'0':str(add_blue),'1':'1'},srv)
                                #logmsg('info','action_autobot added '+str(add_blue)+' bots to BlueTeam')

                                add_rnd=random.randint(0,1)
                                await rcon('AddBot',{'0':str(limit),'1':str(add_rnd)},srv)
                                logmsg('info','action_autobot added '+str(limit)+' bots to team: '+str(add_rnd))
                            else:
                                await rcon('AddBot',{'0':str(limit),'1':'0'},srv)
                                logmsg('info','action_autobot added '+str(limit)+' bots to RedTeam')

                        elif mode=="add":
                            if gamemode=="TDM" or gamemode=="TANKTDM" or gamemode=="SND":
                                #await rcon('AddBot',{'0':'1','1':'0'},srv)
                                #logmsg('info','action_autobot added 1 bot to RedTeam')
                                #await rcon('AddBot',{'0':'1','1':'1'},srv)
                                #logmsg('info','action_autobot added 1 bot to BlueTeam')

                                add_rnd=random.randint(0,1)
                                await rcon('AddBot',{'0':'1','1':str(add_rnd)},srv)
                                logmsg('info','action_autobot added 1 bot to team: '+str(add_rnd))
                            else:
                                await rcon('AddBot',{'0':'1','1':'0'},srv)
                                logmsg('info','action_autobot added 1 bot to RedTeam')

                        elif mode=="remove":
                            if gamemode=="TDM" or gamemode=="TANKTDM" or gamemode=="SND":
                                #await rcon('RemoveBot',{'0':'1','1':'0'},srv)
                                #logmsg('info','action_autobot removed 1 bot from RedTeam')
                                #await rcon('RemoveBot',{'0':'1','1':'1'},srv)
                                #logmsg('info','action_autobot removed 1 bot from BlueTeam')

                                add_rnd=random.randint(0,1)
                                await rcon('RemoveBot',{'0':'1','1':str(add_rnd)},srv)
                                logmsg('info','action_autobot removed 1 bot to team: '+str(add_rnd))
                            else:
                                await rcon('RemoveBot',{'0':'1','1':'0'},srv)
                                logmsg('info','action_autobot removed 1 bot from RedTeam')
                    
                    else: logmsg('warn','action_autobot canceled because of roundstate '+str(roundstate)+' for server '+str(srv))
                else: logmsg('warn','action_autobot canceled because get_serverinfo failed for server '+str(srv))
            else: logmsg('debug','action_autobot is disabled for server '+str(srv))
        else: logmsg('debug','action_autobot canceled because rconplus is disabled for server '+str(srv))


    async def action_autochicken(srv):
        logmsg('debug','action_autochicken called')
        if config['rconplus_enabled'][srv]==True:
            limit=int(config['autochicken_limits'][srv])
            if limit!=0:
                data=await get_serverinfo(srv)
                if data['Successful'] is True:
                    await rcon('SpawnChickens',{'0':str(limit)},srv)
                    logmsg('info','action_autochicken added '+str(limit)+' chicken(s)')
                else: logmsg('warn','action_autochicken canceled because get_serverinfo failed for server '+str(srv))
            else: logmsg('debug','action_autochicken is disabled for server '+str(srv))
        else: logmsg('debug','action_autochicken canceled because rconplus is disabled for server '+str(srv))


    async def action_autozombie(srv):
        logmsg('debug','action_autozombie called')
        if config['rconplus_enabled'][srv]==True:
            limit=int(config['autozombie_limits'][srv])
            if limit!=0:
                data=await get_serverinfo(srv)
                if data['Successful'] is True:
                    await rcon('SpawnZombies',{'0':str(limit)},srv)
                    logmsg('info','action_autozombie added '+str(limit)+' zombie(s)')
                else: logmsg('warn','action_autozombie canceled because get_serverinfo failed for server '+str(srv))
            else: logmsg('debug','action_autozombie is disabled for server '+str(srv))
        else: logmsg('debug','action_autozombie canceled because rconplus is disabled for server '+str(srv))


    async def action_welcomeplayer(srv,joinuser):
        logmsg('debug','action_welcomeplayer called')
        if config['rconplus_enabled'][srv]==True:
            data={}
            data=await rcon('InspectAll',{},srv)
            try:
                for player in data['InspectList']:
                    if player['UniqueId']=="76561199476460201" and joinuser=="[EU][SPQR] Agent":

                        await rcon('GiveMenu',{'0':player['UniqueId']},srv)
                        logmsg('info','givemenu has been set for [SPQR] Agent on server '+str(srv))

                        #await rcon('GodMode',{'0':player['UniqueId'],'1':'1'},srv)
                        #logmsg('info','godmode has been set for [SPQR] Agent on server '+str(srv))

                        #await rcon('NoClip',{'0':player['UniqueId'],'1':'1'},srv)
                        #logmsg('info','noclip has been set for [SPQR] Agent on server '+str(srv))

                        await rcon('Notify',{'0':player['UniqueId'],'1':'WELCOME SPQR AGENT'},srv)
                        logmsg('info','[SPQR] Agent has been notified on server '+str(srv))
            except Exception as e:
                logmsg('warn','action_welcomeplayer failed: '+str(e))
        else: logmsg('debug','action_welcomeplayer canceled because rconplus is disabled for server '+str(srv))


    async def action_enablehardcore(srv):
        logmsg('debug','action_enablehardcore called')
        if config['hardcore_enabled'][srv]==True:
            data={}
            data=await rcon('UGCAddMod',{'0':'UGC3951330'},srv)
            if data['Successful'] is True: logmsg('info','hardcore has been enabled')
            else:
                logmsg('warn','error when enabling hardcore - something went wrong')
        else: logmsg('debug','action_enablehardcore is disabled for server '+str(srv))


    def process_found_keyword(line,keyword,srv):
        match keyword:
            case 'LogHAL':
                logmsg('info','server is starting')

            case 'Server Status Helper':
                logmsg('info','server is now online')

            case 'Heart beat received':
                logmsg('info','heartbeat received')
                asyncio.run(action_autopin(srv))
                asyncio.run(action_autokickhighping(srv))

            case 'Rotating map':
                logmsg('info','map rotation called')

            case 'LogLoad: LoadMap':
                if '/Game/Maps/ServerIdle' in line: logmsg('info','map switch called')
                elif '/Game/Maps/download.download' in line:
                    mapugc0=line.split('UGC',1)
                    mapugc=('UGC'+str(mapugc0[1]))
                    logmsg('info','map is being downloaded: '+str(mapugc).strip())
                elif 'LoadMap: /UGC' in line:
                    mapugc0=line.split('LoadMap: /',1)
                    mapugc1=mapugc0[1].split("/",1)
                    mapugc=mapugc1[0]
                    gamemode0=line.split('game=',1)
                    gamemode=gamemode0[1]
                    logmsg('info','custom map is loading: '+str(mapugc).strip()+' as '+str(gamemode).strip())
                elif '/Game/Maps' in line:
                    mapugc0=line.split('Maps/',1)
                    mapugc1=mapugc0[1].split("/",1)
                    mapugc=mapugc1[0]
                    gamemode0=line.split('game=',1)
                    gamemode=gamemode0[1]
                    logmsg('info','vrankrupt map is loading: '+str(mapugc).strip()+' as '+str(gamemode).strip())

            case 'PavlovLog: StartPlay':
                logmsg('info','map started')

            case '"State":':
                roundstate0=line.split('": "',1)
                roundstate1=roundstate0[1].split('"',1)
                roundstate=roundstate1[0]
                logmsg('info','round state changed to: '+str(roundstate).strip())
                match roundstate:
                    case 'Starting':
                        asyncio.run(action_serverinfo(srv))
                        asyncio.run(action_enablerconplus(srv))
                        asyncio.run(action_enableprone(srv))
                        asyncio.run(action_enabletrails(srv))
                        asyncio.run(action_autobot(srv,'init'))
                        asyncio.run(action_autochicken(srv))
                        asyncio.run(action_autozombie(srv))
                        asyncio.run(action_enablehardcore(srv))
                    #case 'Started':
                    #case 'StandBy':
                    case 'Ended':
                        asyncio.run(action_pullstats(srv))

            case 'Join succeeded':
                joinuser0=line.split('succeeded: ',2)
                joinuser=joinuser0[1]
                logmsg('info','join successful for user: '+str(joinuser).strip())
                asyncio.run(action_welcomeplayer(srv,str(joinuser).strip()))
                #asyncio.run(action_autobot(srv,'remove'))
                asyncio.run(action_autobot(srv,'add'))

            case 'LogNet: UChannel::Close':
                leaveuser0=line.split('RemoteAddr: ',2)
                leaveuser1=leaveuser0[1].split(',',2)
                leaveuser=leaveuser1[0]
                logmsg('info','user left the server: '+str(leaveuser).strip())
                #asyncio.run(action_autobot(srv,'add'))

            case '"KillData":':
                logmsg('info','a player died...')

            case 'LogTemp: Rcon: KickPlayer':
                kickplayer0=line.split('KickPlayer ',2)
                kickplayer=kickplayer0[1]
                logmsg('info','player kicked: '+str(kickplayer).strip())

            case 'LogTemp: Rcon: BanPlayer':
                banplayer0=line.split('BanPlayer ',2)
                banplayer=banplayer0[1]
                logmsg('info','player banned: '+str(banplayer).strip())
                
            case 'Critical error:':
                logmsg('error','server crashed: critical error')
                
            case 'Fatal error!':
                logmsg('error','server crashed: fatal error')

            case 'Preparing to exit':
                logmsg('info','server is shutting down')


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


    target_log='/opt/pavlov-server/praefectus/logs/Pavlov.log'
    logmsg('info',str(meta['name'])+' '+str(meta['version'])+' is now active ('+target_log+')')
    loglines=follow_log(target_log)
    for line in loglines:
        if line!="":
            found_keyword=find_keyword_in_line(line,keywords=[
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
                '"KillData":',
                'LogTemp: Rcon: KickPlayer',
                'LogTemp: Rcon: BanPlayer',
                'Heart beat received',
                'Critical error:',
                'Fatal error!'])
            if found_keyword!='': process_found_keyword(line,found_keyword,srv)
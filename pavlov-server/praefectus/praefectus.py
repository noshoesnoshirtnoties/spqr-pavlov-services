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
        logmsg('debug','dbquery called')
        logmsg('debug','query: '+str(query))
        logmsg('debug','values: '+str(values))
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


    async def rcon(rconcmd,rconparams,srv,is_rconplus=False):
        logmsg('debug','rcon called')
        logmsg('debug','rconcmd: '+str(rconcmd))
        logmsg('debug','rconparams: '+str(rconparams))
        logmsg('debug','srv: '+str(srv))
        logmsg('debug','is_rconplus: '+str(is_rconplus))
        port=config['rcon']['port']+int(srv)
        conn=PavlovRCON(config['rcon']['ip'],port,config['rcon']['pass'])
        i=0
        while i<len(rconparams):
            rconcmd+=' '+str(rconparams[str(i)])
            i+=1

        data_return={}
        try:
            data=await conn.send(rconcmd)
            await conn.send('Disconnect')

            if is_rconplus is True: data_return['Successful']=True
            else:
                data_json=json.dumps(data)
                data_return=json.loads(data_json)
            return data_return
        except:
            data_return['Successful']=False
            return data_return


    async def get_serverinfo(srv):
        logmsg('debug','get_serverinfo called')
        logmsg('debug','srv: '+str(srv))
        try:
            data=await rcon('ServerInfo',{},srv)
            if data['Successful'] is True:
                # unless during rotation, analyze and if necessary modify serverinfo before returning it
                roundstate=data['ServerInfo']['RoundState']
                if roundstate!='Rotating':
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
            return data

        except Exception as e:
            logmsg('warn','EXCEPTION in get_serverinfo: '+str(e))
            logmsg('warn','str(type(data)).lower(): '+str(type(data)).lower())


    async def action_serverinfo(srv):
        logmsg('debug','action_serverinfo called')
        logmsg('debug','srv: '+str(srv))
        try:
            data=await get_serverinfo(srv)
            if data['Successful'] is True:
                roundstate=data['ServerInfo']['RoundState']
                if roundstate=='Starting' or roundstate!='Started' or roundstate!='Standby':
                    logmsg('info','srvname:     '+str(data['ServerInfo']['ServerName']))
                    logmsg('info','playercount: '+str(data['ServerInfo']['PlayerCount']))
                    logmsg('info','mapugc:      '+str(data['ServerInfo']['MapLabel']))
                    logmsg('info','gamemode:    '+str(data['ServerInfo']['GameMode']))
                    logmsg('info','roundstate:  '+str(data['ServerInfo']['RoundState']))
                    logmsg('info','teams:       '+str(data['ServerInfo']['Teams']))
                    if data['ServerInfo']['Teams']==True:
                        logmsg('info','team0score:  '+str(data['ServerInfo']['Team0Score']))
                        logmsg('info','team1score:  '+str(data['ServerInfo']['Team1Score']))
                else: logmsg('warn','action_serverinfo canceled because of roundstate '+str(roundstate)+' for server '+str(srv))
            else: logmsg('warn','action_serverinfo canceled because get_serverinfo failed for server '+str(srv))
        except Exception as e:
            logmsg('warn','EXCEPTION in action_serverinfo: '+str(e))
            logmsg('warn','str(type(data)).lower(): '+str(type(data)).lower())


    async def action_autopin(srv):
        logmsg('debug','action_autopin called')
        logmsg('debug','srv: '+str(srv))
        if config['autopin_limits'][srv]!=0:
            try:
                data=await get_serverinfo(srv)
                if data['Successful'] is True:
                    roundstate=data['ServerInfo']['RoundState']
                    if roundstate=='Starting' or roundstate!='Started' or roundstate!='Standby':
                        limit=config['autopin_limits'][srv]
                        playercount_split=data['ServerInfo']['PlayerCount'].split('/',2)
                        if (int(playercount_split[0]))>=limit:
                            logmsg('debug','limit ('+str(limit)+') reached - setting pin '+str(config['autopin'])+' for server '+str(srv))
                            data=await rcon('SetPin',{'0':config['autopin']},srv)
                            if data['Successful'] is True: logmsg('debug','pin has been set for server '+str(srv))
                            else: logmsg('warn','action_autopin failed because rcon failed')
                        else:
                            logmsg('debug','below limit ('+str(limit)+') - removing pin for server '+str(srv))
                            data=await rcon('SetPin',{'0':' '},srv)
                            if data['Successful'] is True: logmsg('debug','pin has been emptied for server '+str(srv))
                            else: logmsg('warn','action_autopin failed because rcon failed')
                    else: logmsg('warn','action_autopin canceled because of roundstate '+str(roundstate)+' for server '+str(srv))
                else: logmsg('warn','action_autopin canceled because get_serverinfo failed for server '+str(srv))
            except Exception as e:
                logmsg('warn','EXCEPTION in action_autopin: '+str(e))
                logmsg('warn','str(type(data)).lower(): '+str(type(data)).lower())
        else: logmsg('warn','action_autopin is disabled for server '+str(srv))


    async def action_pullstats(srv):
        logmsg('debug','action_pullstats called')
        logmsg('debug','srv: '+str(srv))
        try:
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
                        try:
                            data=await rcon('InspectAll',{},srv)
                            for player in data['InspectList']:
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
                        except Exception as e:
                            logmsg('warn','EXCEPTION in action_pullstats: '+str(e))
                            logmsg('warn','str(type(data)).lower(): '+str(type(data)).lower())

                        logmsg('debug','processed all current players')
                    else: logmsg('debug','not pulling stats because gamemode is not SND')
                else: logmsg('debug','not pulling stats because matchend is not True')
            else: logmsg('debug','not pulling stats because serverinfo returned unsuccessful')
        except Exception as e:
            logmsg('warn','EXCEPTION in action_pullstats: '+str(e))
            logmsg('warn','str(type(data)).lower(): '+str(type(data)).lower())


    async def action_pinglimit(srv):
        logmsg('debug','action_pinglimit called')
        logmsg('debug','srv: '+str(srv))
        if config['pinglimit'][srv]['enabled'] is True:
            try:
                data=await get_serverinfo(srv)
                if data['Successful'] is True:
                    roundstate=data['ServerInfo']['RoundState']
                    if roundstate=='Starting' or roundstate!='Started' or roundstate!='Standby':
                        try:
                            data=await rcon('InspectAll',{},srv)
                            if data['Successful'] is True:
                                for player in data['InspectList']:
                                    notify_player=False
                                    kick_player=False

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
                                        avg=int(avg_ping)
                                        delta=int(max_ping)-int(min_ping)
                                        limit_delta=int(config['pinglimit'][srv]['delta'])
                                        limit_soft=int(config['pinglimit'][srv]['soft'])
                                        limit_hard=int(config['pinglimit'][srv]['hard'])

                                        # check delta
                                        if delta>limit_delta:
                                            logmsg('warn','ping delta ('+str(delta)+') exceeds the delta limit ('+str(limit_delta)+') for player: '+str(steamid64))
                                            msg='YOUR CONNECTION SEEMS UNSTABLE (DELTA: '+str(delta)+' - LIMIT IS '+str(limit_delta)+') :( LIMIT IS PLEASE FIX'
                                            notify_player=True
                                        else: logmsg('debug','ping delta ('+str(delta)+') is within the delta limit ('+str(limit_delta)+') for player: '+str(steamid64))

                                        # check avg ping against soft limit
                                        if avg>limit_soft:
                                            logmsg('warn','ping avg ('+str(avg)+') exceeds the soft limit ('+str(limit_soft)+') for player: '+str(steamid64))
                                            msg='YOUR PING IS TOO HIGH (AVG: '+str(avg)+' - LIMIT IS '+str(limit_soft)+') :( PLEASE FIX'
                                            notify_player=True
                                        else: logmsg('debug','ping avg ('+str(avg)+') is within the soft limit ('+str(limit_soft)+') for player: '+str(steamid64))

                                        # check avg ping against hard limit
                                        if avg>limit_hard:
                                            logmsg('warn','ping avg (AVG: '+str(avg)+') exceeds the hard limit ('+str(limit_hard)+') for player: '+str(steamid64))
                                            notify_player=True
                                            msg='YOUR PING IS WAY TOO HIGH ('+str(avg)+' - LIMIT IS '+str(limit_hard)+') :( PLEASE FIX...'
                                            if config['pinglimit'][srv]['kick'] is True:
                                                logmsg('warn','player will be kicked: '+str(steamid64))
                                                msg='YOUR PING IS WAY TOO HIGH ('+str(avg)+' - LIMIT IS '+str(limit_hard)+') :( YOU WILL BE KICKED AUTOMATICALLY...'
                                                kick_player=True
                                            else: logmsg('warn','player ('+str(steamid64)+') would have been kicked by action_pinglimit, but kick is disabled for server '+str(srv))
                                        else: logmsg('debug','ping avg ('+str(avg)+') is within the hard limit ('+str(limit_hard)+') for player: '+str(steamid64))

                                        # notify
                                        if notify_player is True:
                                            if config['rconplus'][srv]==True:
                                                await rcon('Notify',{'0':steamid64,'1':msg},srv,True)
                                                logmsg('info','player ('+str(steamid64)+') has been notified by action_pinglimit on server '+str(srv))
                                            else: logmsg('warn','player ('+str(steamid64)+') can not be notified by action_pinglimit because rconplus is disabled for server '+str(srv))

                                        # kick
                                        if kick_player is True:
                                            time.sleep(2)
                                            await rcon('Kick',{'0':steamid64},srv)
                                            logmsg('warn','player ('+str(steamid64)+') has been kicked by action_pinglimit from server '+str(srv))

                                        # delete accumulated entries, but keep some recent ones
                                        logmsg('debug','deleting entries for player in pings db')
                                        query="DELETE FROM pings WHERE steamid64 = %s ORDER BY id ASC LIMIT %s"
                                        values=[]
                                        values.append(steamid64)
                                        values.append(cnt_ping - int(config['pinglimit']['keepentries']))
                                        dbquery(query,values)
                                    else: logmsg('debug','not enough data on pings yet')

                                    # add the current sample for the current player...
                                    if int(current_ping)==0: # not sure yet what these are
                                        logmsg('warn','ping is 0 - simply gonna ignore this for now')
                                    elif int(current_ping)>1000:
                                        logmsg('warn','ping is >1000 - simply gonna ignore this for now')
                                    elif int(current_ping)>600:
                                        logmsg('warn','ping is >600 - simply gonna ignore this for now')
                                    else:
                                        logmsg('debug','adding entry in pings db for player: '+str(steamid64))
                                        timestamp=datetime.now(timezone.utc)            
                                        query="INSERT INTO pings ("
                                        query+="steamid64,ping,timestamp"
                                        query+=") VALUES (%s,%s,%s)"
                                        values=[steamid64,current_ping,timestamp]
                                        dbquery(query,values)

                            else: logmsg('warn','action_pinglimit canceled because rcon InspectAll failed for server '+str(srv))

                        except Exception as e:
                            logmsg('warn','EXCEPTION in action_pinglimit: '+str(e))
                            logmsg('warn','str(type(data)).lower(): '+str(type(data)).lower())

                    else: logmsg('warn','action_pinglimit canceled because of roundstate '+str(roundstate)+' for server '+str(srv))
                else: logmsg('warn','action_pinglimit canceled because get_serverinfo failed for server '+str(srv))

            except Exception as e:
                logmsg('warn','EXCEPTION in action_pinglimit: '+str(e))
                logmsg('warn','str(type(data)).lower(): '+str(type(data)).lower())

        else: logmsg('debug','action_pinglimit canceled because pinglimit is disabled')


    async def action_enablerconplus(srv):
        logmsg('debug','action_enablerconplus called')
        logmsg('debug','srv: '+str(srv))
        if config['rconplus'][srv] is True:
            try:
                data=await rcon('UGCAddMod',{'0':'UGC3462586'},srv)
                if data['Successful'] is True: logmsg('info','rconplus has been enabled for server '+str(srv))
                else: logmsg('warn','action_enablerconplus failed because rcon failed')
            except Exception as e:
                logmsg('warn','EXCEPTION in action_enablerconplus: '+str(e))
                logmsg('warn','str(type(data)).lower(): '+str(type(data)).lower())
        else: logmsg('debug','action_enablerconplus canceled because rconplus is disabled for server '+str(srv))


    async def action_enableprone(srv):
        logmsg('debug','action_enableprone called')
        logmsg('debug','srv: '+str(srv))
        if config['rconplus'][srv] is True:
            if config['prone'][srv] is True:
                try:
                    data=await rcon('EnableProne',{'0':'1'},srv,True)
                    if data['Successful'] is True: logmsg('info','prone has been enabled for server '+str(srv))
                    else: logmsg('warn','action_enableprone failed because rcon failed')
                except Exception as e:
                    logmsg('warn','EXCEPTION in action_enableprone: '+str(e))
                    logmsg('warn','str(type(data)).lower(): '+str(type(data)).lower())
            else: logmsg('debug','action_enableprone is disabled for server '+str(srv))
        else: logmsg('debug','action_enableprone canceled because rconplus is disabled for server '+str(srv))


    async def action_enabletrails(srv):
        logmsg('debug','action_enabletrails called')
        logmsg('debug','srv: '+str(srv))
        if config['rconplus'][srv] is True:
            if config['trails'][srv] is True:
                try:
                    data=await rcon('UtilityTrails',{'0':'1'},srv,True)
                    if data['Successful'] is True: logmsg('info','trails have been enabled for server '+str(srv))
                    else: logmsg('warn','action_enabletrails failed because rcon failed')
                except Exception as e:
                    logmsg('warn','EXCEPTION in action_enabletrails: '+str(e))
                    logmsg('warn','str(type(data)).lower(): '+str(type(data)).lower())
            else: logmsg('debug','action_enabletrails is disabled for server '+str(srv))
        else: logmsg('debug','action_enabletrails canceled because rconplus is disabled for server '+str(srv))


    async def action_autobot(srv,mode):
        logmsg('debug','action_autobot called')
        logmsg('debug','srv: '+str(srv))
        logmsg('debug','mode: '+str(mode))
        if config['rconplus'][srv] is True:
            amount=int(config['autobot'][srv]['amount'])
            if amount!=0:
                try:
                    data=await get_serverinfo(srv)
                    if data['Successful'] is True:
                        gamemode=data['ServerInfo']['GameMode'].upper()
                        roundstate=data['ServerInfo']['RoundState']
                        if roundstate=='Starting' or roundstate!='Started' or roundstate!='Standby':

                            if mode=="init":
                                if gamemode=="TDM" or gamemode=="TANKTDM" or gamemode=="SND" or gamemode=="WW2TDM":
                                    await rcon('AddBot',{'0':str(amount//2),'1':'RedTeam'},srv,True)
                                    logmsg('info','action_autobot added '+str(amount//2)+' bots to RedTeam')
                                    await rcon('AddBot',{'0':str(amount//2),'1':'BlueTeam'},srv,True)
                                    logmsg('info','action_autobot added '+str(amount//2)+' bots to BlueTeam')
                                else:
                                    await rcon('AddBot',{'0':str(amount)},srv,True)
                                    logmsg('info','action_autobot added '+str(amount)+' bots')
                            else:
                                if config['autobot'][srv]['managed'] is True:
                                    if mode=="add":
                                        if gamemode=="TDM" or gamemode=="TANKTDM" or gamemode=="SND" or gamemode=="WW2TDM":
                                            rnd_team=random.randint(0,1)
                                            await rcon('AddBot',{'0':'1','1':str(rnd_team)},srv,True)
                                            logmsg('info','action_autobot added 1 bot to team: '+str(rnd_team))
                                        else:
                                            await rcon('AddBot',{'0':'1'},srv,True)
                                            logmsg('info','action_autobot added 1 bot')

                                    elif mode=="remove":
                                        if gamemode=="TDM" or gamemode=="TANKTDM" or gamemode=="SND" or gamemode=="WW2TDM":
                                            rnd_team=random.randint(0,1)
                                            await rcon('RemoveBot',{'0':'1','1':str(rnd_team)},srv,True)
                                            logmsg('info','action_autobot removed 1 bot from team: '+str(rnd_team))
                                        else:
                                            await rcon('RemoveBot',{'0':'1'},srv,True)
                                            logmsg('info','action_autobot removed 1 bot')
                                else: logmsg('debug','action_autobot canceled because "managed" not set for server '+str(srv))

                        else: logmsg('warn','action_autobot canceled because of roundstate '+str(roundstate)+' for server '+str(srv))
                    else: logmsg('warn','action_autobot canceled because get_serverinfo failed for server '+str(srv))
                except Exception as e:
                    logmsg('warn','EXCEPTION in action_autobot: '+str(e))
                    logmsg('warn','str(type(data)).lower(): '+str(type(data)).lower())
            else: logmsg('debug','action_autobot is disabled for server '+str(srv))
        else: logmsg('debug','action_autobot canceled because rconplus is disabled for server '+str(srv))


    async def action_autochicken(srv):
        logmsg('debug','action_autochicken called')
        logmsg('debug','srv: '+str(srv))
        if config['rconplus'][srv] is True:
            amount=int(config['autochicken'][srv])
            if amount!=0:
                await rcon('SpawnChickens',{'0':str(amount)},srv,True)
                logmsg('info','action_autochicken added '+str(amount)+' chicken(s)')
            else: logmsg('debug','action_autochicken is disabled for server '+str(srv))
        else: logmsg('debug','action_autochicken canceled because rconplus is disabled for server '+str(srv))


    async def action_autozombie(srv):
        logmsg('debug','action_autozombie called')
        logmsg('debug','srv: '+str(srv))
        if config['rconplus'][srv] is True:
            amount=int(config['autozombie'][srv])
            if amount!=0:
                await rcon('SpawnZombies',{'0':str(amount)},srv,True)
                logmsg('info','action_autozombie added '+str(amount)+' zombie(s)')
            else: logmsg('debug','action_autozombie is disabled for server '+str(srv))
        else: logmsg('debug','action_autozombie canceled because rconplus is disabled for server '+str(srv))


    async def action_welcomeplayer(srv,joinuser):
        logmsg('debug','action_welcomeplayer called')
        logmsg('debug','srv: '+str(srv))
        logmsg('debug','joinuser: '+str(joinuser))
        try:
            data=await get_serverinfo(srv)
            if data['Successful'] is True:
                roundstate=data['ServerInfo']['RoundState']
                if roundstate=='Starting' or roundstate!='Started' or roundstate!='Standby':
                    if config['rconplus'][srv] is True:
                        data=await rcon('InspectAll',{},srv)

                        if data['Successful'] is True:
                            for player in data['InspectList']:
                                if (player['UniqueId']=="76561199476460201" and joinuser=="[EU][SPQR] Agent") or \
                                    (player['UniqueId']=="76561198863982867" and joinuser=="Jack"):

                                    await rcon('GiveMenu',{'0':player['UniqueId']},srv,True)
                                    logmsg('info','givemenu has been set for '+str(player['UniqueId'])+' ('+str(joinuser)+') on server '+str(srv))

                                    #await rcon('GodMode',{'0':player['UniqueId'],'1':'1'},srv,True)
                                    #logmsg('info','godmode has been set for '+str(player['UniqueId'])+' ('+str(joinuser)+') on server '+str(srv))

                                    #await rcon('NoClip',{'0':player['UniqueId'],'1':'1'},srv,True)
                                    #logmsg('info','noclip has been set for '+str(player['UniqueId'])+' ('+str(joinuser)+') on server '+str(srv))

                                    await rcon('Notify',{'0':player['UniqueId'],'1':'WELCOME '+str(joinuser)},srv,True)
                                    logmsg('info','player '+str(player['UniqueId'])+' ('+str(joinuser)+') has been notified on server '+str(srv))
                        else: logmsg('warn','action_welcomeplayer canceled because rcon InspectAll failed for server '+str(srv))
                    else: logmsg('debug','action_welcomeplayer canceled because rconplus is disabled for server '+str(srv))
                else: logmsg('warn','action_welcomeplayer canceled because of roundstate '+str(roundstate)+' for server '+str(srv))
            else: logmsg('warn','action_welcomeplayer canceled because get_serverinfo failed for server '+str(srv))
        except Exception as e:
            logmsg('warn','EXCEPTION in action_welcomeplayer: '+str(e))
            logmsg('warn','str(type(data)).lower(): '+str(type(data)).lower())


    async def action_enablehardcore(srv):
        logmsg('debug','action_enablehardcore called')
        logmsg('debug','srv: '+str(srv))
        if config['hardcore'][srv] is True:
            try:
                data=await rcon('UGCAddMod',{'0':'UGC3951330'},srv)
                if data['Successful'] is True: logmsg('info','hardcore has been enabled')
                else: logmsg('warn','error when enabling hardcore - something went wrong')
            except Exception as e:
                logmsg('warn','EXCEPTION in action_enablehardcore: '+str(e))
                logmsg('warn','str(type(data)).lower(): '+str(type(data)).lower())
        else: logmsg('debug','action_enablehardcore is disabled for server '+str(srv))


    def process_found_keyword(line,keyword,srv):
        match keyword:
            case 'LogHAL': logmsg('info','server is starting')

            case 'Server Status Helper':
                logmsg('info','server is now online')
                asyncio.run(action_enablerconplus(srv))
                asyncio.run(action_enableprone(srv))
                asyncio.run(action_enabletrails(srv))
                asyncio.run(action_enablehardcore(srv))

            case 'Rotating map': logmsg('info','map rotation called')

            case 'PavlovLog: StartPlay': logmsg('info','map started')

            case 'KillData':
                logmsg('info','a player died...')
                asyncio.run(action_pinglimit(srv))
                
            case 'Critical error': logmsg('error','server crashed: critical error')
                
            case 'Fatal error': logmsg('error','server crashed: fatal error')

            case 'Preparing to exit': logmsg('info','server is shutting down')

            case 'Heart beat received':
                logmsg('info','heartbeat received') # doesnt appear anymore in Pavlov.log since the update...
                asyncio.run(action_pinglimit(srv)) # moved elsewhere because this is never reached
                asyncio.run(action_autopin(srv)) # moved elsewhere because this is never reached

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

            case '"State":':
                roundstate0=line.split('": "',1)
                roundstate1=roundstate0[1].split('"',1)
                roundstate=roundstate1[0]
                logmsg('info','round state changed to: '+str(roundstate).strip())
                match roundstate:
                    case 'Starting':
                        asyncio.run(action_serverinfo(srv))
                        asyncio.run(action_pinglimit(srv))
                        asyncio.run(action_autopin(srv))
                    case 'Started':
                        asyncio.run(action_autobot(srv,'init'))
                        asyncio.run(action_autochicken(srv))
                        asyncio.run(action_autozombie(srv))
                    #case 'StandBy':
                    case 'Ended':
                        asyncio.run(action_pullstats(srv))

            case 'Join succeeded':
                joinuser0=line.split('succeeded: ',2)
                joinuser=joinuser0[1]
                logmsg('info','join successful for user: '+str(joinuser).strip())
                asyncio.run(action_welcomeplayer(srv,str(joinuser).strip()))
                asyncio.run(action_pinglimit(srv))
                asyncio.run(action_autopin(srv))

            case 'LogNet: UChannel::Close':
                leaveuser0=line.split('RemoteAddr: ',2)
                leaveuser1=leaveuser0[1].split(',',2)
                leaveuser=leaveuser1[0]
                logmsg('info','user left the server: '+str(leaveuser).strip())
                asyncio.run(action_autopin(srv))

            case 'LogTemp: Rcon: KickPlayer':
                kickplayer0=line.split('KickPlayer ',2)
                kickplayer=kickplayer0[1]
                logmsg('info','player kicked: '+str(kickplayer).strip())
                asyncio.run(action_autopin(srv))

            case 'LogTemp: Rcon: BanPlayer':
                banplayer0=line.split('BanPlayer ',2)
                banplayer=banplayer0[1]
                logmsg('info','player banned: '+str(banplayer).strip())
                asyncio.run(action_autopin(srv))

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
                'Heart beat received',
                'Critical error',
                'Fatal error'])
            if found_keyword!='': process_found_keyword(line,found_keyword,srv)
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


    async def rcon(rconcmd,rconparams,is_rconplus=False):
        fx=inspect.stack()[0][3]
        logmsg('debug',fx+' called')
        #logmsg('debug','rconcmd: '+str(rconcmd))
        #logmsg('debug','rconparams: '+str(rconparams))
        #logmsg('debug','is_rconplus: '+str(is_rconplus))

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

        if is_rconplus is True:
            data={}
            data['Successful']=True
        return data


    async def send_notification(steamid64,msg):
        fx=inspect.stack()[0][3]
        logmsg('debug',fx+' called')
        #logmsg('debug','steamid64: '+str(steamid64))
        #logmsg('debug','msg: '+str(msg))

        if config['rconplus'][srv] is True:
            try:
                await rcon('Notify',{'0':str(steamid64),'1':msg},True)
                logmsg('info','player '+steamid64+' has been notified')
            except Exception as e:
                logmsg('error','EXCEPTION[0] in '+fx+': '+str(e))
        else: logmsg('info',fx+' canceled because rconplus is disabled')


    async def get_serverinfo():
        fx=inspect.stack()[0][3]
        logmsg('debug',fx+' called')

        try:
            data_serverinfo=await rcon('ServerInfo',{})
            if data_serverinfo['Successful'] is True:
                si=data_serverinfo['ServerInfo']
                si['GameMode']=si['GameMode'].upper() # make sure gamemode is uppercase

                # demo rec counts as 1 player in SND
                if si['GameMode']=="SND":
                    numberofplayers0=si['PlayerCount'].split('/',2)
                    numberofplayers1=numberofplayers0[0]

                    # demo only exists if there is players
                    if int(numberofplayers1)>0: numberofplayers2=(int(numberofplayers1)-1)
                    else: numberofplayers2=(numberofplayers0[0])

                    maxplayers=numberofplayers0[1]
                    numberofplayers=str(numberofplayers2)+'/'+str(maxplayers)
                else: numberofplayers=si['PlayerCount']
                si['PlayerCount']=numberofplayers

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
                data_serverinfo['ServerInfo']=si
            return data_serverinfo
        except Exception as e:
            logmsg('error','EXCEPTION[0] in '+fx+': '+str(e))
            return data_serverinfo


    async def init_rotate_workaround():
        fx=inspect.stack()[0][3]
        logmsg('debug',fx+' called')
        
        try:
            data_serverinfo=await get_serverinfo()
            if data_serverinfo['Successful'] is True:
                if str(data_serverinfo['ServerInfo']['MapLabel']).lower()=='datacenter' and \
                    str(data_serverinfo['ServerInfo']['GameMode']).upper()=='CUSTOM':

                    try:
                        data_rotatemap=await rcon('RotateMap',{})
                        if data_rotatemap['Successful'] is True: logmsg('debug',fx+' RotateMap successful')
                    except Exception as e:
                        logmsg('error','EXCEPTION[1] in '+fx+': '+str(e))
                else:
                    logmsg('debug','this didnt work')
                    logmsg('debug','maplabel: '+str(data_serverinfo['ServerInfo']['MapLabel']).lower())
                    logmsg('debug','gamemode: '+str(data_serverinfo['ServerInfo']['GameMode']).upper())
        except Exception as e:
            logmsg('error','EXCEPTION[0] in '+fx+': '+str(e))


    async def log_serverinfo():
        fx=inspect.stack()[0][3]
        logmsg('debug',fx+' called')

        try:
            data_serverinfo=await get_serverinfo()
            if data_serverinfo['Successful'] is True:
                logmsg('info','srvname:     '+str(data_serverinfo['ServerInfo']['ServerName']))
                logmsg('info','playercount: '+str(data_serverinfo['ServerInfo']['PlayerCount']))
                logmsg('info','mapugc:      '+str(data_serverinfo['ServerInfo']['MapLabel']))
                logmsg('info','gamemode:    '+str(data_serverinfo['ServerInfo']['GameMode']))
                logmsg('info','roundstate:  '+str(data_serverinfo['ServerInfo']['RoundState']))
                logmsg('info','teams:       '+str(data_serverinfo['ServerInfo']['Teams']))
                if data_serverinfo['ServerInfo']['Teams']==True:
                    logmsg('info','team0score:  '+str(data_serverinfo['ServerInfo']['Team0Score']))
                    logmsg('info','team1score:  '+str(data_serverinfo['ServerInfo']['Team1Score']))
        except Exception as e:
            logmsg('error','EXCEPTION[0] in '+fx+': '+str(e))


    async def pullstats():
        fx=inspect.stack()[0][3]
        logmsg('debug','pullstats called')

        try:
            data_serverinfo=await get_serverinfo()

            # drop maxplayers from playercount
            numberofplayers0=data_serverinfo['ServerInfo']['PlayerCount'].split('/',2)
            numberofplayers=numberofplayers0[0]
            data_serverinfo['ServerInfo']['PlayerCount']=numberofplayers

            # only pull stats if match ended, gamemode is SND and state is not rotating
            if data_serverinfo['ServerInfo']['MatchEnded'] is True:
                if data_serverinfo['ServerInfo']['GameMode']=="SND":
                    logmsg('debug','actually pulling stats now')

                    # pull scoreboard
                    try:
                        data_serverinfo=await rcon('InspectAll',{})
                        for player in data_serverinfo['InspectList']:
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
                                steamuser_id,kills,deaths,assists,score,ping,data_serverinfo['ServerInfo']['ServerName'],data_serverinfo['ServerInfo']['PlayerCount'],
                                data_serverinfo['ServerInfo']['MapLabel'],data_serverinfo['ServerInfo']['GameMode'],data_serverinfo['ServerInfo']['MatchEnded'],
                                data_serverinfo['ServerInfo']['Teams'],data_serverinfo['ServerInfo']['Team0Score'],data_serverinfo['ServerInfo']['Team1Score'],timestamp]
                            dbquery(query,values)
                    except Exception as e:
                        logmsg('error','EXCEPTION[1] in '+fx+': '+str(e))
                    logmsg('info','processed all current players')
                else: logmsg('info','not pulling stats because gamemode is not SND')
            else: logmsg('debug','not pulling stats because matchend is not True')
        except Exception as e:
            logmsg('error','EXCEPTION[0] in '+fx+': '+str(e))


    async def autopin():
        fx=inspect.stack()[0][3]
        logmsg('debug',fx+' called')

        if config['autopin_limits'][srv]!=0:
            try:
                data_serverinfo=await get_serverinfo()
                if data_serverinfo['Successful'] is True:
                    roundstate=data_serverinfo['ServerInfo']['RoundState']
                    if roundstate=='Starting' or roundstate=='Started' or roundstate=='StandBy' or roundstate=='Ended':
                        limit=config['autopin_limits'][srv]
                        playercount_split=data_serverinfo['ServerInfo']['PlayerCount'].split('/',2)
                        if (int(playercount_split[0]))>=limit:
                            logmsg('debug','limit ('+str(limit)+') reached - setting pin '+str(config['autopin']))
                            try:
                                data_setpin=await rcon('SetPin',{'0':config['autopin']})
                                if data_setpin['Successful'] is True: logmsg('debug','pin has been set')
                            except Exception as e:
                                logmsg('error','EXCEPTION[1] in '+fx+': '+str(e))
                        else:
                            logmsg('debug','below limit ('+str(limit)+') - removing pin')
                            try:
                                data_setpin=await rcon('SetPin',{'0':' '})
                                if data_setpin['Successful'] is True: logmsg('debug','pin has been emptied')
                            except Exception as e:
                                logmsg('error','EXCEPTION[2] in '+fx+': '+str(e))
                    else: logmsg('warn',fx+' canceled because of roundstate '+str(roundstate))
            except Exception as e:
                logmsg('error','EXCEPTION[0] in '+fx+': '+str(e))
        else: logmsg('warn',fx+' canceled because autopin is disabled')


    async def pinglimit():
        fx=inspect.stack()[0][3]
        logmsg('debug','pinglimit called')

        if config['pinglimit'][srv]['enabled'] is True:
            try:
                data_serverinfo=await get_serverinfo()
                roundstate=data_serverinfo['ServerInfo']['RoundState']
                if roundstate=='Starting' or roundstate=='Started' or roundstate=='StandBy' or roundstate=='Ended':
                    try:
                        data_inspectall=await rcon('InspectAll',{})
                        for player in data_inspectall['InspectList']:
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
                                    logmsg('warn','ping delta ('+str(delta)+') exceeds delta limit ('+str(limit_delta)+') for player: '+str(steamid64))
                                    msg='CONNECTION UNSTABLE\n\nDELTA '+str(delta)+' EXCEEDS DELTA LIMIT '+str(limit_delta)+' :('
                                    notify_player=True
                                else: logmsg('debug','ping delta ('+str(delta)+') is within delta limit ('+str(limit_delta)+') for player: '+str(steamid64))

                                # check avg ping against soft limit
                                if avg>limit_soft:
                                    logmsg('warn','ping avg ('+str(avg)+') exceeds soft limit ('+str(limit_soft)+') for player: '+str(steamid64))
                                    msg='PING AVG '+str(avg)+' EXCEEDS SOFT LIMIT '+str(limit_soft)+' :('
                                    notify_player=True
                                else: logmsg('debug','ping avg ('+str(avg)+') is within soft limit ('+str(limit_soft)+') for player: '+str(steamid64))

                                # check avg ping against hard limit
                                if avg>limit_hard:
                                    logmsg('warn','ping avg (AVG: '+str(avg)+') exceeds hard limit ('+str(limit_hard)+') for player: '+str(steamid64))
                                    msg='PING AVG '+str(avg)+' EXCEEDS HARD LIMIT '+str(limit_hard)+' :('
                                    notify_player=True
                                    if config['pinglimit'][srv]['kick'] is True:
                                        logmsg('warn','player will be kicked: '+str(steamid64))
                                        msg='PING AVG '+str(avg)+' EXCEEDS HARD LIMIT '+str(limit_hard)+' :(\n\nYOU WILL BE KICKED AUTOMATICALLY...'
                                        kick_player=True
                                    else: logmsg('warn','player ('+str(steamid64)+') would have been kicked by '+str(fx)+', but kick is disabled')
                                else: logmsg('debug','ping avg ('+str(avg)+') is within hard limit ('+str(limit_hard)+') for player: '+str(steamid64))

                                # notify
                                if notify_player is True:
                                    await send_notification(steamid64,msg)

                                # kick
                                if kick_player is True:
                                    time.sleep(2)
                                    await rcon('Kick',{'0':steamid64})
                                    logmsg('warn','player ('+str(steamid64)+') has been kicked by '+str(fx))

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

                    except Exception as e:
                        logmsg('error','EXCEPTION[1] in '+fx+': '+str(e))

                else: logmsg('warn',fx+' canceled because of roundstate '+str(roundstate))

            except Exception as e:
                logmsg('error','EXCEPTION[0] in '+fx+': '+str(e))

        else: logmsg('debug',fx+' canceled because pinglimit is disabled')


    async def load_rconplus():
        fx=inspect.stack()[0][3]
        logmsg('debug',fx+' called')

        if config['rconplus'][srv] is True:
            try:
                data_addmod=await rcon('UGCAddMod',{'0':'UGC3462586'})
                if data_addmod['Successful'] is True: logmsg('info','rconplus has been enabled')
            except Exception as e:
                logmsg('error','EXCEPTION[0] in '+fx+': '+str(e))
        else: logmsg('info',fx+' canceled because rconplus is disabled')


    async def enable_prone():
        fx=inspect.stack()[0][3]
        logmsg('debug',fx+' called')

        if config['rconplus'][srv] is True:
            if config['prone'][srv] is True:
                try:
                    await rcon('EnableProne',{'0':'1'},True)
                    logmsg('info','prone has probably been enabled')
                except Exception as e:
                    logmsg('error','EXCEPTION[0] in '+fx+': '+str(e))
            else: logmsg('info',fx+' canceled because prone is disabled')
        else: logmsg('info',fx+' canceled because rconplus is disabled')


    async def enable_trails():
        fx=inspect.stack()[0][3]
        logmsg('debug',fx+' called')

        if config['rconplus'][srv] is True:
            if config['trails'][srv] is True:
                try:
                    await rcon('UtilityTrails',{'0':'1'},True)
                    logmsg('info','trails have probably been enabled')
                except Exception as e:
                    logmsg('error','EXCEPTION[0] in '+fx+': '+str(e))
            else: logmsg('info',fx+' canceled because trails are disabled')
        else: logmsg('info',fx+' canceled because rconplus is disabled')


    async def disable_falldamage():
        fx=inspect.stack()[0][3]
        logmsg('debug',fx+' called')

        if config['rconplus'][srv] is True:
            if config['disable_falldamage'][srv] is True:
                try:
                    await rcon('FallDamage',{'0':False},True)
                    logmsg('info','falldamage has probably been disabled')
                except Exception as e:
                    logmsg('error','EXCEPTION[0] in '+fx+': '+str(e))
            else: logmsg('info',fx+' canceled because disabling falldamage is disabled')
        else: logmsg('info',fx+' canceled because rconplus is disabled')


    async def add_bot(mode):
        fx=inspect.stack()[0][3]
        logmsg('debug',fx+' called')
        logmsg('debug','mode: '+str(mode))

        if config['rconplus'][srv] is True:
            amount=int(config['autobot'][srv]['amount'])
            if amount!=0:
                try:
                    data_serverinfo=await get_serverinfo()
                    gamemode=data_serverinfo['ServerInfo']['GameMode'].upper()
                    roundstate=data_serverinfo['ServerInfo']['RoundState']

                    if not (str(data_serverinfo['ServerInfo']['MapLabel']).lower()=='datacenter' and \
                        str(data_serverinfo['ServerInfo']['GameMode']).upper()=='CUSTOM'):

                        if roundstate=='Starting' or roundstate=='Started' or roundstate=='StandBy' or roundstate=='Ended':
                            if gamemode!="SND":
                                if mode=="init":
                                    if gamemode=="TDM" or gamemode=="TANKTDM" or gamemode=="WW2TDM":
                                        await rcon('AddBot',{'0':str(amount//2),'1':'RedTeam'},True)
                                        logmsg('info',fx+' probably added '+str(amount//2)+' bot(s) to RedTeam')
                                        await rcon('AddBot',{'0':str(amount//2),'1':'BlueTeam'},True)
                                        logmsg('info',fx+' probably added '+str(amount//2)+' bot(s) to BlueTeam')
                                    else:
                                        await rcon('AddBot',{'0':str(amount)},True)
                                        logmsg('info',fx+' probably added '+str(amount)+' bot(s)')
                                else:
                                    if config['autobot'][srv]['managed'] is True:
                                        if mode=="add":
                                            if gamemode=="TDM" or gamemode=="TANKTDM" or gamemode=="WW2TDM":
                                                rnd_team=random.randint(0,1)
                                                await rcon('AddBot',{'0':'1','1':str(rnd_team)},True)
                                                logmsg('info',fx+' probably added 1 bot to team '+str(rnd_team))
                                            elif gamemode=="DM" or gamemode=="CUSTOM":
                                                await rcon('AddBot',{'0':'1'},True)
                                                logmsg('info',fx+' probably added 1 bot')
                                        elif mode=="remove":
                                            if gamemode=="TDM" or gamemode=="TANKTDM" or gamemode=="WW2TDM":
                                                rnd_team=random.randint(0,1)
                                                await rcon('RemoveBot',{'0':'1','1':str(rnd_team)},True)
                                                logmsg('info',fx+' probably removed 1 bot from team: '+str(rnd_team))
                                            elif gamemode=="DM" or gamemode=="CUSTOM":
                                                await rcon('RemoveBot',{'0':'1'},True)
                                                logmsg('info',fx+' probably removed 1 bot')
                                    else: logmsg('info',fx+' canceled because "managed" not set')
                            else: logmsg('info',fx+' canceled because gamemode is "SND"')
                        else: logmsg('warn',fx+' canceled because of roundstate '+str(roundstate))
                    else: logmsg('info',fx+' canceled because of datacenter custom init workaround')
                except Exception as e:
                    logmsg('error','EXCEPTION[0] in '+fx+': '+str(e))
            else: logmsg('info',fx+' canceled because bots are disabled')
        else: logmsg('info',fx+' canceled because rconplus is disabled')


    async def add_chicken():
        fx=inspect.stack()[0][3]
        logmsg('debug',fx+' called')

        if config['rconplus'][srv] is True:
            amount=int(config['autochicken'][srv])
            if amount!=0:
                try:
                    data_serverinfo=await get_serverinfo()
                    if not (str(data_serverinfo['ServerInfo']['MapLabel']).lower()=='datacenter' and \
                        str(data_serverinfo['ServerInfo']['GameMode']).upper()=='CUSTOM'):

                        await rcon('SpawnChickens',{'0':str(amount)},True)
                        logmsg('info',fx+' probably added '+str(amount)+' chicken(s)')
                    else: logmsg('info',fx+' canceled because of datacenter custom init workaround')
                except Exception as e:
                    logmsg('error','EXCEPTION[0] in '+fx+': '+str(e))
            else: logmsg('info',fx+' canceled because chickens are disabled')
        else: logmsg('info',fx+' canceled because rconplus is disabled')


    async def add_zombie():
        fx=inspect.stack()[0][3]
        logmsg('debug',fx+' called')

        if config['rconplus'][srv] is True:
            amount=int(config['autozombie'][srv])
            if amount!=0:
                try:
                    data_serverinfo=await get_serverinfo()
                    if not (str(data_serverinfo['ServerInfo']['MapLabel']).lower()=='datacenter' and \
                        str(data_serverinfo['ServerInfo']['GameMode']).upper()=='CUSTOM'):

                        await rcon('SpawnZombies',{'0':str(amount)},True)
                        logmsg('info',fx+' probably added '+str(amount)+' zombie(s)')
                    else: logmsg('info',fx+' canceled because of datacenter custom init workaround')
                except Exception as e:
                    logmsg('error','EXCEPTION[0] in '+fx+': '+str(e))
            else: logmsg('info',fx+' canceled because rconplus is disabled')
        else: logmsg('info',fx+' canceled because rconplus is disabled')


    async def welcome_player(joinuser):
        fx=inspect.stack()[0][3]
        logmsg('debug',fx+' called')
        logmsg('debug','joinuser: '+str(joinuser))

        try:
            data_serverinfo=await get_serverinfo()
            roundstate=data_serverinfo['ServerInfo']['RoundState']
            if roundstate=='Starting' or roundstate=='Started' or roundstate=='StandBy' or roundstate=='Ended':
                if config['rconplus'][srv] is True:
                    try:
                        data_inspectall=await rcon('InspectAll',{})
                        for player in data_inspectall['InspectList']:
                            steamid64=player['UniqueId']

                            if joinuser==player['PlayerName']:
                                data_modlist=await rcon('ModeratorList',{})
                                if steamid64 in data_modlist['ModeratorList']:
                                    await rcon('GiveMenu',{'0':steamid64},True)
                                    logmsg('info','givemenu has probably been set for '+str(steamid64)+' ('+str(joinuser)+')')

                            msg=str(data_serverinfo['ServerInfo']['ServerName'])+'\n\n'
                            msg+='WELCOME :)\n\n'+str(joinuser)
                            await send_notification(steamid64,msg)

                    except Exception as e:
                        logmsg('error','EXCEPTION[1] in '+fx+': '+str(e))
                else: logmsg('info',fx+' canceled because rconplus is disabled')
            else: logmsg('warn',fx+' canceled because roundstate is '+str(roundstate))
        except Exception as e:
            logmsg('error','EXCEPTION[0] in '+fx+': '+str(e))


    async def load_hardcore():
        fx=inspect.stack()[0][3]
        logmsg('debug',fx+' called')

        if config['hardcore'][srv] is True:
            try:
                data_addmod=await rcon('UGCAddMod',{'0':'UGC3951330'})
                if data_addmod['Successful'] is True: logmsg('info','hardcore has been enabled')
            except Exception as e:
                logmsg('error','EXCEPTION[0] in '+fx+': '+str(e))
        else: logmsg('info',fx+' canceled because hardcore is disabled')


    def process_found_keyword(line,keyword):
        match keyword:
            case 'LogHAL': logmsg('info','server is starting')

            case 'Server Status Helper':
                logmsg('info','server is now online')
                asyncio.run(load_rconplus())
                asyncio.run(load_hardcore())
                asyncio.run(enable_prone())
                asyncio.run(enable_trails())
                asyncio.run(disable_falldamage())

            case 'Rotating map': logmsg('info','map rotation called')

            case 'PavlovLog: StartPlay': logmsg('info','map started')

            case 'KillData':
                logmsg('info','a player died...')
                asyncio.run(pinglimit())

            case 'LogLoad: LoadMap':
                if '/Game/Maps/ServerIdle' in line: logmsg('info','map switch called')
                #elif '/Game/Maps/download.download' in line:
                #    mapugc0=line.split('UGC',1)
                #    mapugc=('UGC'+str(mapugc0[1]))
                #    logmsg('info','map is being downloaded: '+str(mapugc).strip())
                #elif 'LoadMap: /UGC' in line:
                #    mapugc0=line.split('LoadMap: /',1)
                #    mapugc1=mapugc0[1].split("/",1)
                #    mapugc=mapugc1[0]
                #    gamemode0=line.split('game=',1)
                #    gamemode=gamemode0[1]
                #    logmsg('info','custom map is loading: '+str(mapugc).strip()+' as '+str(gamemode).strip())
                #elif '/Game/Maps' in line:
                #    mapugc0=line.split('Maps/',1)
                #    mapugc1=mapugc0[1].split("/",1)
                #    mapugc=mapugc1[0]
                #    gamemode0=line.split('game=',1)
                #    gamemode=gamemode0[1]
                #    logmsg('info','vrankrupt map is loading: '+str(mapugc).strip()+' as '+str(gamemode).strip())

            case '"State":':
                roundstate0=line.split('": "',1)
                roundstate1=roundstate0[1].split('"',1)
                roundstate=roundstate1[0]
                logmsg('info','round state changed to: '+str(roundstate).strip())
                match roundstate:
                    case 'Starting':
                        asyncio.run(init_rotate_workaround())
                        asyncio.run(add_chicken())
                        asyncio.run(add_zombie())
                        asyncio.run(add_bot('init'))
                    case 'Started':
                        asyncio.run(autopin())
                        asyncio.run(pinglimit())
                        asyncio.run(log_serverinfo())
                    #case 'StandBy':
                    case 'Ended':
                        asyncio.run(autopin())
                        asyncio.run(pinglimit())
                        asyncio.run(pullstats())

            case 'Join succeeded':
                joinuser0=line.split('succeeded: ',2)
                joinuser=joinuser0[1]
                logmsg('info','join successful for user: '+str(joinuser).strip())
                asyncio.run(autopin())
                asyncio.run(welcome_player(str(joinuser).strip()))

            case 'LogNet: UChannel::Close':
                leaveuser0=line.split('RemoteAddr: ',2)
                leaveuser1=leaveuser0[1].split(',',2)
                leaveuser=leaveuser1[0]
                logmsg('info','user left the server: '+str(leaveuser).strip())
                asyncio.run(autopin())
                asyncio.run(add_bot('add'))

            case 'LogTemp: Rcon: KickPlayer':
                kickplayer0=line.split('KickPlayer ',2)
                kickplayer=kickplayer0[1]
                logmsg('info','player kicked: '+str(kickplayer).strip())
                asyncio.run(autopin())
                asyncio.run(add_bot('add'))

            case 'LogTemp: Rcon: BanPlayer':
                banplayer0=line.split('BanPlayer ',2)
                banplayer=banplayer0[1]
                logmsg('info','player banned: '+str(banplayer).strip())
                asyncio.run(autopin())
                asyncio.run(add_bot('add'))
                
            case 'Critical error': logmsg('error','server crashed: critical error')
                
            case 'Fatal error': logmsg('error','server crashed: fatal error')

            case 'Preparing to exit': logmsg('warn','server is shutting down')

            case 'Heart beat received':
                logmsg('info','heartbeat received') # doesnt appear anymore in Pavlov.log since the update...
                #asyncio.run(pinglimit()) # moved elsewhere because this is never reached
                #asyncio.run(autopin()) # moved elsewhere because this is never reached


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
                'Heart beat received',
                'Critical error',
                'Fatal error'])
            if found_keyword!='': process_found_keyword(line,found_keyword)
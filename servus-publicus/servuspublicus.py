import os
import re
import sys
import json
import time
import logging
import discord
import random
import asyncio
import operator
import inspect
from pavlov import PavlovRCON
import mysql.connector
from pathlib import Path
from pavlov import PavlovRCON
from datetime import datetime,timezone

def run_servuspublicus(meta,config):


    if bool(config['debug'])==True: level=logging.DEBUG
    else: level=logging.INFO
    logging.basicConfig(
        filename='servus-publicus.log',
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


    intents=discord.Intents.default()
    intents.message_content=True
    intents.members=True
    client=discord.Client(intents=intents)


    async def log_discord(message):
        logmsg('debug','log_discord called')
        channel=client.get_channel(int(config['discord']['channel-ids']['e-bot-log']))
        try: await channel.send(message)
        except Exception as e: logmsg('debug',str(e))


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
        fx=inspect.stack()[0][3]
        logmsg('debug',fx+' called')
        logmsg('debug','rconcmd: '+str(rconcmd))
        logmsg('debug','rconparams: '+str(rconparams))
        logmsg('debug','srv: '+str(srv))
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
        data=await rcon('ServerInfo',{},int(srv))
        if data['Successful'] is True:
            # unless during rotation, analyze and if necessary modify serverinfo before returning it
            if data['ServerInfo']['RoundState']!='Rotating':
                si=data['ServerInfo']

                # make sure gamemode is uppercase
                si['GameMode']=si['GameMode'].upper()

                # demo rec counts as 1 player in SND
                if si['GameMode']=="SND":
                    numberofplayers0=si['PlayerCount'].split('/',2)
                    numberofplayers1=numberofplayers0[0]
                    if int(numberofplayers1)>0: # demo only exists if there is players
                        numberofplayers2=(int(numberofplayers1)-1)
                    else:
                        numberofplayers2=(numberofplayers0[0])
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
                
                data['ServerInfo']=si
            else: data['Successful']=False
        else: data['Successful']=False
        return data


    async def send_answer(client,message,user_message,is_private,is_bot_channel):
        response=''
        ums2=user_message.split(' ',2)
        ums3=user_message.split(' ',3)
        ums4=user_message.split(' ',4)
        command=ums2[0]
        command_wo_excl=command[1:]
        if str(command)!='': # this seems to occur with system messages (in discord; like in new-arrivals)

            is_senate=False
            for id in config['discord']['senate-member']:
                if str(id)==str(message.author.id):
                    logmsg('info','user has senate role')
                    is_senate=True

            access_granted=True
            for senatecmd in config['discord']['senate-cmds']:
                if senatecmd==command:
                    logmsg('info','senate-cmd found')
                    if is_senate is not True: access_granted=False

            if access_granted:
                logmsg('info','access to command has been granted')

                if is_bot_channel is True or is_senate is True:
                    log_this=True
                    match command:
                        case '!help':
                            if is_senate is True: response=Path('txt/help_senate.txt').read_text()
                            else: response=Path('txt/help_all.txt').read_text()

                        case '!spqr': response=Path('txt/spqr.txt').read_text()

                        case '!loremipsum': response=Path('txt/loremipsum.txt').read_text()

                        case '!roles': response=Path('txt/roles.txt').read_text()

                        case '!rules': response=Path('txt/rules.txt').read_text()

                        case '!reqs': response=Path('txt/requirements.txt').read_text()

                        case '!suntzu':
                            randomquote=random.choice(os.listdir('txt/suntzu'))
                            quotepath="txt/suntzu/"+randomquote
                            response=Path(str(quotepath)).read_text()

                        case '!showservers':
                            i=0
                            parts=[command+': successful\n']
                            while i<10:
                                data=await get_serverinfo(i)
                                if data['Successful'] is True:
                                    si=data['ServerInfo']
                                    parts.append('(#'+str(i)+') '+str(si['ServerName']))
                                    parts.append(str(si['MapLabel'])+' '+str(si['GameMode']))
                                    parts.append('PlayerCount: '+str(si['PlayerCount'])+'\n')
                                else: parts.append(user_message+': server '+str(i)+' is unreachable\n')
                                i+=1

                            for part in parts: response=response+'\n'+part

                        case '!serverinfo':
                            if len(ums2)>1:
                                data=await get_serverinfo(ums2[1])
                                if data['Successful'] is True:
                                    si=data['ServerInfo']
                                    parts=[
                                        command+': successful\n',
                                        'ServerName: '+str(si['ServerName']),
                                        'PlayerCount: '+str(si['PlayerCount']),
                                        'MapLabel: '+str(si['MapLabel']),
                                        'GameMode: '+str(si['GameMode']),
                                        'RoundState: '+str(si['RoundState']),
                                        'Teams: '+str(si['Teams']),
                                        'Team0Score: '+str(si['Team0Score']),
                                        'Team1Score: '+str(si['Team1Score']),
                                        'MatchEnded: '+str(si['MatchEnded']),
                                        'WinningTeam: '+str(si['WinningTeam'])]
                                    for part in parts: response=response+'\n'+part
                                else: response=command+' failed - something went wrong'
                            else: response=command+' is missing parameters'

                        case '!maplist':
                            if len(ums2)>1:
                                data=await rcon('MapList',{},ums2[1])
                                if data['Successful'] is True:
                                    response=command+': successful'
                                    for part in data['MapList']: response=response+'\n'+str(part['MapId'])+' as '+str(part['GameMode'])
                                else: response=command+' failed - something went wrong'
                            else: response=command+' is missing parameters'

                        case '!playerlist':
                            if len(ums2)>1:
                                data=await rcon('InspectAll',{},ums2[1])
                                if data['Successful'] is True:
                                    response=command+': successful'
                                    for player in data['InspectList']: response=response+'\n'+str(player['PlayerName'])+' ('+str(player['UniqueId'])+')'
                                else: response=command+' failed - something went wrong'
                            else: response=command+' is missing parameters'

                        case '!resetsnd':
                            if len(ums2)>1:
                                data=await rcon('ResetSND',{},ums2[1])
                                if data['Successful'] is True: response=command+' successful'
                                else: response=command+' failed - something went wrong'
                            else: response=command+' is missing parameters'

                        case '!rotatemap':
                            if len(ums2)>1:
                                data=await rcon('RotateMap',{},ums2[1])
                                if data['Successful'] is True: response=command+' successful'
                                else: response=command+' failed - something went wrong'
                            else: response=command+' is missing parameters'

                        case '!setmap':
                            if len(ums4)>2:
                                if len(ums4)<2: response=command+' is missing parameters'
                                else:
                                    data=await rcon('SwitchMap',{'0':ums4[2],'1':ums4[3]},ums4[1])
                                    if data['Successful'] is True: response=command+' successful'
                                    else: response=command+' failed - something went wrong'
                            else: response=command+' is missing parameters'

                        case '!setrandommap':
                            if len(ums2)>1:
                                data=await rcon('MapList',{},ums2[1])
                                i=0
                                poolofrandommaps={}
                                for mapentry in data['MapList']:
                                    if mapentry['GameMode'].upper()=='SND':
                                        if mapentry['MapId'] not in poolofrandommaps:
                                            poolofrandommaps[i]=mapentry['MapId']
                                            i+=1
                                randommap=random.choice(poolofrandommaps)
                                data=await rcon('SwitchMap',{'0':randommap,'1':'SND'},srv)
                                if data['Successful'] is True: response=command+' successful'
                                else: response=command+' failed - something went wrong'
                            else: response=command+' is missing parameters'

                        case '!pause':
                            if len(ums2)>1:
                                data=await rcon('PauseMatch',{'0':'300'},ums2[1])
                                if data['Successful'] is True: response=command+': successful'
                                else: response=command+' failed - something went wrong'
                            else: response=command+' is missing parameters'

                        case '!unpause':
                            if len(ums2)>1:
                                data=await rcon('PauseMatch',{'0':'0'},ums2[1])
                                if data['Successful'] is True: response=command+': successful'
                                else: response=command+' failed - something went wrong'
                            else: response=command+' is missing parameters'

                        case '!kick':
                            if len(ums3)>1:
                                data=await rcon('Kick',{'0':ums3[2]},ums3[1])
                                if data['Successful'] is True: response=command+' successful'
                                else: response=command+' failed - something went wrong'
                            else: response=command+' is missing parameters'

                        case '!ban':
                            if len(ums3)>1:
                                data=await rcon('Ban',{'0':ums3[2]},ums3[2])
                                if data['Successful'] is True: response=command+' successful'
                                else: response=command+' failed - something went wrong'
                            else: response=command+' is missing parameters'

                        case '!unban':
                            if len(ums3)>1:
                                data=await rcon('Unban',{'0':ums3[2]},ums3[1])
                                if data['Successful'] is True: response=command+' successful'
                                else: response=command+' failed - something went wrong'
                            else: response=command+' is missing parameters'

                        case '!modlist':
                            if len(ums2)>1:
                                data=await rcon('ModeratorList',{},ums2[1])
                                if data['Successful'] is True:
                                    response=command+': successful'
                                    for part in data['ModeratorList']: response=response+'\n'+str(part)
                                else: response=command+' failed - something went wrong'
                            else: response=command+' is missing parameters'

                        case '!blacklist':
                            if len(ums2)>1:
                                data=await rcon('Banlist',{},ums2[1])
                                if data['Successful'] is True:
                                    response=command+': successful'
                                    for part in data['BanList']: response=response+'\n'+str(part)
                                else: response=command+' failed - something went wrong'
                            else: response=command+' is missing parameters'

                        case '!pings':
                            if len(ums2)>1:
                                data=await rcon('InspectAll',{},ums2[1])
                                if data['Successful'] is True:
                                    response=command+': successful'
                                    for player in data['InspectList']:
                                        steamusers_id=player['UniqueId']
                                        current_ping=player['Ping']

                                        # get averages for current player
                                        query="SELECT steamid64,ping,"
                                        query+="AVG(ping) as avg_ping "
                                        query+="FROM pings "
                                        query+="WHERE steamid64 = %s"
                                        values=[]
                                        values.append(steamusers_id)
                                        pings=dbquery(query,values)
                                        average_ping=pings['rows'][0]['avg_ping']

                                        response=response+'\n'+steamusers_id+': '+str(current_ping)+' (current), '+str(average_ping)+' (average)'
                                else: response=command+' failed - something went wrong'
                            else: response=command+' is missing parameters'

                        case '!clear':
                            if len(ums2)>1:
                                cl_chn=ums2[1]
                                chn=client.get_channel(int(config['discord']['channel-ids'][cl_chn]))
                                async for del_msg in chn.history(limit=100):
                                    del_msg_id=del_msg.id
                                    old_message=await chn.fetch_message(del_msg_id)
                                    try: await old_message.delete()
                                    except Exception as e: response=str(e).strip()
                                response=command+': successful'
                            else:
                                logmsg('warn',command+' is missing parameters')
                                response=command+' is missing parameters'

                        case '!echo':
                            if len(ums2)>1:
                                response=ums2[1]
                            else:
                                logmsg('warn',command+' is missing parameters')
                                response=command+' is missing parameters'

                        case '!writeas':
                            if len(ums3)>2:
                                wa_channel=ums3[1]
                                wa_ums=user_message.split(command+' '+wa_channel+' ',2)
                                chn=client.get_channel(int(config['discord']['channel-ids'][wa_channel]))
                                try:
                                    await chn.send(wa_ums[1])
                                    response='message sent successfully'
                                except Exception as e: response=str(e).strip()
                            else:
                                logmsg('warn',command+' is missing parameters')
                                response=command+' is missing parameters'

                        case '!register':
                            if len(ums2)>1:
                                steamid64=ums2[1]
                                discordid=message.author.id

                                # check if steamuser exists
                                logmsg('debug','checking if steamid64 exists in steamuser db')
                                query="SELECT id FROM steamusers WHERE steamid64 = %s LIMIT 1"
                                values=[]
                                values.append(steamid64)
                                steamusers=dbquery(query,values)
                                logmsg('debug','steamusers: '+str(steamusers))

                                # add steamuser if it does not exist
                                if steamusers['rowcount']==0:
                                    logmsg('debug','steamid64 not found in steamusers db')
                                    query="INSERT INTO steamusers (steamid64) VALUES (%s)"
                                    values=[]
                                    values.append(steamid64)
                                    dbquery(query,values)
                                    logmsg('info','created entry in steamusers db for steamid64 '+str(steamid64))
                                else: logmsg('debug','steamid64 already exists in steamusers db')
                                
                                # get the steamuser id
                                query="SELECT id FROM steamusers WHERE steamid64 = %s LIMIT 1"
                                values=[]
                                values.append(steamid64)
                                steamusers=dbquery(query,values)
                                steamusers_id=steamusers['rows'][0]['id']
                                
                                # get discorduser id
                                logmsg('debug','checking if discordid exists in discordusers db')
                                query="SELECT id FROM discordusers WHERE discordid = %s LIMIT 1"
                                values=[]
                                values.append(discordid)
                                discordusers=dbquery(query,values)
                                logmsg('debug','discordusers: '+str(discordusers))

                                # add discorduser if it does not exist
                                if discordusers['rowcount']==0:
                                    logmsg('debug','discordid not found in discordusers db')
                                    query="INSERT INTO discordusers (discordid) VALUES (%s)"
                                    values=[]
                                    values.append(discordid)
                                    dbquery(query,values)
                                    logmsg('info','created entry in discordusers db for discordid '+str(discordid))
                                else: logmsg('debug','discordid already exists in discordusers db')

                                # get discorduser id
                                query="SELECT id FROM discordusers WHERE discordid = %s LIMIT 1"
                                values=[]
                                values.append(discordid)
                                discordusers=dbquery(query,values)
                                discordusers_id=discordusers['rows'][0]['id']

                                # check if steamuser and discorduser are already registered
                                logmsg('debug','checking if entry in register db exists')
                                query="SELECT id FROM register WHERE steamusers_id = %s AND discordusers_id = %s LIMIT 1"
                                values=[]
                                values.append(steamusers_id)
                                values.append(discordusers_id)
                                register=dbquery(query,values)

                                # if discorduser is not registered with given steamuser, check if there is another steamid64
                                if register['rowcount']==0:
                                    logmsg('debug','checking if discorduser is known with another steamuser')
                                    query="SELECT id FROM register WHERE NOT steamusers_id = %s AND discordusers_id = %s LIMIT 1"
                                    values=[]
                                    values.append(steamusers_id)
                                    values.append(discordusers_id)
                                    register=dbquery(query,values)

                                    # if discorduser is not registered with a different steamid64, add new entry in register
                                    if register['rowcount']==0:
                                        logmsg('debug','not entry found in register db')
                                        query="INSERT INTO register (steamusers_id,discordusers_id) VALUES (%s,%s)"
                                        values=[]
                                        values.append(steamusers_id)
                                        values.append(discordusers_id)
                                        dbquery(query,values)
                                        logmsg('info','registered steamid64 '+str(steamid64)+' with discordid ('+str(discordid)+')')
                                        response='registered steamid64 ('+str(steamid64)+') with discordid ('+str(discordid)+')'
                                    else: # discorduser is registered with a different steamid64
                                        register_id=register['rows'][0]['id']
                                        logmsg('warn','entry found in register db discordusers_id ('+str(discordusers_id)+') with id ('+str(register_id)+'), but with a different steamid64')
                                        response='already registered discordusers_id ('+str(discordusers_id)+') as id ('+str(register_id)+'), but with a different steamid64'
                                else: # discorduser is already registered with given steamid64
                                    register_id=register['rows'][0]['id']
                                    logmsg('warn','entry found in register db for steamusers_id ('+str(steamusers_id)+') and discordusers_id ('+str(discordusers_id)+') with id ('+str(register_id)+')')
                                    response='already registered steamusers_id ('+str(steamusers_id)+') with discordusers_id ('+str(discordusers_id)+') as id ('+str(register_id)+')'
                            else: # missing parameters
                                logmsg('warn',command+' is missing parameter')
                                response=command+' is missing parameter'

                        case '!unregister':
                            if len(ums2)>1:
                                db_param=ums2[1]
                                steamid64=db_param
                                discordid=message.author.id
                                logmsg('debug','deleting entry in register for discorduser')

                                # get discorduser id
                                query="SELECT id FROM discordusers WHERE discordid=%s LIMIT 1"
                                values=[]
                                values.append(discordid)
                                discordusers=dbquery(query,values)

                                if discordusers['rowcount']==0: # actually delete
                                    discordusers_id=discordusers['rows'][0]['id']
                                    query="DELETE FROM register WHERE discordusers_id = %s LIMIT 1"
                                    values=[]
                                    values.append(discordusers_id)
                                    register=dbquery(query,values)
                                    logmsg('info','deleted entry in register for given discorduser: '+str(discordid)+')')
                                    response='deleted entry in register for given discorduser: '+str(discordid)+')'
                                else: # could not find discorduser with given discordid
                                    logmsg('warn','could not find discorduser in discordusers db')
                                    response='could not find discorduser in discordusers db'
                            else: # missing parameters
                                logmsg('warn',command+' is missing parameter')
                                response=command+' is missing parameter'

                        case '!getstats':
                            discordid=str(message.author.id)

                            # get id from discordusers db
                            query="SELECT id FROM discordusers WHERE discordid=%s LIMIT 1"
                            values=[]
                            values.append(discordid)
                            discordusers=dbquery(query,values)
                            if discordusers['rowcount']==0: # discorduser does not exist
                                logmsg('warn','discordid not registered')
                                response='discordid not registered'
                            else: # discorduser exists
                                discordusers_id=discordusers['rows'][0]['id']

                                # get id for steamuser from register db
                                query="SELECT steamusers_id FROM register WHERE discordusers_id=%s LIMIT 1"
                                values=[]
                                values.append(discordusers_id)
                                register=dbquery(query,values)
                                steamusers_id=register['rows'][0]['steamusers_id']

                                # get steamusers steamid64
                                query="SELECT steamid64 FROM steamusers WHERE id=%s LIMIT 1"
                                values=[]
                                values.append(steamusers_id)
                                steamusers=dbquery(query,values)
                                steamusers_steamid64=steamusers['rows'][0]['steamid64']

                                # get steamusers details
                                #query="SELECT ... FROM steamusers_details WHERE steamusers_id=%s LIMIT 1"
                                #values=[]
                                #values.append(steamusers_id)
                                #steamusers_details=dbquery(query,values)
                                #...

                                # get averages for steamuser from stats db
                                query="SELECT kills,deaths,assists,score,ping"
                                query+=",AVG(kills) as avg_kills,AVG(deaths) as avg_deaths,AVG(assists) as avg_assists,AVG(score) as avg_score,AVG(ping) as avg_ping"
                                query+=",MIN(kills) as min_kills,MIN(deaths) as min_deaths,MIN(assists) as min_assists,MIN(score) as min_score,MIN(ping) as min_ping"
                                query+=",MAX(kills) as max_kills,MAX(deaths) as max_deaths,MAX(assists) as max_assists,MAX(score) as max_score,MAX(ping) as max_ping"
                                query+=" FROM stats WHERE gamemode='SND' AND steamusers_id=%s "
                                query+="AND matchended IS TRUE AND playercount=10 "
                                query+="ORDER BY timestamp ASC"
                                values=[]
                                values.append(steamusers_id)
                                stats=dbquery(query,values)
                                logmsg('debug','stats: '+str(stats))

                                # get all entries for steamuser (for rowcount)
                                query="SELECT id FROM stats WHERE gamemode='SND' AND steamusers_id=%s "
                                query+="AND matchended IS TRUE AND playercount=10 "
                                query+="ORDER BY timestamp ASC"
                                values=[]
                                values.append(steamusers_id)
                                all_stats=dbquery(query,values)

                                limit_stats=3
                                if all_stats['rowcount']<limit_stats:
                                    # not enough stats
                                    logmsg('info','not enough data to generate stats ('+str(all_stats['rowcount'])+')')
                                    response='not enough data to generate stats ('+str(all_stats['rowcount'])+')'
                                else:
                                    parts=[
                                        user_message+': successful\n'
                                        '',
                                        'WIP',
                                        '',
                                        'Entries found for player '+str(steamusers_steamid64)+': '+str(all_stats['rowcount']),
                                        'AVG Score: '+str(stats['rows'][0]['avg_score']),
                                        'AVG Kills: '+str(stats['rows'][0]['avg_kills']),
                                        'AVG Deaths: '+str(stats['rows'][0]['avg_deaths']),
                                        'AVG Assists: '+str(stats['rows'][0]['avg_assists']),
                                        'AVG Ping: '+str(stats['rows'][0]['avg_ping'])
                                    ]
                                    response=''
                                    for part in parts: response=response+'\n'+part

                        case '!getrank':
                            discordid=str(message.author.id)

                            # get id from discordusers db
                            query="SELECT id FROM discordusers WHERE discordid=%s LIMIT 1"
                            values=[]
                            values.append(discordid)
                            discordusers=dbquery(query,values)
                            if discordusers['rowcount']==0:
                                # discorduser does not exist
                                logmsg('warn','discordid not registered')
                                response='discordid not registered'
                            else:
                                # discorduser exists
                                discordusers_id=discordusers['rows'][0]['id']

                                # get id for steamuser from register db
                                query="SELECT steamusers_id FROM register WHERE discordusers_id=%s LIMIT 1"
                                values=[]
                                values.append(discordusers_id)
                                register=dbquery(query,values)
                                steamusers_id=register['rows'][0]['steamusers_id']

                                # get rank for steamuser from ranks db
                                query="SELECT rank,title FROM ranks WHERE steamusers_id=%s LIMIT 1"
                                values=[]
                                values.append(steamusers_id)
                                ranks=dbquery(query,values)

                                if ranks['rowcount']==0:
                                    # no rank found
                                    logmsg('warn','no rank found')
                                    response='no rank found'
                                else:
                                    rank=ranks['rows'][0]['rank']
                                    title=ranks['rows'][0]['title']
                                    parts=[
                                        user_message+': successful\n'
                                        '',
                                        'WIP',
                                        '',
                                        'rank: '+str(rank),
                                        'title: '+str(title)]
                                    response=''
                                    for part in parts: response=response+'\n'+part

                        case '!genteams':
                            if len(ums2)>1:
                                match_msg_id=ums2[1]

                                guild=await client.fetch_guild(config['discord']['guild-id'])

                                #chnid=config['discord']['channel-ids']['g-matches']
                                chnid=config['discord']['channel-ids']['g-matches-test']

                                chn=await client.fetch_channel(chnid)
                                match_msg=await chn.fetch_message(match_msg_id)

                                # iterate over reactions
                                count=0
                                players=[]
                                for reaction in match_msg.reactions:

                                    # iterate over users of each reaction
                                    async for user in reaction.users():

                                        # iterate over ALL GUILD MEMBERS to find the one with the same name...
                                        async for member in guild.fetch_members(limit=None):
                                            if member==user:
                                                reaction_userid=member.id
                                                players.append(member.id)

                                    count=count+reaction.count

                                if count==10: # 10 players signed up
                                    default_rank=5.5
                                    players_ranked={}
                                    for player in players:
                                        # get id from discordusers db
                                        query="SELECT id FROM discordusers WHERE discordid=%s LIMIT 1"
                                        values=[]
                                        values.append(player)
                                        discordusers=dbquery(query,values)
                                        if discordusers['rowcount']==0: # discorduser does not exist
                                            players_ranked[player]=default_rank
                                        else: # discorduser exists
                                            discordusers_id=discordusers['rows'][0]['id']

                                            # get id for steamuser from register db
                                            query="SELECT steamusers_id FROM register WHERE discordusers_id=%s LIMIT 1"
                                            values=[]
                                            values.append(discordusers_id)
                                            register=dbquery(query,values)
                                            steamusers_id=register['rows'][0]['steamusers_id']

                                            # get rank for steamuser from ranks db
                                            query="SELECT rank,title FROM ranks WHERE steamusers_id=%s LIMIT 1"
                                            values=[]
                                            values.append(steamusers_id)
                                            ranks=dbquery(query,values)

                                            # assign default rank if none found
                                            if ranks['rowcount']==0: players_ranked[player]=default_rank
                                            else: players_ranked[player]=ranks['rows'][0]['rank']
                                    
                                    players_ranked_sorted=dict(sorted(players_ranked.items(),key=operator.itemgetter(1),reverse=True))
                                    logmsg('debug','players_ranked_sorted: '+str(players_ranked_sorted))

                                    # generate 2 teams
                                    team1=[]
                                    team2=[]
                                    number=0
                                    for player in players_ranked_sorted:
                                        match number:
                                            case 0: team1.append(player)
                                            case 1: team2.append(player)
                                            case 2: team1.append(player)
                                            case 3: team2.append(player)
                                            case 4: team2.append(player)
                                            case 5: team1.append(player)
                                            case 6: team2.append(player)
                                            case 7: team1.append(player)
                                            case 8: team2.append(player)
                                            case 9: team1.append(player)
                                        number+=1
                                    
                                    logmsg('debug','team1: '+str(team1))
                                    logmsg('debug','team2: '+str(team2))

                                    # generate response message
                                    part_team1="team 1: "
                                    for player in team1: part_team1+="<@"+str(player)+"> "
                                    part_team1+='  starting as T'

                                    part_team2="team 2: "
                                    for player in team2: part_team2+="<@"+str(player)+"> "
                                    part_team2+='  starting as CT'

                                    parts=[
                                            user_message+': successful\n'
                                            '',
                                            str(part_team1),
                                            str(part_team2)
                                    ]
                                    response=''
                                    for part in parts: response=response+'\n'+part

                                else: # not enough players
                                    logmsg('warn',command+' canceled because not enough players')
                                    response=command+' canceled because not enough players - need 10'

                            else: # missing parameters
                                logmsg('warn',command+' is missing parameters')
                                response=command+' is missing parameters'

                        case '!rcon':
                            ums=user_message.split(' ')
                            if len(ums)>2:
                                rconsrv=ums[1]
                                rconcommand=ums[2]
                                rconparams={}
                                i=0
                                j=0
                                for part in ums:
                                    if i>2:
                                        rconparams[str(j)]=part
                                        j+=1
                                    i+=1
                                data=await rcon(rconcommand,rconparams,rconsrv)
                                try:
                                    response=command+' response: '+str(data)
                                except Exception as e: logmsg('debug',str(e))
                            else: # missing parameters
                                logmsg('warn',command+' is missing parameter(s)')
                                response=command+' is missing parameter(s) - rtfm :P'
                                
                        case _ : log_this=False

                else: # wrong channel
                    logmsg('warn','command issuer didnt use the right channel')
                    response='please use the #e-bot-commands channel to issue commands'

            else: # access denied
                logmsg('warn','missing access rights for command: '+str(command))
                response='missing access rights for command: '+str(command)

        # log this command (if it was one...)
        if log_this is True:
            logmsg('info',str(command)+' called by '+str(message.author.name)+' ('+str(message.author.id)+')')
            await log_discord('[servus-publicus] '+str(command)+' called by '+str(message.author.name)+' ('+str(message.author.id)+')')

        # check if there is a response and if there is, send it
        if int(len(response))<1: logmsg('debug','nothing to do - response was found empty')
        else:
            logmsg('debug','response: '+str(response))
            try: await message.author.send(response) if is_private else await message.channel.send(response)
            except Exception as e: logmsg('debug',str(e))


    @client.event
    async def on_ready():
        logmsg('info',str(meta['name'])+' '+str(meta['version'])+' is now running')


    @client.event
    async def on_message(message):
        if message.author==client.user:
            logmsg('debug','message.author == client.user -> dont get high on your own supply')
            return
        username=str(message.author)
        user_message=str(message.content)
        channel=str(message.channel)
        channelid=str(message.channel.id)

        if len(user_message)>0 and user_message[0]=='?':
                user_message=user_message[1:]
                is_private=True
        else: is_private=False

        if channelid==config['discord']['bot-commands-channel']: is_bot_channel=True
        else: is_bot_channel=False

        await send_answer(client,message,user_message,is_private,is_bot_channel)


    client.run(config['discord']['bot_token'])
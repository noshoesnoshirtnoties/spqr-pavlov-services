import sys
import json
import time
import random
import asyncio
import datetime
import mysql.connector
from pathlib import Path
from pavlov import PavlovRCON
from datetime import datetime,timezone

if __name__ == '__main__':
    if str(sys.argv[1])!='': srv=str(sys.argv[1])
    else: srv='0'
    print('[DEBUG] srv: '+str(srv))

    rnd_sleep=random.randint(1,29)
    print('[DEBUG] gonna sleep for '+str(rnd_sleep)+' seconds to prevent all crons from running at the exact same time')
    time.sleep(rnd_sleep)

    config=json.loads(open('/opt/pavlov-server/praefectus/config.json').read())

    def dbquery(query,values):
        print('[DEBUG] dbquery called')
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
        print('[DEBUG] rcon called called')
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


    async def pinglimit():
        print('[DEBUG] pinglimit called')
        if config['rconplus'][srv] is True:
            serverinfo=await rcon('ServerInfo',{})
            try:
                if serverinfo['Successful'] is True:
                    si=serverinfo['ServerInfo']
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
                    serverinfo['ServerInfo']=si

                    roundstate=serverinfo['ServerInfo']['RoundState']
                    if roundstate=='Starting' or roundstate=='Started' or roundstate=='StandBy' or roundstate=='Ended':
                        inspectall=await rcon('InspectAll',{})
                        try:
                            for player in inspectall['InspectList']:
                                kda=player['KDA'].split('/',3)
                                kills=kda[0]
                                deaths=kda[1]
                                assists=kda[2]
                                score=player['Score']
                                steamid64=player['UniqueId']
                                current_ping=player['Ping']
                                notify_player=False
                                kick_player=False

                                # check if player is actually in the server
                                if int(kills)!=0 or int(deaths)!=0 or int(score)!=0:

                                    # add the current sample for the current player...
                                    if int(current_ping)!=0:
                                        print('[DEBUG] adding entry in pings db for player: '+str(steamid64))
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
                                        print('[DEBUG] rowcount ('+str(cnt_ping)+') >= minentries ('+str(config['pinglimit']['minentries'])+')')
                                        avg=int(avg_ping)
                                        delta=int(max_ping)-int(min_ping)
                                        limit_delta=int(config['pinglimit'][srv]['delta'])
                                        limit_soft=int(config['pinglimit'][srv]['soft'])
                                        limit_hard=int(config['pinglimit'][srv]['hard'])

                                        # check delta
                                        if delta>limit_delta:
                                            print('[WARN] ping delta ('+str(delta)+') exceeds delta limit ('+str(limit_delta)+') for player: '+str(steamid64))
                                            msg='ping delta warning :('
                                            notify_player=False
                                        else: print('[DEBUG] ping delta ('+str(delta)+') is within delta limit ('+str(limit_delta)+') for player: '+str(steamid64))

                                        # check avg ping against soft limit
                                        if avg>limit_soft:
                                            print('[WARN] ping avg ('+str(avg)+') exceeds soft limit ('+str(limit_soft)+') for player: '+str(steamid64))
                                            msg='ping exceeds soft limit ('+str(limit_soft)+') :('
                                            notify_player=True
                                        else: print('[DEBUG] ping avg ('+str(avg)+') is within soft limit ('+str(limit_soft)+') for player: '+str(steamid64))

                                        # check avg ping against hard limit
                                        if avg>limit_hard:
                                            print('[WARN] ping avg ('+str(avg)+') exceeds hard limit ('+str(limit_hard)+') for player: '+str(steamid64))
                                            msg='ping exceeds hard limit ('+str(limit_hard)+') :('
                                            notify_player=True
                                            if config['pinglimit'][srv]['kick'] is True:
                                                print('[WARN] player will be kicked: '+str(steamid64))
                                                msg+='\nauto-kick is enabled'
                                                kick_player=True
                                            else: print('[WARN] player ('+str(steamid64)+') would have been kicked by pinglimit, but kick is disabled')
                                        else: print('[DEBUG] ping avg ('+str(avg)+') is within hard limit ('+str(limit_hard)+') for player: '+str(steamid64))

                                        # notify
                                        if notify_player is True:
                                            await rcon('Notify',{'0':str(steamid64),'1':msg},True)
                                            print('[INFO] player '+steamid64+' has been notified by pinglimit')

                                        # kick
                                        if kick_player is True:
                                            await rcon('Kick',{'0':str(steamid64)})
                                            print('[WARN] player ('+str(steamid64)+') has been kicked by pinglimit')

                                        # delete accumulated entries, but keep some recent ones
                                        print('[DEBUG] deleting entries for player in pings db')
                                        query="DELETE FROM pings WHERE steamid64 = %s ORDER BY id ASC LIMIT %s"
                                        values=[]
                                        values.append(steamid64)
                                        values.append(cnt_ping - int(config['pinglimit']['keepentries']))
                                        dbquery(query,values)

                                    else: print('[DEBUG] canceled because there is not enough data on pings yet')
                                else: print('[DEBUG] canceled because player doesnt seem to be in the server yet')
                        except Exception as e:
                            print('[EXCEPTION]: '+str(e))
                            print('[EXCEPTION] inspectall: '+str(inspectall))
                    else: print('[WARN] canceled because of roundstate '+str(roundstate))
            except Exception as e:
                print('[EXCEPTION]: '+str(e))
                print('[EXCEPTION] serverinfo: '+str(serverinfo))
        else: logmsg('info','pinglimit canceled because rconplus is disabled')

    try:
        i=0
        while i<=config['pinglimit']['minentries']:
            asyncio.run(pinglimit())
            time.sleep(5)
            i+=1
    except Exception as e:
        print('[EXCEPTION]: '+str(e))
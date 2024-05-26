import sys
import json
import discord
from discord.ext import tasks, commands
import datetime
import time
import mysql.connector

if __name__ == '__main__':
    # read config
    config=json.loads(open('./config.json').read())

    # function: query mysqldb
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

    # init discord
    intents=discord.Intents.default()
    intents.message_content=True
    client=discord.Client(intents=intents)

    @client.event
    async def on_ready():
        channel=client.get_channel(int(config['discord']['channel-ids']['stats']))

        # delete old stats message
        async for message in channel.history(limit=10):
            messageid=message.id
            old_message=await channel.fetch_message(messageid)
            try: await old_message.delete()
            except Exception as e: print('[ERROR] '+str(e))

        servers_to_show=[
            "[EU][SPQR] TEST",
            "[EU][SPQR] Gladiator",
            "[EU][SPQR] SND 24/7",
            "[EU][SPQR] Poolday 24/7",
            "[EU][SPQR] BattleWar 24/7",
            "[EU][SPQR] Drachenschanze 24/7",
            "[EU][SPQR] Sigma Fury DM 24/7",
            "[EU][SPQR] Kennithhs Playground 24/7",
            "[EU][SPQR] Dust II DM 24/7",
            "[EU][SPQR] WW2 TDM 24/7"
        ]

        # get stats per server
        for server in servers_to_show:
            print('[DEBUG] server: '+str(server))

            query="SELECT steamusers_id"
            query+=",AVG(kills) as avg_kills,AVG(deaths) as avg_deaths,AVG(assists) as avg_assists,AVG(score) as avg_score,AVG(ping) as avg_ping"
            query+=",MIN(kills) as min_kills,MIN(deaths) as min_deaths,MIN(assists) as min_assists,MIN(score) as min_score,MIN(ping) as min_ping"
            query+=",MAX(kills) as max_kills,MAX(deaths) as max_deaths,MAX(assists) as max_assists,MAX(score) as max_score,MAX(ping) as max_ping"
            query+=" FROM stats"
            query+=" WHERE servername=%s"
            query+=" GROUP BY steamusers_id"
            query+=" ORDER BY avg_score DESC"
            stats1=dbquery(query,[server])
            print('[DEBUG] stats1: '+str(stats1))

            query="SELECT DISTINCT steamusers_id"
            query+=",AVG(kills) as avg_kills,AVG(deaths) as avg_deaths,AVG(assists) as avg_assists,AVG(score) as avg_score,AVG(ping) as avg_ping"
            query+=",MIN(kills) as min_kills,MIN(deaths) as min_deaths,MIN(assists) as min_assists,MIN(score) as min_score,MIN(ping) as min_ping"
            query+=",MAX(kills) as max_kills,MAX(deaths) as max_deaths,MAX(assists) as max_assists,MAX(score) as max_score,MAX(ping) as max_ping"
            query+=" FROM stats"
            query+=" WHERE servername=%s"
            query+=" ORDER BY avg_score DESC"
            stats2=dbquery(query,[server])
            print('[DEBUG] stats2: '+str(stats2))

            #if stats['rowcount']>0:
            #    stats_message=server+"\n"
            #    stats_message+="---------------------------------------------------------------------------------\n"
            #    i=1
            #    for stat in stats['rows']:
            #        print('[DEBUG] stat: '+str(stat))
            #        query="SELECT id,steamid64"
            #        query+=" FROM steamusers"
            #        query+=" WHERE id=%s"
            #        steamuser=dbquery(query,[player['steamusers_id']])

            #        print('[DEBUG] steamuser: '+str(steamuser))
            #        query="SELECT id,steamusers_id"
            #        query+=" FROM steamusers_details"
            #        query+=" WHERE steamusers_id=%s"
            #        steamusers_details=dbquery(query,[player['steamusers_id']])
            #        print('[DEBUG] steamusers_details: '+str(steamusers_details))

            #        if i<10: stats_message+=" "
            #        stats_message+="#"+str(i)+"  |  "
            #        stats_message+=str(steamuser['rows'][0]['steamid64'])+"  |  "
            #        stats_message+="{:.2f}".format(player['avg_score'])+" avg score  |  "
            #        stats_message+="{:.2f}".format(player['avg_kills'])+" avg kills  |  "
            #        stats_message+="{:.2f}".format(player['avg_deaths'])+" avg deaths\n"
            #        i+=1

            #    print("[INFO] stats_message:\n"+stats_message)

            #    # add new stats message in discord channel
            #    try: await channel.send(stats_message)
            #    except Exception as e: print('[ERROR] '+str(e))
            #else: print("[INFO] no stats for server: "+server)

        # close conn
        await client.close()

    client.run(config['discord']['bot_token'])

    exit()

import sys
import json
import discord
from discord.ext import tasks, commands
import datetime
import time
import mysql.connector

if __name__ == '__main__':
    # get params
    if str(sys.argv[1])!='': env=str(sys.argv[1])
    else: env='live'

    # read config
    config = json.loads(open('../config.json').read())[env]

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

    # get steamuserid from ranks (top 10)
    #query="SELECT steamusers_id,rank,title FROM ranks ORDER BY rank DESC LIMIT 10"
    #values=[]
    #ranks=dbquery(query,values)
    #for rank in ranks:
    #    print('[DEBUG]'+str(rank))
    #    #steamusers_id=

    #    # get stats from db for steamuserid
    #    query="SELECT kills,deaths,assists,score,ping"
    #    query+=",AVG(kills) as avg_kills,AVG(deaths) as avg_deaths,AVG(assists) as avg_assists,AVG(score) as avg_score,AVG(ping) as avg_ping"
    #    query+=",MIN(kills) as min_kills,MIN(deaths) as min_deaths,MIN(assists) as min_assists,MIN(score) as min_score,MIN(ping) as min_ping"
    #    query+=",MAX(kills) as max_kills,MAX(deaths) as max_deaths,MAX(assists) as max_assists,MAX(score) as max_score,MAX(ping) as max_ping"
    #    query+=" FROM stats WHERE gamemode='SND' AND steamusers_id=%s "
    #    query+="AND matchended IS TRUE AND playercount=10 "
    #    query+="ORDER BY timestamp ASC"
    #    values=[]
    #    values.append(steamusers_id)
    #    stats=dbquery(query,values)

    # generate stats message from stats data
    stats_message="WIP :construction_worker:"

    @client.event
    async def on_ready():
        channelid=int(config['bot-channel-ids']['stats'])
        channel=client.get_channel(channelid)

        # delete old stats message
        async for message in channel.history(limit=10):
            messageid=message.id
            old_message=await channel.fetch_message(messageid)
            try:
                await old_message.delete()
            except Exception as e:
                print('[ERROR] '+str(e))

        # add new stats message
        try:
            await channel.send(stats_message)
        except Exception as e:
            print('[ERROR] '+str(e))

        # close conn
        await client.close()

    client.run(config['bot_token'])

    exit()

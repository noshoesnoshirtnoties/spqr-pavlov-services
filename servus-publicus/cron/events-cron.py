import sys
import json
import discord
from discord.ext import tasks, commands
import datetime
import time

if __name__ == '__main__':
    # read config
    config=json.loads(open('./config.json').read())

    # create new events
    current=datetime.datetime.utcnow().replace(hour=0,minute=0,second=0,microsecond=0)
    unix=time.mktime(current.timetuple())

    # european summer time (begins at 01:00 UTC/WET (02:00 CET, 03:00 EET) on the last Sunday in March (25 ~ 31 March))
    #daylight_saving_adjustment=0

    # regular time (begins at 01:00 UTC (02:00 WEST, 03:00 CEST, 04:00 EEST) on the last Sunday in October (25 ~ 31 October))
    daylight_saving_adjustment=1*3600

    # this script expects to be run daily
    today_now=unix + (18 * 3600) + daylight_saving_adjustment
    one_full_day=1 * 86400
    announcement_time=2 * one_full_day
    event_time=int(today_now + announcement_time)

    event_message='<t:'+str(event_time)+':F>, <t:'+str(event_time)+':R>'

    # init discord
    intents=discord.Intents.default()
    intents.message_content=True
    client=discord.Client(intents=intents)

    @client.event
    async def on_ready():
        channel=client.get_channel(int(config['discord']['bot-channel-ids']['g-matches']))

        # delete old event msgs
        #async for message in channel.history(limit=10):
        #    messageid=message.id
        #    old_message=await channel.fetch_message(messageid)
        #    try: await old_message.delete()
        #    except Exception as e: print('[ERROR] '+str(e))

        # send event msg
        try: await channel.send(event_message)
        except Exception as e: print('[ERROR] '+str(e))

        # close conn
        await client.close()

    client.run(config['discord']['bot_token'])

    exit()

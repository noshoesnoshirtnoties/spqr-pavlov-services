import sys
import json
import discord
from discord.ext import tasks, commands
import datetime
import time

if __name__ == '__main__':
    # read config
    config = json.loads(open('/opt/pavlov-server/praefectus/config.json').read())

    # create new events
    current=datetime.datetime.utcnow().replace(hour=0,minute=0,second=0,microsecond=0)
    unix=time.mktime(current.timetuple())

    # european summer time (begins at 01:00 UTC/WET (02:00 CET, 03:00 EET) on the last Sunday in March (25 ~ 31 March))
    #daylight_saving_adjustment=0

    # regular time (begins at 01:00 UTC (02:00 WEST, 03:00 CEST, 04:00 EEST) on the last Sunday in October (25 ~ 31 October))
    daylight_saving_adjustment=1*3600

    # this script expects to be run sundays
    mon=unix + (1 * 86400) + (18 * 3600) + daylight_saving_adjustment
    tue=unix + (2 * 86400) + (19 * 3600) + daylight_saving_adjustment
    wed=unix + (3 * 86400) + (18 * 3600) + daylight_saving_adjustment
    thu=unix + (4 * 86400) + (19 * 3600) + daylight_saving_adjustment
    sat=unix + (6 * 86400) + (18 * 3600) + daylight_saving_adjustment

    new_events=[
        '<t:'+str(int(mon))+':F>, <t:'+str(int(mon))+':R>',
        '<t:'+str(int(tue))+':F>, <t:'+str(int(tue))+':R>',
        '<t:'+str(int(wed))+':F>, <t:'+str(int(wed))+':R>',
        '<t:'+str(int(thu))+':F>, <t:'+str(int(thu))+':R>',
        '<t:'+str(int(sat))+':F>, <t:'+str(int(sat))+':R>'
    ]

    # init discord
    intents=discord.Intents.default()
    intents.message_content=True
    client=discord.Client(intents=intents)

    @client.event
    async def on_ready():
        channelid=int(config['bot-channel-ids']['g-matches'])
        channel=client.get_channel(channelid)

        # delete old events in discord
        #async for message in channel.history(limit=10):
        #    messageid=message.id
        #    old_message=await channel.fetch_message(messageid)
        #    try: await old_message.delete()
        #    except Exception as e: print('[ERROR] '+str(e))

        # add new events in discord
        for new_event in new_events:
            try: await channel.send(new_event)
            except Exception as e: print('[ERROR] '+str(e))

        # close conn
        await client.close()

    client.run(config['bot_token'])

    exit()

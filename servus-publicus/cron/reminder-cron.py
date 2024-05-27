import sys
import json
import discord
import os
import random
from pathlib import Path

if __name__ == '__main__':
    # read config
    config=json.loads(open('./config.json').read())

    # init discord
    intents=discord.Intents.default()
    intents.message_content=True
    client=discord.Client(intents=intents)

    @client.event
    async def on_ready():
        #channel=client.get_channel(int(config['discord']['channel-ids']['news']))
        channel=client.get_channel(int(config['discord']['channel-ids']['e-bot-test']))

        gladiator=config['discord']['role-ids']['gladiator']
        tiro=config['discord']['role-ids']['tiro']
        gmatches=config['discord']['channel-ids']['g-matches']

        # get random quote 
        randomquote=random.choice(os.listdir('./txt/suntzu'))
        quotepath="./txt/suntzu/"+randomquote
        quote=Path(str(quotepath)).read_text()

        response='<@&'+str(gladiator)+'> <@&'+str(tiro)+'> **automated reminder**\n\n:crossed_swords:  come play <#'+str(gmatches)+'>\n\n'+quote+'\n-SunTzu'

        try:
            await channel.send(response)
        except Exception as e:
            print('[ERROR] '+str(e))
        await client.close()

    client.run(config['discord']['bot_token'])
    exit()

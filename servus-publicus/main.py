import json
import bot

if __name__ == '__main__':
    # read meta + config
    meta=json.loads(open('meta.json').read())
    config=json.loads(open('config.json').read())

    # run
    bot.run_bot(meta,config)
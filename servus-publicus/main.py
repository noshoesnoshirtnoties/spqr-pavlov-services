import json
import servuspublicus

if __name__ == '__main__':
    # read meta + config
    meta=json.loads(open('meta.json').read())
    config=json.loads(open('config.json').read())

    # run
    servuspublicus.run_servuspublicus(meta,config)
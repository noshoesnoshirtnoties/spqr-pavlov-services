import os
import sys
import json
import praefectus

if __name__ == '__main__':

    # get srv from env
    srv=os.environ['SRV']

    # read meta + config
    meta=json.loads(open('meta.json').read())
    config=json.loads(open('config.json').read())

    # run
    praefectus.run_praefectus(meta,config,srv)
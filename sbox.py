#!/usr/bin/env python2

import os
import yaml
import time
import logging
import argparse

from sboxify import sboxify
from service import service
from publish import publish

logging.basicConfig(level=logging.DEBUG)

parser = argparse.ArgumentParser(description='Spotify distributed jukebox')
parser.add_argument('--config', default="config.yaml", help='sbox config file (yaml)')
parser.add_argument('--spotify_user', default=None, help="spotify user")
parser.add_argument('--spotify_pass', default=None, help="spotify pass")
args = parser.parse_args()

class sbox:
    def __init__(self, args):
        self.config = sbox_config(args)
        self.sboxify = sboxify(self.config)
        self.service = service(self.config, self.sboxify)
        self.publish = publish(self.config)

    def start(self):
        self.sboxify.start()
        self.service.start()
        self.publish.start()

    def stop(self):
        self.publish.stop()
        self.service.stop()
        self.sboxify.stop()

class sbox_config(object):
    def __init__(self, args):
        self.args = vars(args)
        self.config = yaml.load(open(args.config))

    def __getattr__(self, key):
        if key in self.args and self.args[key]:
            return self.args[key]

        if key in self.config:
            return self.config[key]

        raise AttributeError(key)

    def __setattr__(self, key, value):
        if key in ("args", "config"):
            self.__dict__[key] = value
            return

        if key not in self.config:
            raise AttributeError(key)

        self.config[key] = value
        yaml.dump(self.config, open(self.args['config'], 'w'))

if __name__ == "__main__":
    s = sbox(args)
    s.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        s.stop()

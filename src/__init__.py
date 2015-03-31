#!/usr/bin/env python
#encoding: UTF-8

'''
网易云音乐 Entry
'''

import os
import locale
try:
    import ujson as json
except ImportError:
    import json
import atexit
from menu import Menu
from api import NetEase
from player import Player
from ui import Ui


APP_VER = 1000

class App(object):
    def __init__(self):
        self.home = os.path.expanduser("~") + '/.musicbox'
        if not os.path.isdir(self.home):
            os.mkdir(self.home)

        locale.setlocale(locale.LC_ALL, "")
        code = locale.getpreferredencoding()
        try:
            sfile = file(self.home + "/config.json",'r')
            data = json.loads(sfile.read())
            #version check
            assert('v' in data and data['v'] <= APP_VER)
            self.collection = data['collection']
            self.userid = data['account']['id']
            self.username = data['account']['nickname']
            self.netease = NetEase(cookie = data['account']['cookie'])
            sfile.close()
        except:
            self.collection = []
            self.userid = None
            self.username = None
            self.netease = NetEase()

        self.ui = Ui(self.netease)
        self.player = Player(self.ui)
        self.menu = Menu(self.netease, self.ui, self.player, [self.userid, self.username, self.update_profile])

    def update_profile(self, uid, uname):
        self.userid = uid
        self.username = uname

    def start(self):
        self.menu.start()

    def stop(self):
        sfile = file(self.home + "/config.json", 'w')
        data = {
            'v': APP_VER,
            'account': {
                'id': self.userid,
                'nickname': self.username,
                'cookie': self.netease.cookies
            },
            'collection': self.collection
        }
        sfile.write(json.dumps(data))
        sfile.close()


if __name__ == '__main__':
    app = App()
    atexit.register(app.stop)
    app.start()

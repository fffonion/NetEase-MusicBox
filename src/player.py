#!/usr/bin/env python
#encoding: UTF-8

'''
网易云音乐 Player
'''
# Let's make some noise

import subprocess
import threading
import random
import time
import os
import signal
from ui import Ui


# carousel x in [left, right]
carousel = lambda left, right, x: left if (x>right) else (right if x<left else x)


class Player:

    def __init__(self, ui_instance):
        self.ui = ui_instance
        self.datatype = 'songs'
        self.popen_handler = None
        # flag stop, prevent thread start
        self.playing_flag = False
        self.pause_flag = False
        self.playmode = 'list'
        self.songs = []
        self.idx = 0

    def popen_recall(self, onExit, popenArgs):
        """
        Runs the given args in a subprocess.Popen, and then calls the function
        onExit when the subprocess completes.
        onExit is a callable object, and popenArgs is a lists/tuple of args that
        would give to subprocess.Popen.
        """
        def runInThread(onExit, popenArgs):
            self.popen_handler = subprocess.Popen(['mpg123', popenArgs], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.popen_handler.wait()
            if self.playing_flag:
                self.pick_song()
                onExit()
            return
        thread = threading.Thread(target=runInThread, args=(onExit, popenArgs))
        thread.start()
        # returns immediately after the thread starts
        return thread

    def recall(self):
        self.playing_flag = True
        if self.datatype == 'radio' and len(self.songs) == 1:#no songs left, we only have 1 callback func
            _get_radio_song_func = self.songs[0]
            self.songs = _get_radio_song_func() + self.songs # this will generate [song1, song2, ..., _get_radio_song]
        item = self.songs[ self.idx ]
        self.ui.build_playinfo(item['song_name'], item['artist'], item['album_name'], self.playmode, meta = item['mp3_meta'])
        self.popen_recall(self.recall, item['mp3_url'])

    def play(self, datatype, datalist, idx):
        # if same playlists && idx --> same song :: pause/resume it
        if datatype == 'radio' and self.datatype != 'radio':#first entering radio; if not first, goto else
            #datalist = [_get_radio_song, _skip_radio_song] (2 func)
            self.songs = datalist
            self.datatype = datatype
            self.recall()
        elif datatype == 'songs' or datatype == 'djchannels':
            self.datatype = datatype
            if idx == self.idx and datalist == self.songs:
                if self.pause_flag:
                    self.resume()
                else:
                    self.pause()

            else:
                if datatype == 'songs' or datatype == 'djchannels':
                    self.songs = datalist
                    self.idx = idx

                # if it's playing
                if self.playing_flag:
                    self.switch()

                # start new play
                else:
                    self.recall()
        # if current menu is not song, pause/resume
        else:
            if self.playing_flag:
                if self.pause_flag:
                    self.resume()
                else:
                    self.pause()
            else:
                pass
        self.datatype = datatype
    # play another
    def switch(self):
        self.stop()
        # wait process be killed
        time.sleep(0.01)
        self.recall()

    def stop(self):
        if self.playing_flag and self.popen_handler:
            self.playing_flag = False
            self.popen_handler.kill()

    def pause(self):
        self.pause_flag = True
        os.kill(self.popen_handler.pid, signal.SIGSTOP)
        item = self.songs[ self.idx ]
        self.ui.build_playinfo(item['song_name'], item['artist'], item['album_name'], self.playmode, pause=True, meta = item['mp3_meta'])

    def resume(self):
        self.pause_flag = False
        os.kill(self.popen_handler.pid, signal.SIGCONT)
        item = self.songs[ self.idx ]
        self.ui.build_playinfo(item['song_name'], item['artist'], item['album_name'], self.playmode, meta = item['mp3_meta'])

    def next(self):
        self.stop()
        time.sleep(0.01)
        self.pick_song()
        self.recall()

    def prev(self):
        self.stop()
        time.sleep(0.01)
        self.pick_song(next=False)
        self.recall()

    def pick_song(self, next=True):
        if self.datatype == 'radio':
            if len(self.songs) > 1:# fail-safe
                s = self.songs.pop(0) # pop first one
        else:
            if self.playmode == 'list':
                self.idx = carousel(0, len(self.songs)-1, (self.idx+1) if next else (self.idx-1))
            elif self.playmode == 'single':
                pass
            elif self.playmode == 'random':
                self.idx = random.randint(0, len(self.songs)-1)

    def change_mode(self, playmode):
        if playmode in ['list', 'single', 'random']:
            self.playmode = playmode
            if self.songs:
                item = self.songs[ self.idx ]
                self.ui.build_playinfo(item['song_name'], item['artist'], item['album_name'], self.playmode, self.pause_flag, meta = item['mp3_meta'])


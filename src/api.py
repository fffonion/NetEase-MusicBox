#!/usr/bin/env python
#encoding: UTF-8

'''
网易云音乐 Api
'''

import re
try:
    import ujson as json
except ImportError:
    import json
import requests
from urllib import urlencode
from hashlib import md5


# list去重
def uniq(arr):
    arr2 = list(set(arr))
    arr2.sort(key=arr.index)
    return arr2

default_timeout = 10
base_url = 'http://music.163.com'

class NetEase:
    TOKEN_EXPIRED = 301
    # bigger then 10000 to avoid conflict with api code
    NO_ERROR = 10001
    APP_ERROR = 10002
    TOKEN_EXPIRED = 10003

    MUSIC_LEVEL_HIGH = 320
    MUSIC_LEVEL_MID = 160
    MUSIC_LEVEL_LOW = 96
    MUSIC_LEVEL_BASIC = 96

    def __init__(self, cookie = {}):
        self.header = {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip,deflate,sdch',
            'Accept-Language': 'zh-CN,zh;q=0.8,gl;q=0.6,zh-TW;q=0.4',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Host': 'music.163.com',
            'Referer': 'http://music.163.com/search/',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.152 Safari/537.36'
        }
        self.cookies = {
            'appver': '1.6.1.82809',
            'channel':'netease',
            'osver':'China-Operating-System-3.4.0-signed-keys-20150330eng',#乱打的啦
            'os':'cos'
        }
        self.cookies.update(cookie)
        self.batch_entered = False
        self.batch_stack = []
        self.token_refreshed = False
        self.music_level = NetEase.MUSIC_LEVEL_MID

    def enter_batch(self):
        if self.batch_entered:
            raise AttributeError("already in batch mode")
        self.batch_entered = True

    def commit_batch(self, method = 'POST'):
        data = map(lambda x:(x[0], json.dumps(x[1])), self.batch_stack)
        self.batch_entered = False
        self.batch_stack = []
        return self.httpRequest(
                method,
                '/batch',
                query = data,
                extra_header = {} if method == 'GET' else {'Origin':'orpheus://orpheus'}
        )

    def make_cookie(self):
        c = ';'.join(['='.join(x) for x in self.cookies.iteritems()])
        self.header.update({'Cookie':c})

    def httpRequest(self, method, action, query = '', timeout = None, extra_header = {}, json_resp = True):
        headers = dict(self.header)
        headers.update(extra_header)
        # if batch mode, not REALLY send request
        if self.batch_entered:
            self.batch_stack.append((action, query))
            return

        query = urlencode(query)

        if(method == 'GET'):
            url = base_url + ((action + '?' + query) if query else action)
            connection = requests.get(url, headers=headers, timeout=default_timeout)

        elif(method == 'POST'):
            connection = requests.post(
                base_url + action,
                data = query,
                headers = headers,
                timeout = default_timeout
        )
        h = connection.headers
        if 'set-cookie' in h:
            for line in h['set-cookie'].split(','):
                for c in line.split(';'):
                    _ = c.strip().split('=')
                    if len(_) < 2:
                        continue
                    k = _[0]
                    v = '='.join(_[1:])
                    if k.lower() not in ['expires', 'path', 'domain', 'max-age']:
                        self.cookies[k] = v
            self.make_cookie()

        connection.encoding = "UTF-8"
        if json_resp:
            data = json.loads(connection.text)
        else:
            data = connection.text
        return data

    def check_login(self, login_func):
        if 'MUSIC_U' not in self.cookies:#new user
            return login_func()
        elif not self.token_refreshed:
            return self.refresh_token(login_func)
        return NetEase.NO_ERROR

    # 登录 password = hashlib.md5( raw_password ).hexdigest()
    def login(self, username, password):
        action = '/api/login/'
        query = {
            'username': username,
            'password': password,
            'rememberLogin': 'true'
        }
        try:
            return self.httpRequest('POST', action, query)
        except:
            return {'code': NetEase.APP_ERROR}

    def refresh_token(self, login_func):
        action = '/api/login/token/refresh'
        query = {
            'cookieToken': self.cookies['MUSIC_U'],
        }
        try:
            ret = self.httpRequest('POST', action, query)
            if ret['code'] == 200:
                return NetEase.NO_ERROR
            else:
                #TODO token expired, call login_func
                if ret['code'] == NetEase.TOKEN_EXPIRED:
                    return login_func("登录态失效，")
                else:
                    return NetEase.NO_ERROR
        except:
            return 501

    # 用户歌单
    def user_playlist(self, uid, offset = 0, limit = 100):
        action = '/api/user/playlist/'
        query = {
            'offset': offset,
            'limit': limit,
            'uid': uid
        }
        try:
            data = self.httpRequest('GET', action, query)
            return data['playlist']
        except:
            return []

    # 搜索单曲(1)，歌手(100)，专辑(10)，歌单(1000)，用户(1002) *(type)*
    def search(self, s, stype=1, offset=0, total='true', limit=60):
        action = '/api/search/get/web'
        query = {
            's': s,
            'type': stype,
            'offset': offset,
            'total': total,
            'limit': 60
        }
        return self.httpRequest('POST', action, query)

    # 新碟上架 http://music.163.com/#/discover/album/
    def new_albums(self, offset=0, limit=50):
        action = '/api/album/new'
        query = {
            'area': 'ALL',
            'offset': offset,
            'total': 'true',
            'limit': limit
        }
        try:
            data = self.httpRequest('GET', action, query)
            return data['albums']
        except:
            return []

    # 歌单（网友精选碟） hot||new http://music.163.com/#/discover/playlist/
    def top_playlists(self, category='全部', order='hot', offset=0, limit=50):
        #TODO sort by cateogory
        action = '/api/playlist/list'
        query = {
            'cat': category,
            'order': order,
            'offset': offset,
            'total': ('true' if offset else 'false'),
            'limit': limit
        }
        try:
            data = self.httpRequest('GET', action, query)
            return data['playlists']
        except:
            return []

    # 歌单详情
    def playlist_detail(self, playlist_id):
        action = '/api/playlist/detail'
        query = {
            'id': playlist_id
        }
        try:
            data = self.httpRequest('GET', action, query)
            return data['result']['tracks']
        except:
            return []

    # 热门歌手 http://music.163.com/#/discover/artist/
    def top_artists(self, offset=0, limit=100):
        action = '/api/artist/top'
        query = {
            'offset': offset,
            'total': 'false',
            'limit': limit
        }
        try:
            data = self.httpRequest('GET', action, query)
            return data['artists']
        except:
            return []

    # 热门单曲 http://music.163.com/#/discover/toplist 50
    def top_songlist(self, offset=0, limit=100):
        action = '/discover/toplist'
        try:
            ret = self.httpRequest('GET', action, json_resp = False)
            songids = re.findall(r'/song\?id=(\d+)', ret)
            if songids == []:
                return []
            # 去重
            songids = uniq(songids)
            return self.songs_detail(songids)
        except:
            return []

    # 每日歌曲推荐
    def daily_recommend(self, cmd = "songs", offset = 0, limit = 20, **kwargs):
        #    cmd   |   args needed  |      args optional    
        # ---------|----------------|-----------------------
        #   songs  |      None      |   offset=0,limit=20
        #  dislike |     resId      | resType=4,alg=itembased
        args_dict = {
            'songs': {'offset': 0, 'total': 'true', 'limit': 20},
            'dislike': {'resId':None, 'resType':'4', 'alg':'itembased'},
        }
        action = '/api/discovery/recommend/songs'
        if cmd not in args_dict:
            raise NotImplementedError(" %s is not daily_recommend command" % cmd)

        query = args_dict[cmd]
        query.update(kwargs)
        if None in query.values():
            raise ValueError(" args for %s not satisfied" % cmd)
        try:
            ret = self.httpRequest('GET', action, query)
            return ret['recommend']
        except:
            return []

    # 歌手单曲
    def artists(self, artist_id):
        action = '/api/artist/' + str(artist_id)
        try:
            data = self.httpRequest('GET', action)
            return data['hotSongs']
        except:
            return []

    # album id --> song id set
    def album(self, album_id):
        action = 'http://music.163.com/api/album/' + str(album_id)
        try:
            data = self.httpRequest('GET', action)
            return data['album']['songs']
        except:
            return []

    # song ids --> song urls ( details )
    def songs_detail(self, ids, offset=0):
        tmpids = ids[offset:]
        tmpids = tmpids[0:100]
        tmpids = map(str, tmpids)
        action = '/api/song/detail'
        query = {
            "ids":'[' + (',').join(tmpids) + ']'
            #not passing raw list because str(list) generates comma with space
        }
        try:
            data = self.httpRequest('GET', action, query)
            return data['songs']
        except:
            return []

    # song id --> song url ( details )
    def song_detail(self, music_id):
        action = "/api/song/detail/"
        query = {
            "id": music_id,
            "ids": "[" + str(music_id) + "]"
        }
        try:
            data = self.httpRequest('GET', action, query)
            return data['songs']
        except:
            return []

    def radio(self, cmd = 'get', **kwargs):
        #    cmd   |   args needed  |      args optional    
        # ---------|----------------|-----------------------
        #    get   |       None     |          None         
        #    skip  |      songId    | time=0,  alg=itembased
        # trash/add|   songId, time |       alg=itembased   
        args_dict = {
            'get': {},
            'skip': {'alg':'itembased', 'songId':None, 'time':'0'},
            'trash/add': {'alg':'itembased', 'songId':None, 'time':None}
        }
        if cmd not in args_dict:
            raise NotImplementedError(" %s is not radio command" % cmd)

        query = args_dict[cmd]
        query.update(kwargs)
        if None in query.values():
            raise ValueError(" args for %s not satisfied" % cmd)

        action = '/api/radio/' + cmd
        try:
            data = self.httpRequest('GET', action, query)
            return data['data']
        except:
            return []

    #http://music.163.com/api/playlist/update/playcount?id=40299992
    #

    # 今日最热（0）, 本周最热（10），历史最热（20），最新节目（30）
    def djchannels(self, cmd = 'toplist', offset=0, limit=10):
        action = '/api/program/' + cmd
        query = {
            'offset': offset,
            'total': 'true',
            'limit': limit,
        }
        #try:
        ret = self.httpRequest('GET', action, query)
        chn = map(lambda x:self.dig_info(x['program']['mainSong'], 'channels'), ret['toplist'])
        return chn
        #except:
        #    return []

    # DJchannel ( id, channel_name ) ids --> song urls ( details )
    # 将 channels 整理为 songs 类型
    # def channel_detail(self, channelids, offset=0):
    #     channels = []
    #     for i in range(0, len(channelids)):
    #         action = '/api/dj/program/detail'
    #         query = {
    #             "id": channelids[i]
    #         }
    #         try:
    #             data = self.httpRequest('GET', action, query)
    #             channel = self.dig_info(ret['program']['mainSong'], 'channels' )
    #             channels.append(channel)
    #         except:
    #             continue

    #     return channels
    
    def _getBase64DigestString(self, s):
        salt = bytearray('3go8&$8*3*3h0k(2)2', 'iso_8859_1')
        s = bytearray(str(s), 'iso_8859_1')
        # if ( inp_len > 0 )
        # {
        # pos = 0;
        # do
        # {
        #   (*ptr_inp + pos) ^= (*ptr_salt + pos % salt_len);
        #   ++pos;
        # }
        # while ( pos != inp_len );
        # }
        salt_len = len(salt)
        for i in range(len(s)):
            s[i] ^= salt[i % salt_len]
        return md5(s).digest().encode('base64').rstrip('\n').replace('/', '_').replace('+', '-')

    def _get_music_info(self, data, lvl = None):
        meta = {
            'duration': data['duration'],
            'bitrate': 96000,
            'sr': 44100,
            'ext': 'mp3'
        }
        lvl = lvl or self.music_level          
        key_map = {
            NetEase.MUSIC_LEVEL_HIGH: 'hMusic',
            NetEase.MUSIC_LEVEL_MID: 'mMusic',
            NetEase.MUSIC_LEVEL_LOW: 'lMusic',
            NetEase.MUSIC_LEVEL_BASIC: 'bMusic',
            None:'audition'
        }
        key = key_map[lvl]
        if key in data and data[key]:#not None
            dfsid = data[key]['dfsId']
            meta.update({
                    'bitrate': data[key]['bitrate'],
                    'sr': data[key]['sr'],
                    'ext': data[key]['extension']
                })
            return 'http://m1.music.126.net/%s/%s.mp3' % (
                    self._getBase64DigestString(dfsid), dfsid
                ), meta
        else:
            return data['mp3Url'], meta

    def dig_info(self, data ,dig_type):
        temp = []
        if dig_type == 'songs' or dig_type == 'radio':
            for i in range(0, len(data) ):
                url, meta = self._get_music_info(data[i])
                song_info = {
                    'song_id': data[i]['id'],
                    'artist': [],
                    'song_name': data[i]['name'],
                    'album_name': data[i]['album']['name'],
                    'mp3_url': url,
                    'mp3_meta': meta,
                }
                if 'artist' in data[i]:
                    song_info['artist'] = data[i]['artist']
                elif 'artists' in data[i]:
                    for j in range(0, len(data[i]['artists']) ):
                        song_info['artist'].append( data[i]['artists'][j]['name'] )
                    song_info['artist'] = ', '.join( song_info['artist'] )
                else:
                    song_info['artist'] = '未知艺术家'

                temp.append(song_info)

        elif dig_type == 'artists':
            temp = []
            for i in range(0, len(data) ):
                artists_info = {
                    'artist_id': data[i]['id'],
                    'artists_name': data[i]['name'],
                    'alias': ''.join(data[i]['alias'])
                }
                temp.append(artists_info)

            return temp

        elif dig_type == 'albums':
            for i in range(0, len(data) ):
                albums_info = {
                    'album_id': data[i]['id'],
                    'albums_name': data[i]['name'],
                    'artists_name': data[i]['artist']['name']
                }
                temp.append(albums_info)

        elif dig_type == 'playlists':
            for i in range(0, len(data) ):
                playlists_info = {
                    'playlist_id': data[i]['id'],
                    'playlists_name': data[i]['name'],
                    'creator_name': data[i]['creator']['nickname']
                }
                temp.append(playlists_info)


        elif dig_type == 'channels':
            url, meta = self._get_music_info(data[i])
            channel_info = {
                'song_id': data['id'],
                'song_name': data['name'],
                'artist': data['artists'][0]['name'],
                'album_name': 'DJ节目',
                'mp3_url': url,
                'mp3_meta': meta
                }
            temp = channel_info

        return temp


# Licensed under the Apache License, Version 2.0

import urllib,urllib2,urlparse,base64
import xbmcplugin,xbmcaddon,xbmcgui,sys,xbmc
import simplejson as json

base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
args = urlparse.parse_qs(sys.argv[2][1:])

xbmcplugin.setContent(addon_handle, 'movies')

addon = xbmcaddon.Addon()
vres = addon.getSetting('video_res')
if vres not in ['0','1','2','3','4']: vres = '0'
video_res = [1080,720,480,360,240][int(vres)]
subtitles = addon.getSetting('subtitles')
startupmsg = addon.getSetting('startupmsg')
language = addon.getSetting('language')
if len('' + language) < 1: language = 'E'
__language__ = addon.getLocalizedString

def build_url(query):
    return base_url + '?' + urllib.urlencode(query)

def get_json(url):
    data = urllib2.urlopen(url).read().decode('utf-8')
    return json.loads(data)

def b64_encode_object(obj):
    js = json.dumps(obj)
    b64 = base64.b64encode(js)
    return b64

def b64_decode_object(str):
    js = base64.b64decode(str)
    obj = json.loads(js)
    return obj

def time_str_to_sec(s):
    dur = s.split(':')
    if len(dur) == 3:
        return int(dur[0]) * 60 * 60 + int(dur[1]) * 60 + int(dur[2])
    elif len(dur) == 2:
        return int(dur[0]) * 60 + int(dur[1])
    elif len(dur) == 1:
        return int(dur[0])

def build_folders(subcat_ary):
    isStreaming = mode[0] == 'Streaming'
    for s in subcat_ary:
        url = build_url({'mode': s.get('key')})
        li = xbmcgui.ListItem(s.get('name'))
        if 'rph' in s['images']:
            li.setArt({'thumb': s['images']['rph'].get('md'), 'icon': s['images']['rph'].get('md')})
        if 'pnr' in s['images']:
            li.setArt({'fanart': s['images']['pnr'].get('md')})
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=(isStreaming == False))

def ask_hidden(file_data):
    d = xbmcgui.Dialog()
    if d.yesno(__language__(30013), __language__(30014)):
        data = b64_decode_object(file_data)
        li = build_basic_listitem(data)
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=data['video'], listitem=li)
        xbmcplugin.endOfDirectory(addon_handle)

def get_video_metadata(file_ary, exclude_hidden=False):
    videoFiles = []
    for r in file_ary:
        video = get_best_video(r['files'])
        if video is None: continue

        sqr_img = ''
        wide_img = ''
        if 'sqr' in r['images']: sqr_img = r['images']['sqr'].get('md')
        elif 'cvr' in r['images']: sqr_img = r['images']['cvr'].get('md')
        if 'pnr' in r['images']: wide_img = r['images']['pnr'].get('md')

        if r.get('type') == 'audio': media_type = 'music'
        else: media_type = 'video'

        video_file = {'id': r['guid'], 'video': video['progressiveDownloadURL'], 'wide_img': wide_img,
                      'sqr_img': sqr_img, 'title': r.get('title'), 'dur': r.get('duration'), 'type': media_type}

        if 'WebExclude' in r['tags']:
            if exclude_hidden: continue
            file_data = b64_encode_object(video_file)
            video_file = {'id': None, 'video': build_url({'mode': 'ask_hidden', 'file_data': file_data}), 'wide_img': None,
                  'sqr_img': None, 'title': __language__(30013), 'dur': None}

        videoFiles.append(video_file)
    return videoFiles

def get_best_video(file_ary):
    videos = []
    for x in file_ary:
        try:
            if int(x['label'][:-1]) > video_res: continue
        except (ValueError, TypeError):
            if int(x['frameHeight']) > video_res: continue
        videos.append(x)
    videos = sorted(videos, reverse=True)
    if subtitles == 'false': videos = [x for x in videos if x['subtitled'] == False]
    if len(videos) == 0: return None
    return videos[0]

def build_basic_listitem(file_data):
    li = xbmcgui.ListItem(file_data['title'])
    li.setArt({'icon': file_data['wide_img'], 'thumb': file_data['sqr_img'], 'fanart': file_data['wide_img']})
    li.addStreamInfo(file_data['type'], {'duration':file_data['dur']})
    return li

def build_media_entries(file_ary):
    for v in get_video_metadata(file_ary):
        li = build_basic_listitem(v)
        
        if v['id'] is None:
            xbmcplugin.addDirectoryItem(handle=addon_handle, url=v['video'], listitem=li, isFolder=True)    
        else:
            bingeAction = 'XBMC.RunPlugin(' + build_url({'mode':'watch_from_here','from_mode':mode[0],'first':v['id']}) + ')'

            file_data = b64_encode_object(v)
            addToPlaylistAction = 'XBMC.RunPlugin(' + build_url({'mode':'add_to_playlist','file_data':file_data}) +')'

            li.addContextMenuItems([(__language__(30010), bingeAction),(__language__(30011), addToPlaylistAction)], replaceItems=True)
            xbmcplugin.addDirectoryItem(handle=addon_handle, url=v['video'], listitem=li)

def process_top_level():
    if startupmsg == 'true':
        d = xbmcgui.Dialog()
        if d.yesno(__language__(30016), __language__(30017), nolabel=__language__(30018), yeslabel=__language__(30019)):
            d.textviewer(__language__(30016), __language__(30020))

    url = 'https://data.jw-api.org/mediator/v1/categories/' + language + '?'
    cats_raw = urllib2.urlopen(url).read().decode('utf-8')
    categories = json.loads(cats_raw)

    for c in categories['categories']:
        if 'WebExclude' not in c.get('tags', []):
            url = build_url({'mode': c.get('key')})
            li = xbmcgui.ListItem(c.get('name'))
            xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=True)

    url = build_url({'mode': 'search'})
    li = xbmcgui.ListItem(__language__(30022))
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=True)

    url = build_url({'mode': 'languages'})
    li = xbmcgui.ListItem(__language__(30005))
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=True)

    xbmcplugin.endOfDirectory(addon_handle)

def build_playlist(file_ary, first):
    added = 0
    current = float(0)
    foundStartEp = False

    metadata = get_video_metadata(file_ary, exclude_hidden=True)
    total = float(len(metadata))

    dl = xbmcgui.DialogProgress()
    dl.create(__language__(30006), __language__(30007))

    pl = xbmc.PlayList(1)
    pl.clear()

    for item in reversed(metadata):
        dl.update(int(current / total * 100))
        if item['id'] == first: foundStartEp = True
        if foundStartEp == True:
            added += 1
            li = xbmcgui.ListItem(item['title'])
            li.setArt({'thumb': item['sqr_img'], 'icon': item['sqr_img']})
            pl.add(item['video'], li)
        current += 1.0
    dl.close()

    if added > 0:
        xbmc.Player().play(pl)
    else:
        xbmcgui.Dialog().ok(__language__(30008), __language__(30009))
    return pl

def process_sub_level(sub_level, create_playlist, from_id):
    info = get_json('https://data.jw-api.org/mediator/v1/categories/' + language + '/' + sub_level + '?&detailed=1')
    if create_playlist == False:
        if 'subcategories' in info['category']: build_folders(info['category']['subcategories'])
        if 'media' in info['category']: build_media_entries(info['category']['media'])
        xbmcplugin.endOfDirectory(addon_handle)
    else:
        pl = build_playlist(info['category']['media'], from_id)
        xbmc.Player().play(pl)

def process_streaming():
    info = get_json('https://data.jw-api.org/mediator/v1/schedules/' + language + '/Streaming')
    for s in info['category']['subcategories']:
        if s['key'] == mode[0]:
            pl = xbmc.PlayList(1)
            pl.clear()
            for item in get_video_metadata(s['media']):
                li = xbmcgui.ListItem(item['title'])
                li.setArt({'icon': item['sqr_img'], 'thumb': item['sqr_img']})
                pl.add(item['video'], li)
            xbmc.Player().play(pl)
            xbmc.Player().seekTime(s['position']['time'])
            return

def get_languages():
    info = get_json('http://data.jw-api.org/mediator/v1/languages/' + language + '/web')
    for l in info['languages']:
        url = build_url({'mode': 'set_language', 'language': l['code']})
        li = xbmcgui.ListItem(l['vernacular'] + ' / ' + l['name'])
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=False)
    xbmcplugin.endOfDirectory(addon_handle)

def set_language(language):
    language = language
    addon.setSetting('language', language)
    xbmc.executebuiltin('Action(ParentDir)')

def add_to_playlist(file_data):
    data = b64_decode_object(file_data)

    pl = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    li = build_basic_listitem(data)

    pl.add(url=data['video'], listitem=li)

def search_dialog():
    kb = xbmc.Keyboard("", __language__(30022))
    kb.doModal()
    if kb.isConfirmed():
        search_string = kb.getText()
        url = 'https://data.jw-api.org/search/query?'
        query = urllib.urlencode({'q': search_string, 'lang': language, 'limit': 24})
        headers = {'Authorization': 'Bearer ' + get_jwt_token()}
        try:
            info = get_json(urllib2.Request(url + query, headers=headers))
        except urllib2.HTTPError as e:
            if e.code == 401:
                headers = {'Authorization': 'Bearer ' + get_jwt_token(True)}
                info = get_json(urllib2.Request(url + query, headers=headers))
            else:
                raise
        if 'hits' in info: build_search_entries(info['hits'])
        xbmcplugin.endOfDirectory(addon_handle)

def get_jwt_token(update=False):
    token = addon.getSetting('jwt_token')
    if not token or update is True:
        url = 'https://tv.jw.org/tokens/web.jwt'
        token = urllib2.urlopen(url).read().decode('utf-8')
        if token != '':
            addon.setSetting('jwt_token', token)
    return token

def build_search_entries(result_ary):
    for r in result_ary:
        if 'WebExclude' in r.get('tags'):
            continue

        li = xbmcgui.ListItem(r['displayTitle'])
        li.setProperty("isPlayable", "true")

        if 'type:audio' in r.get('tags'):
            media_type = 'music'
        else:
            media_type = 'video'

        dur = 0
        for m in r.get('metadata'):
            if m['key'] == 'duration':
                print m['value']
                dur = time_str_to_sec(m['value'])
                print dur
                break
        li.setInfo(media_type, {'duration': dur})

        for i in r.get('images'):
            if i.get('size') == 'md' and i.get('type') == 'sqr':
                li.setArt({'thumb': i.get('url')})
            if i.get('size') == 'md' and i.get('type') == 'pnr':
                li.setArt({'icon': i.get('url'), 'fanart': i.get('url')})

        url = build_url({'mode': 'play', 'key': r['languageAgnosticNaturalKey']})
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=False)

def play_search_result(video_key):
    info = get_json('https://data.jw-api.org/mediator/v1/media-items/' + language + '/' + video_key)
    video = get_best_video(info['media'][0]['files'])
    if video:
        li = xbmcgui.ListItem(info['media'][0]['title'])
        li.setPath(video['progressiveDownloadURL'])
        xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, li)


mode = args.get('mode', None)

if mode is None: process_top_level()
elif mode[0] == 'languages': get_languages()
elif mode[0] == 'set_language': set_language(args.get('language')[0])
elif mode[0] == 'watch_from_here': process_sub_level(args.get('from_mode')[0], True, args.get('first')[0])
elif mode[0] == 'add_to_playlist': add_to_playlist(args.get('file_data')[0])
elif mode[0] == 'ask_hidden': ask_hidden(args.get('file_data')[0])
elif mode[0] == 'search': search_dialog()
elif mode[0] == 'play': play_search_result(args.get('key')[0])
elif (mode[0].startswith('Streaming') and len(mode[0]) > 9): process_streaming()
else: process_sub_level(mode[0], False, 0)

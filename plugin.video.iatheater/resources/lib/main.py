"""
    Internet Archive Kodi Addon
    Copyright (C) 2024 gujal
    Copyright (c) 2026 PythonTrousers (Architecture and Modifications)
    
    First modified by PythonTrousers on 2026-06-14: Extensive architectural restructuring, 
    logic rewrites, and AI-assisted capability expansions.
    
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import json
import re
import sys
import threading
import random
import urllib.parse
import urllib.request
import math
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmcvfs
from html import unescape
from resources.lib import client, cache

_addon = xbmcaddon.Addon()
_addonID = _addon.getAddonInfo('id')
_plugin = _addon.getAddonInfo('name')
_version = _addon.getAddonInfo('version')
_icon = _addon.getAddonInfo('icon')
_fanart = _addon.getAddonInfo('fanart')
_language = _addon.getLocalizedString
_settings = _addon.getSetting
_addonpath = f'special://profile/addon_data/{_addonID}/'

# Safely parse Kodi version using the official API
try:
    _version_str = xbmc.getInfoLabel('System.BuildVersion')
    _kodiver = float(re.search(r'^(\d+\.\d+)', _version_str).group(1))
except Exception:
    _kodiver = 19.0

# DEBUG
DEBUG = _settings("DebugMode") == "true"

if not xbmcvfs.exists(_addonpath):
    xbmcvfs.mkdir(_addonpath)

cache_duration = int(_settings('timeout'))

if not xbmcvfs.exists(_addonpath + 'settings.xml'):
    _addon.openSettings()


class Main(object):
    def __init__(self):
        self.base_url = 'https://archive.org/'
        self.search_url = f'{self.base_url}services/search/beta/page_production/'
        self.img_path = f'{self.base_url}services/img/'
        self.headers = {'Referer': self.base_url}
        
        # Cache parameters once on initialization
        self.args = urllib.parse.parse_qs(urllib.parse.urlparse(sys.argv[2]).query)
        
        # Pre-compile regex patterns for performance
        self.re_s_e = re.compile(r's\s*(\d+)[._ -]*e\s*(\d+)')
        self.re_x = re.compile(r'(\d+)\s*x\s*(\d+)')
        self.re_ep = re.compile(r'(?:ep|episode)[._ -]*(\d+)')
        self.re_track = re.compile(r'^(?:track\s*)?(\d{1,3})[\s._-]')
        
        # Revert to standard lists for reliable substring matching
        self.video_exts = ('.mp4', '.mkv', '.avi', '.mov', '.m4v', '.vob', '.iso', '.wmv', '.mpg', '.mpeg', '.flv', '.m2ts', '.ts', '.webm', '.ogv')
        self.audio_exts = ('.mp3', '.flac', '.ogg', '.m4a', '.wav', '.opus', '.aac', '.wma', '.aiff', '.aif', '.shn', '.m4b', '.ape', '.wv')
        self.video_markers = ['mp4', 'mkv', 'avi', 'mov', 'm4v', 'h.264', 'h264', 'mpeg', 'matroska', 'vp8', 'vp9', 'webm', 'vob', 'iso', 'wmv', 'mpg', 'flv', 'm2ts', 'ts', 'ogv']
        self.audio_markers = ['mp3', 'flac', 'ogg', 'm4a', 'wav', 'vorbis', 'audio', 'opus', 'aac', 'wma', 'aiff', 'aif', 'shn', 'm4b', 'ape', 'wv']

        # Prioritize URL parameters over asynchronous settings read to prevent race conditions
        content_type = self.parameters('content_type') or _settings('context')
        if content_type and _settings('context') != content_type:
            _addon.setSetting('context', content_type)
            
        action = self.parameters('action')
        
        if action == 'list_items':
            page = int(self.parameters('page') or 1)
            target = self.parameters('target')
            self.list_items(target, page, content_type)
        elif action == 'list_collections':
            page = int(self.parameters('page') or 1)
            self.list_collections(page, content_type)
        elif action == 'expand_item':
            item_id = self.parameters('target')
            self.expand_item(item_id, content_type)
        elif action == 'play_video':
            item_id = self.parameters('target')
            self.play_video(item_id, content_type)
        elif action == 'search':
            self.search(content_type)
        elif action == 'search_word':
            keyword = urllib.parse.unquote(self.parameters('keyword'))
            page = int(self.parameters('page') or 1)
            self.search_word(keyword, page, content_type)
        elif action == 'search_history':
            self.list_history()
        elif action == 'clear_history':
            if xbmcgui.Dialog().yesno(_plugin, "Are you sure you want to clear your entire search history?"):
                self._clear_history()
                xbmc.executebuiltin("Container.Refresh")
        elif action == 'continue_watching':
            self.list_resume()
        elif action == 'clear_all_resumes':
            if xbmcgui.Dialog().yesno(_plugin, "Are you sure you want to clear your Continue Watching list?"):
                self._clear_all_resumes()
                xbmc.executebuiltin("Container.Refresh")
        elif action == 'remove_resume':
            if xbmcgui.Dialog().yesno(_plugin, "Remove this item from your Continue Watching list?"):
                self._remove_resume(self.parameters('target'), self.parameters('ep_tag'))
                xbmc.executebuiltin("Container.Refresh")
        elif action == 'clear':
            if xbmcgui.Dialog().yesno(_plugin, "Are you sure you want to clear the addon cache?"):
                self.clear_cache()
        else:
            if action == '':
                self.show_splash_screen()
            self.main_menu(content_type)

    def main_menu(self, content_type):
        if DEBUG:
            self.log(f'main_menu({content_type})')
            
        category = [
            {'title': 'Continue Watching', 'key': 'continue'},
            {'title': 'Popular Collections', 'key': 'popular'},
            {'title': 'Search Movies', 'key': 'search_movie'},
            {'title': 'Search TV Shows', 'key': 'search_tv'},
            {'title': 'Search All Videos', 'key': 'search_general'},
            {'title': 'Search Audio & Music', 'key': 'search_audio'},
            {'title': 'Search History', 'key': 'history'},
            {'title': 'Clear Cache', 'key': 'cache'}
        ]
        
        for i in category:
            listitem = xbmcgui.ListItem(i['title'])
            listitem.setArt({'thumb': _icon, 'fanart': _fanart, 'icon': _icon})

            is_folder = True
            if i['key'] == 'cache':
                url = f"{sys.argv[0]}?action=clear"
                is_folder = False
            elif i['key'].startswith('search_'):
                is_folder = False
            
            if i['key'] == 'search_movie':
                url = f"{sys.argv[0]}?action=search&content_type=video&search_type=movie"
            elif i['key'] == 'search_tv':
                url = f"{sys.argv[0]}?action=search&content_type=video&search_type=tv"
            elif i['key'] == 'search_general':
                url = f"{sys.argv[0]}?action=search&content_type=video&search_type=video"
            elif i['key'] == 'search_audio':
                url = f"{sys.argv[0]}?action=search&content_type=audio&search_type=audio"
            elif i['key'] == 'history':
                url = f"{sys.argv[0]}?action=search_history"
                is_folder = True  # History renders a directory list
            elif i['key'] == 'continue':
                url = f"{sys.argv[0]}?action=continue_watching"
            elif i['key'] == 'popular':
                url = f"{sys.argv[0]}?action=list_collections&page=1&content_type=video"

            xbmcplugin.addDirectoryItems(int(sys.argv[1]), [(url, listitem, is_folder)])

        xbmcplugin.addSortMethod(handle=int(sys.argv[1]), sortMethod=xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.setContent(int(sys.argv[1]), 'addons')
        xbmcplugin.endOfDirectory(int(sys.argv[1]), True)

    def show_splash_screen(self):
        if DEBUG:
            self.log('show_splash_screen()')
        
        try:
            # WindowDialog overlays the screen without needing XML skin files
            dialog = xbmcgui.WindowDialog()
            
            # Standard Kodi coordinate system base is 1280x720. 
            # Passing _fanart directly utilizes your existing fanart.jpg
            splash_image = xbmcgui.ControlImage(0, 0, 1280, 720, _fanart)
            dialog.addControl(splash_image)
            
            dialog.show()
            
            # Pause the main thread briefly so the user actually sees the splash screen
            xbmc.sleep(1500) 
            
        except Exception as e:
            self.log(f"Splash screen error: {str(e)}")
        finally:
            dialog.close()

    # --- LOCAL DATA MANAGEMENT ---

    def _safe_int(self, val):
        """Safely parse integers protecting against empty strings from the API"""
        try:
            return int(val)
        except (ValueError, TypeError):
            return 0

    def _get_history(self):
        hist_file = xbmcvfs.translatePath(f"{_addonpath}search_history.json")
        if xbmcvfs.exists(hist_file):
            try:
                with open(hist_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e: 
                self.log(f'Failed to parse search history: {str(e)}')
                return []
        return []

    def _save_history(self, keyword, content_type, search_type='video'):
        hist = self._get_history()
        
        hist = [entry for entry in hist if not (entry.get('keyword', '').lower() == keyword.lower() and entry.get('search_type', 'video') == search_type)]
        
        entry = {'keyword': keyword, 'content_type': content_type, 'search_type': search_type}
        hist.insert(0, entry)
        hist = hist[:20] 
        
        hist_file = xbmcvfs.translatePath(f"{_addonpath}search_history.json")
        with open(hist_file, 'w', encoding='utf-8') as f:
            json.dump(hist, f)

    def _clear_history(self):
        hist_file = xbmcvfs.translatePath(f"{_addonpath}search_history.json")
        with open(hist_file, 'w', encoding='utf-8') as f:
            json.dump([], f)

    def _get_resume(self):
        res_file = xbmcvfs.translatePath(f"{_addonpath}resume_data.json")
        if xbmcvfs.exists(res_file):
            try:
                with open(res_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e: 
                self.log(f'Failed to parse resume data: {str(e)}')
                return {}
        return {}

    def _save_resume(self, item_id, ep_tag, title, content_type, time_pos):
        res = self._get_resume()
        key = f"{item_id}_{ep_tag}"
        res[key] = {
            'item_id': item_id,
            'ep_tag': ep_tag,
            'title': title,
            'content_type': content_type,
            'time': time_pos
        }
        res_file = xbmcvfs.translatePath(f"{_addonpath}resume_data.json")
        with open(res_file, 'w', encoding='utf-8') as f:
            json.dump(res, f)

    def _remove_resume(self, item_id, ep_tag):
        res = self._get_resume()
        key = f"{item_id}_{ep_tag}"
        if key in res:
            del res[key]
            res_file = xbmcvfs.translatePath(f"{_addonpath}resume_data.json")
            with open(res_file, 'w', encoding='utf-8') as f:
                json.dump(res, f)

    def _clear_all_resumes(self):
        res_file = xbmcvfs.translatePath(f"{_addonpath}resume_data.json")
        with open(res_file, 'w', encoding='utf-8') as f:
            json.dump({}, f)

    def _has_playable_media(self, fields, content_type):
        formats = fields.get('format', [])
        if not formats:
            return True 
            
        if isinstance(formats, str):
            formats = [formats]
            
        formats_str = " ".join(str(f).lower() for f in formats)
        
        if content_type == 'video':
            return any(marker in formats_str for marker in self.video_markers)
        else:
            return any(marker in formats_str for marker in self.audio_markers)

    def _parse_duration_to_minutes(self, duration_data):
        if not duration_data:
            return None
        try:
            if isinstance(duration_data, list):
                duration_data = duration_data[0]
                
            d_str = str(duration_data).strip()
            
            if d_str.replace('.', '', 1).isdigit():
                return float(d_str) / 60.0
                
            parts = d_str.split(':')
            if len(parts) == 3:
                return int(parts[0]) * 60 + int(parts[1]) + float(parts[2]) / 60.0
            elif len(parts) == 2:
                return int(parts[0]) + float(parts[1]) / 60.0
        except Exception as e:
            self.log(f'Duration parse error: {str(e)}')
            
        return None

    def format_bytes(self, size):
        n = 0
        slabels = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
        while size > 1024:
            size /= 1024
            n += 1
            return f"{size:.2f} {slabels.get(n, 'PB')}"

    # --- UI VIEWS ---

    def list_history(self):
        hist = self._get_history()
        items_to_add = []
        
        if hist:
            li_clear = xbmcgui.ListItem('[COLOR red]-- Clear Search History --[/COLOR]')
            li_clear.setArt({'icon': 'DefaultFolder.png'})
            li_clear.setProperty('IsPlayable', 'false')
            url_clear = f"{sys.argv[0]}?action=clear_history"
            items_to_add.append((url_clear, li_clear, False))

        for entry in hist:
            stype = entry.get('search_type', 'video')
            stype_display = "TV" if stype == 'tv' else stype.capitalize()
            
            title = f"{urllib.parse.unquote(entry['keyword'])} ({stype_display})"
                
            listitem = xbmcgui.ListItem(title)
            listitem.setArt({'icon': _icon, 'fanart': _fanart})
            listitem.setProperty('IsPlayable', 'false')
            
            url = f"{sys.argv[0]}?" + urllib.parse.urlencode({
                'action': 'search',
                'keyword': entry['keyword'],
                'content_type': entry['content_type'],
                'search_type': stype
            })
            items_to_add.append((url, listitem, True))
            
        if items_to_add:
            xbmcplugin.addDirectoryItems(int(sys.argv[1]), items_to_add)
            
        xbmcplugin.setContent(int(sys.argv[1]), 'files')
        xbmcplugin.endOfDirectory(int(sys.argv[1]), cacheToDisc=False)

    def list_resume(self):
        res = self._get_resume()
        if not res:
            xbmcgui.Dialog().notification(_plugin, "No unfinished media found.", _icon, 3000, False)
            xbmcplugin.endOfDirectory(int(sys.argv[1]), True)
            return
            
        items_to_add = []
        li_clear = xbmcgui.ListItem('[COLOR red]-- Clear All Resumes --[/COLOR]')
        li_clear.setArt({'icon': 'DefaultFolder.png'})
        li_clear.setProperty('IsPlayable', 'false')
        url_clear = f"{sys.argv[0]}?action=clear_all_resumes"
        items_to_add.append((url_clear, li_clear, False))
            
        for key, data in res.items():
            title = f"{data['title']} [I](Resume)[/I]"
            listitem = self.make_listitem({'title': title}, data['content_type'])
            listitem.setArt({'fanart': _fanart})
            listitem.setProperty('IsPlayable', 'true')
            
            ctx_url = f"{sys.argv[0]}?" + urllib.parse.urlencode({
                'action': 'remove_resume',
                'target': data['item_id'],
                'ep_tag': data['ep_tag']
            })
            listitem.addContextMenuItems([('Remove from Continue Watching', f"RunPlugin({ctx_url})")])
            
            url = f"{sys.argv[0]}?" + urllib.parse.urlencode({
                'action': 'play_video',
                'target': data['item_id'],
                'ep_tag': data['ep_tag'],
                'content_type': data['content_type']
            })
            items_to_add.append((url, listitem, False))
            
        if items_to_add:
            xbmcplugin.addDirectoryItems(int(sys.argv[1]), items_to_add)
            
        xbmcplugin.setContent(int(sys.argv[1]), 'videos')
        xbmcplugin.endOfDirectory(int(sys.argv[1]), cacheToDisc=False)

    def clear_cache(self):
        if DEBUG:
            self.log('clear_cache()')
        cache.cache_clear()
        xbmcgui.Dialog().notification(_plugin, _language(30201), _icon, 3000, False)

    # --- API COMMUNICATORS ---

    def get_search_items(self, filter_map, target, page, content_type, sort_param=None):
        cd = {}
        params = {
            'service_backend': 'metadata',
            'user_query': target,
            'hits_per_page': 100,
            'page': page,
            'filter_map': filter_map,
            'aggregations': 'false',
            'client_url': self.base_url
        }
        if sort_param:
            params['sort'] = sort_param
            
        resp = client.request(self.search_url, headers=self.headers, params=params)
        
        if resp and isinstance(resp, dict):
            cd = resp.get('response', {}).get('body', {}).get('hits', {})
        return cd

    def get_items(self, filter_map, target, page):
        cd = {}
        params = {
            'page_type': 'collection_details',
            'page_target': target,
            'hits_per_page': 100,
            'page': page,
            'filter_map': filter_map,
            'aggregations': 'false',
            'client_url': self.base_url
        }
        
        resp = client.request(self.search_url, headers=self.headers, params=params)
        
        if resp and isinstance(resp, dict):
            cd = resp.get('response', {}).get('body', {}).get('hits', {})
        return cd

    # --- CORE LISTERS ---

    def list_collections(self, page, content_type):
        target = 'movies' if content_type == 'video' else 'audio'
        filter_map = '{"mediatype":{"collection":"inc"}}'
        data = cache.get(self.get_items, cache_duration, filter_map, target, page)
        
        if data:
            items = data.get('hits')
            if not items:
                xbmcgui.Dialog().notification(_plugin, "No playable media found.", _icon, 3000, False)
                xbmcplugin.endOfDirectory(int(sys.argv[1]), True)
                return
                
            items_to_add = []
            
            if page == 1:
                if content_type == 'video':
                    shortcuts = [
                        ("opensource_movies", "[COLOR gold]Community Video (Default)[/COLOR]", "General video and movie uploads"),
                        ("dvdtray", "[COLOR gold]DVD Tray[/COLOR]", "Full DVD ISO backups"),
                        ("vhsvault", "[COLOR gold]The VHS Vault[/COLOR]", "Raw VHS captures and preservation"),
                        ("television_inbox", "[COLOR gold]Unsorted Television[/COLOR]", "Raw TV captures"),
                        ("laserdiscs", "[COLOR gold]Laserdisc Archive[/COLOR]", "High quality laserdisc rips"),
                        ("feature_films", "[COLOR gold]Feature Films[/COLOR]", "Classic full length movies"),
                        ("anime", "[COLOR gold]The Anime Cascade[/COLOR]", "Anime episodes and series"),
                        ("animationandcartoons", "[COLOR gold]Animation & Cartoons[/COLOR]", "Classic cartoons"),
                        ("classic_tv", "[COLOR gold]Classic TV[/COLOR]", "Vintage television broadcasts"),
                        ("SciFi_Horror", "[COLOR gold]Sci-Fi / Horror[/COLOR]", "Sci-Fi and Horror films"),
                        ("comedy_films", "[COLOR gold]Comedy Films[/COLOR]", "Comedy films"),
                        ("film_noir", "[COLOR gold]Film Noir[/COLOR]", "Classic film noir"),
                        ("bmovies", "[COLOR gold]B-Movies[/COLOR]", "B-movie classics")
                    ]
                else:
                    shortcuts = [
                        ("opensource_audio", "[COLOR gold]Community Audio (Default)[/COLOR]", "Uncurated audio and music uploads"),
                        ("album_recordings", "[COLOR gold]Long Playing Records (Vinyl)[/COLOR]", "Vinyl LP preservation project"),
                        ("folksoundomy_music", "[COLOR gold]Folksoundomy Music[/COLOR]", "Full albums and soundboards"),
                        ("audio_music", "[COLOR gold]Music, Arts & Culture[/COLOR]", "General music collection"),
                        ("etree", "[COLOR gold]Live Music Archive (Concerts)[/COLOR]", "Lossless concert recordings"),
                        ("78rpm", "[COLOR gold]78 RPMs & Cylinder Recordings[/COLOR]", "Vintage 78 RPM records"),
                        ("netlabels", "[COLOR gold]Netlabels (Indie Albums)[/COLOR]", "Independent netlabel releases"),
                        ("podcasts", "[COLOR gold]Podcasts & Radio[/COLOR]", "Podcasts and radio broadcasts")
                    ]

                for slug, title, plot in shortcuts:
                    labels = {
                        'title': title,
                        'plot' if content_type == 'video' else 'comment': plot
                    }
                    listitem = self.make_listitem(labels, content_type)
                    listitem.setArt({'icon': _icon, 'thumb': _icon, 'fanart': _fanart})
                    listitem.setProperty('IsPlayable', 'false')
                    url = f"{sys.argv[0]}?" + urllib.parse.urlencode({
                        'action': 'list_items',
                        'page': 1,
                        'target': slug,
                        'content_type': content_type
                    })
                    items_to_add.append((url, listitem, True))
                
            for item in items:
                fields = item.get('fields', {})
                if not self._has_playable_media(fields, content_type): continue
                
                title = fields.get('title')
                if isinstance(title, list):
                    title = title[0] if title else ''
                slug = fields.get('identifier')
                if not title:
                    title = slug
                    
                plot = fields.get('description')
                if isinstance(plot, list):
                    plot = plot[0] if plot else ''
                plot = unescape(plot) if plot else ''
                
                count = fields.get('item_count')
                
                labels = {
                    'title': f"{title} [I]({count:,} items)[/I]",
                    'plot' if content_type == 'video' else 'comment': plot
                }
                listitem = self.make_listitem(labels, content_type)
                listitem.setArt({'icon': self.img_path + slug, 'thumb': self.img_path + slug, 'fanart': _fanart})
                listitem.setProperty('IsPlayable', 'false')
                
                url = f"{sys.argv[0]}?" + urllib.parse.urlencode({
                    'action': 'list_items',
                    'page': 1,
                    'target': slug,
                    'content_type': content_type
                })
                items_to_add.append((url, listitem, True))

            total = data.get('total')
            if page * 100 < total:
                lastpg = math.ceil(total / 100)
                page += 1
                listitem = self.make_listitem({'title': f"[COLOR lime]{_language(30204)}...[/COLOR] ({page}/{lastpg})"}, content_type)
                listitem.setArt({'icon': _icon, 'thumb': _icon, 'fanart': _fanart})
                listitem.setProperty('IsPlayable', 'false')
                url = f"{sys.argv[0]}?" + urllib.parse.urlencode({
                    'action': 'list_collections',
                    'page': page,
                    'content_type': content_type
                })
                items_to_add.append((url, listitem, True))

            if items_to_add:
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), items_to_add)

            xbmcplugin.setContent(int(sys.argv[1]), 'videos' if content_type == 'video' else 'albums')
            xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
            xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_TITLE)
            xbmcplugin.endOfDirectory(int(sys.argv[1]), cacheToDisc=True)
        else:
            xbmcgui.Dialog().notification(_plugin, "Error retrieving collections.", _icon, 3000, False)
            xbmcplugin.endOfDirectory(int(sys.argv[1]), True)

    def list_items(self, target, page, content_type):
        mt_type = 'movies' if content_type == 'video' else 'audio'
        filter_map = f'{{"mediatype":{{"{mt_type}":"inc","etree":"inc"}}}}'
        data = cache.get(self.get_items, cache_duration, filter_map, target, page)
        
        if data:
            items = data.get('hits')
            if not items:
                xbmcgui.Dialog().notification(_plugin, "No playable media found.", _icon, 3000, False)
                xbmcplugin.endOfDirectory(int(sys.argv[1]), True)
                return
                
            items_to_add = []
            for item in items:
                fields = item.get('fields', {})
                if not self._has_playable_media(fields, content_type): continue
                
                title = fields.get('title')
                if isinstance(title, list):
                    title = title[0] if title else ''
                slug = fields.get('identifier')
                if not title:
                    title = slug
                    
                plot = fields.get('description')
                if isinstance(plot, list):
                    plot = plot[0] if plot else ''
                plot = unescape(plot) if plot else ''
                
                labels = {
                    'title': title,
                    'plot' if content_type == 'video' else 'comment': plot
                }
                listitem = self.make_listitem(labels, content_type)
                listitem.setArt({'icon': self.img_path + slug, 'thumb': self.img_path + slug, 'fanart': _fanart})
                listitem.setProperty('IsPlayable', 'false')
                
                url = f"{sys.argv[0]}?" + urllib.parse.urlencode({
                    'action': 'expand_item',
                    'target': slug,
                    'content_type': content_type
                })
                items_to_add.append((url, listitem, True))

            if not items_to_add:
                xbmcgui.Dialog().notification(_plugin, "No playable media found after filtering.", _icon, 3000, False)
                xbmcplugin.endOfDirectory(int(sys.argv[1]), True)
                return

            total = data.get('total')
            if page * 100 < total:
                lastpg = math.ceil(total / 100)
                page += 1
                listitem = self.make_listitem({'title': f"[COLOR lime]{_language(30204)}...[/COLOR] ({page}/{lastpg})"}, content_type)
                listitem.setArt({'icon': _icon, 'thumb': _icon, 'fanart': _fanart})
                listitem.setProperty('IsPlayable', 'false')
                url = f"{sys.argv[0]}?" + urllib.parse.urlencode({
                    'action': 'list_items',
                    'page': page,
                    'target': target,
                    'content_type': content_type
                })
                items_to_add.append((url, listitem, True))

            if items_to_add:
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), items_to_add)

            xbmcplugin.setContent(int(sys.argv[1]), 'videos' if content_type == 'video' else 'songs')
            xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
            xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_TITLE)
            xbmcplugin.endOfDirectory(int(sys.argv[1]), cacheToDisc=True)
        else:
            xbmcgui.Dialog().notification(_plugin, "Error retrieving items.", _icon, 3000, False)
            xbmcplugin.endOfDirectory(int(sys.argv[1]), True)

    def search(self, content_type):
        search_type = self.parameters('search_type') or 'video'
        prefilled_keyword = urllib.parse.unquote(self.parameters('keyword'))
        
        collections = []
        if search_type == 'movie':
            collections = [
                ("None (Search All Movies)", "none"),
                ("Community Video (Default)", "opensource_movies"),
                ("DVD Tray", "dvdtray"),
                ("The VHS Vault", "vhsvault"),
                ("Laserdisc Archive", "laserdiscs"),
                ("Feature Films", "feature_films"),
                ("Animation & Cartoons", "animationandcartoons"),
                ("Sci-Fi / Horror", "SciFi_Horror"),
                ("Comedy Films", "comedy_films"),
                ("Film Noir", "film_noir"),
                ("B-Movies", "bmovies")
            ]
            heading = "Search Movies"
        elif search_type == 'tv':
            collections = [
                ("None (Search All TV Shows)", "none"),
                ("Community Video (Default)", "opensource_movies"),
                ("Unsorted Television", "television_inbox"),
                ("DVD Tray", "dvdtray"),
                ("The VHS Vault", "vhsvault"),
                ("The Anime Cascade", "anime"),
                ("Animation & Cartoons", "animationandcartoons"),
                ("Classic TV", "classic_tv"),
                ("Television Archive", "tvarchive"),
                ("Television", "television"),
                ("Laserdisc Archive", "laserdiscs")
            ]
            heading = "Search TV Shows"
        elif search_type == 'audio':
            collections = [
                ("None (Search All Audio)", "none"),
                ("Community Audio (Default)", "opensource_audio"),
                ("Long Playing Records (Vinyl)", "album_recordings"),
                ("Folksoundomy Music", "folksoundomy_music"),
                ("Music, Arts & Culture", "audio_music"),
                ("Live Music Archive (Concerts)", "etree"),
                ("78 RPMs & Cylinder Recordings", "78rpm"),
                ("Netlabels (Indie Albums)", "netlabels"),
                ("Podcasts & Radio", "podcasts")
            ]
            heading = "Search Audio & Music"
        else:
            heading = f"Search {content_type.capitalize()}"
            
        if prefilled_keyword:
            search_text = prefilled_keyword
        else:
            keyboard = xbmc.Keyboard()
            keyboard.setHeading(heading)
            keyboard.doModal()
            
            if keyboard.isConfirmed() and len(keyboard.getText()) > 2:
                search_text = keyboard.getText()
            else:
                xbmcgui.Dialog().notification(_plugin, _language(30202), _icon, 3000, False)
                xbmcplugin.endOfDirectory(int(sys.argv[1]), True)
                return

        self._save_history(search_text, content_type, search_type)
        
        collection_str = ""
        auto_select_col = _settings('auto_select_collection') == 'true'
        manual_override = _settings('manual_collection_override') == 'true'
        
        if manual_override:
            if search_type == 'movie':
                collection_str = _settings('manual_movie_col')
            elif search_type == 'tv':
                collection_str = _settings('manual_tv_col')
            else:
                collection_str = _settings('manual_audio_col')
                
            if not collection_str.strip():
                collection_str = "opensource_movies" if content_type == 'video' else "opensource_audio"
        elif auto_select_col:
            if search_type == 'movie':
                collection_str = _settings('default_movie_collection') or 'opensource_movies'
            elif search_type == 'tv':
                collection_str = _settings('default_tv_collection') or 'opensource_movies'
            else:
                collection_str = _settings('default_audio_collection') or 'opensource_audio'
        elif collections:
            col_names = [c[0] for c in collections]
            selected_indices = xbmcgui.Dialog().multiselect("Select Collections (Default)", col_names)
            
            if selected_indices is None:
                xbmcplugin.endOfDirectory(int(sys.argv[1]), True)
                return
                
            if not selected_indices:
                collection_str = "opensource_movies" if content_type == 'video' else "opensource_audio"
            else:
                selected_slugs = [collections[i][1] for i in selected_indices]
                if "none" in selected_slugs:
                    collection_str = "none"
                else:
                    collection_str = ",".join(selected_slugs)
        
        xbmcplugin.endOfDirectory(int(sys.argv[1]), cacheToDisc=False)
        
        params = {
            'action': 'search_word',
            'keyword': search_text,
            'content_type': content_type,
            'search_type': search_type,
            'page': 1
        }
        if collection_str:
            params['collections'] = collection_str
            
        url = f"{sys.argv[0]}?" + urllib.parse.urlencode(params)
        xbmc.executebuiltin(f"Container.Update({url},replace)")

    def search_word(self, search_text, page, content_type):
        search_type = self.parameters('search_type') or 'video'
        collection_str = self.parameters('collections')
        
        mt_type = 'movies' if content_type == 'video' else 'audio'
        
        f_map = {
            "mediatype": {mt_type: "inc", "etree": "inc"}
        }
        
        query_string = search_text
        sort_param = None
        
        # 1. Routing Trap Fix & Global Assignment
        if not collection_str:
            if search_type == 'video':
                collection_str = "none"
            else:
                collection_str = "opensource_movies" if content_type == 'video' else "opensource_audio"
                
        # 2. Collection Injection (Bypassed if 'none')
        if collection_str != "none":
            cols = [c.strip() for c in collection_str.split(',') if c.strip()]
            if cols:
                f_map["collection"] = {c: "inc" for c in cols}
                
        # 3. Sort Injection & Exclusions
        if search_type == 'movie':
            exclusions = '(trailer OR teaser OR promo OR clip OR snippet OR "short film" OR sample OR review OR intro OR menu OR extras OR bonus OR preview OR previews OR fandub OR "fan dub" OR "fan edit" OR "fan project" OR "screen recording")'
            query_string = f'({search_text}) AND NOT title:{exclusions} AND NOT subject:{exclusions}'
        elif search_type == 'tv':
            exclusions = '(promo OR clip OR commercial OR bumper OR advert OR "tv spot" OR teaser OR trailer OR intro OR menu OR extras OR bonus OR preview OR previews OR fandub OR "fan dub" OR "fan edit" OR "fan project" OR "screen recording")'
            query_string = f'({search_text}) AND NOT title:{exclusions} AND NOT subject:{exclusions}'
            
        filter_map_json = json.dumps(f_map, separators=(',', ':'))
            
        data = cache.get(self.get_search_items, cache_duration, filter_map_json, query_string, page, content_type, sort_param)
        
        if data:
            items = data.get('hits')
            if not items:
                xbmcgui.Dialog().notification(_plugin, "No media matching format found.", _icon, 3000, False)
                xbmcplugin.endOfDirectory(int(sys.argv[1]), True)
                return
                
            items_to_add = []
            
            for item in items:
                fields = item.get('fields', {})
                if not self._has_playable_media(fields, content_type): continue
                
                if search_type in ['movie', 'tv']:
                    dur_data = fields.get('duration') or fields.get('length')
                    dur_mins = self._parse_duration_to_minutes(dur_data)
                    
                    if dur_mins is not None:
                        if search_type == 'movie' and dur_mins < 45:
                            continue
                        if search_type == 'tv' and dur_mins < 5:
                            continue
                
                title = fields.get('title')
                if isinstance(title, list):
                    title = title[0] if title else ''
                slug = fields.get('identifier')
                if not title:
                    title = slug
                
                plot = fields.get('description')
                if isinstance(plot, list):
                    plot = plot[0] if plot else ''
                plot = unescape(plot) if plot else ''
                
                labels = {
                    'title': title,
                    'plot' if content_type == 'video' else 'comment': plot
                }
                listitem = self.make_listitem(labels, content_type)
                listitem.setArt({'icon': self.img_path + slug, 'thumb': self.img_path + slug, 'fanart': _fanart})
                listitem.setProperty('IsPlayable', 'false')
                
                url = f"{sys.argv[0]}?" + urllib.parse.urlencode({
                    'action': 'expand_item',
                    'target': slug,
                    'content_type': content_type
                })
                items_to_add.append((url, listitem, True))

            if not items_to_add:
                xbmcgui.Dialog().notification(_plugin, "No playable media found after filtering.", _icon, 3000, False)
                xbmcplugin.endOfDirectory(int(sys.argv[1]), True)
                return

            total = data.get('total')
            if page * 100 < total:
                lastpg = math.ceil(total / 100)
                page += 1
                listitem = self.make_listitem({'title': f"[COLOR lime]{_language(30204)}...[/COLOR] ({page}/{lastpg})"}, content_type)
                listitem.setArt({'icon': _icon, 'thumb': _icon, 'fanart': _fanart})
                listitem.setProperty('IsPlayable', 'false')
                
                params = {
                    'action': 'search_word',
                    'keyword': search_text,
                    'content_type': content_type,
                    'search_type': search_type,
                    'page': page
                }
                if collection_str:
                    params['collections'] = collection_str 
                    
                url = f"{sys.argv[0]}?" + urllib.parse.urlencode(params)
                items_to_add.append((url, listitem, True))

            if items_to_add:
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), items_to_add)

            xbmcplugin.setContent(int(sys.argv[1]), 'videos' if content_type == 'video' else 'songs')
            xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
            xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_TITLE)
            xbmcplugin.endOfDirectory(int(sys.argv[1]), cacheToDisc=True)
        else:
            xbmcgui.Dialog().notification(_plugin, "Error retrieving search results.", _icon, 3000, False)
            xbmcplugin.endOfDirectory(int(sys.argv[1]), True)

    # --- MEDIA PLAYBACK AND RESOLVING ---

    def get_episode_identifier(self, filename):
        clean_filename = filename.split('/')[-1].lower()
        
        m = self.re_s_e.search(clean_filename)
        if m: return f"S{int(m.group(1)):02d}E{int(m.group(2)):02d}"
        
        m = self.re_x.search(clean_filename)
        if m: return f"S{int(m.group(1)):02d}E{int(m.group(2)):02d}"
        
        m = self.re_ep.search(clean_filename)
        if m: return f"EP{int(m.group(1)):02d}"
        
        m = self.re_track.search(clean_filename)
        if m: return f"Track {int(m.group(1)):03d}"
        
        return clean_filename.rsplit('.', 1)[0]

    def expand_item(self, item_id, content_type):
        api_url = f"{self.base_url}metadata/{item_id}"
        jd = cache.get(client.request, cache_duration, api_url)

        if not isinstance(jd, dict) or 'files' not in jd:
            xbmcgui.Dialog().notification(_plugin, "No playable media found.", _icon, 3000, False)
            xbmcplugin.endOfDirectory(int(sys.argv[1]), True)
            return

        valid_exts = self.video_exts if content_type == 'video' else self.audio_exts
        sources = [i for i in jd.get('files', []) if i.get('name', '').lower().endswith(valid_exts) and '.ia.' not in i.get('name', '').lower()]

        if not sources:
            xbmcgui.Dialog().notification(_plugin, "No playable media found.", _icon, 3000, False)
            xbmcplugin.endOfDirectory(int(sys.argv[1]), True)
            return

        episodes = {}
        for source in sources:
            filename = source.get('name')
            ep_tag = self.get_episode_identifier(filename)
            if ep_tag not in episodes: episodes[ep_tag] = []
            episodes[ep_tag].append(source)
            
        sorted_tags = sorted(list(episodes.keys()), key=lambda item: [text.zfill(10) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', item)])
        
        res_data = self._get_resume()
        items_to_add = []
        
        for tag in sorted_tags:
            eps = episodes[tag]
            formats = [src.get('name').split('.')[-1].lower() for src in eps]
            format_str = ', '.join(f'.{fmt}' for fmt in set(formats))
            
            clean_title = eps[0].get('title')
            if isinstance(clean_title, list):
                clean_title = clean_title[0] if clean_title else ''
                
            if not clean_title:
                clean_title = tag if tag != eps[0].get('name', '').rsplit('.', 1)[0] else eps[0].get('name', '').split('/')[-1]
            
            display_title = f"{clean_title} ({format_str})"
            
            res_key = f"{item_id}_{tag}"
            if res_key in res_data:
                display_title = f"{display_title} [I](Resume)[/I]"
            
            listitem = self.make_listitem({'title': display_title}, content_type)
            listitem.setArt({'fanart': _fanart})
            listitem.setProperty('IsPlayable', 'true')
            
            url = f"{sys.argv[0]}?" + urllib.parse.urlencode({
                'action': 'play_video',
                'target': item_id,
                'ep_tag': tag,
                'content_type': content_type
            })
            items_to_add.append((url, listitem, False))
            
        if items_to_add:
            xbmcplugin.addDirectoryItems(int(sys.argv[1]), items_to_add)
            
        xbmcplugin.setContent(int(sys.argv[1]), 'videos' if content_type == 'video' else 'songs')
        xbmcplugin.endOfDirectory(int(sys.argv[1]), cacheToDisc=False)

    def play_video(self, item_id, content_type):
        ep_tag = self.parameters('ep_tag')
        
        # When queue=0 it means Kodi's playlist is automatically playing this next background item.
        auto_play = _settings('auto_play_queue') != 'false'
        do_queue = self.parameters('queue') != '0' and auto_play

        # Extract playback memory (if queued by background playlist)
        pref_ext = self.parameters('pref_ext')
        pref_height = self.parameters('pref_height')
        pref_source = self.parameters('pref_source')

        api_url = f"{self.base_url}metadata/{item_id}"
        jd = cache.get(client.request, cache_duration, api_url)

        if not isinstance(jd, dict) or 'files' not in jd:
            xbmcplugin.setResolvedUrl(int(sys.argv[1]), False, listitem=xbmcgui.ListItem())
            return

        parent_title = jd.get('metadata', {}).get('title', '')
        if isinstance(parent_title, list):
            parent_title = parent_title[0] if parent_title else ''

        if parent_title and parent_title.lower() not in ep_tag.lower():
            resume_title = f"{parent_title} - {ep_tag}"
        else:
            resume_title = ep_tag if ep_tag else parent_title

        files = jd.get('files', [])
        workable_servers = jd.get('workable_servers', ['archive.org'])
        item_dir = jd.get('dir', '')

        valid_exts = self.video_exts if content_type == 'video' else self.audio_exts
        sources = [i for i in files if i.get('name', '').lower().endswith(valid_exts) and '.ia.' not in i.get('name', '').lower()]
        
        episodes = {}
        for source in sources:
            filename = source.get('name')
            tag = self.get_episode_identifier(filename)
            if tag not in episodes: episodes[tag] = []
            episodes[tag].append(source)
            
        sorted_tags = sorted(list(episodes.keys()), key=lambda item: [text.zfill(10) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', item)])
        
        if ep_tag not in episodes:
            xbmcplugin.setResolvedUrl(int(sys.argv[1]), False, listitem=xbmcgui.ListItem())
            return
            
        target_files = episodes[ep_tag]
        selected_file = None

        auto_stream = _settings('auto_select_stream') == 'true'
        user_pref_vid_ext = _settings('pref_video_ext')
        user_pref_aud_ext = _settings('pref_audio_ext')
        max_res_str = _settings('max_resolution')
        max_res = self._safe_int(max_res_str) if max_res_str != 'Any' else 99999

        # --- SELECTION & FORMAT MEMORY LOGIC ---
        if len(target_files) > 1:
            if content_type == 'video':
                target_files.sort(key=lambda i: (self._safe_int(i.get('height')), i.get('source', ''), self._safe_int(i.get('size'))), reverse=True)
            else:
                target_files.sort(key=lambda i: self._safe_int(i.get('size')), reverse=True)

            # If an automated playlist queue is playing, force exact match to previous video settings WITHOUT throwing Dialog Menu
            if not do_queue and pref_ext:
                best_match = None
                matches = [f for f in target_files if f.get('name', '').lower().endswith(pref_ext)]
                
                if matches:
                    if pref_height:
                        height_matches = [f for f in matches if str(f.get('height', '')) == pref_height]
                        if height_matches:
                            if pref_source:
                                source_matches = [f for f in height_matches if str(f.get('source', '')).lower() == pref_source.lower()]
                                best_match = source_matches[0] if source_matches else height_matches[0]
                            else:
                                best_match = height_matches[0]
                        else:
                            best_match = matches[0]
                    else:
                        best_match = matches[0]
                
                # Fallback to the best quality option if exact match isn't found
                selected_file = best_match if best_match else target_files[0]
                
            elif auto_stream:
                if content_type == 'video' and max_res < 99999:
                    filtered_files = [f for f in target_files if self._safe_int(f.get('height')) <= max_res or self._safe_int(f.get('height')) == 0]
                    if filtered_files:
                        target_files = filtered_files
                
                best_match = None
                pref_ext_setting = user_pref_vid_ext if content_type == 'video' else user_pref_aud_ext
                if pref_ext_setting and pref_ext_setting != 'Ask Every Time':
                    matches = [f for f in target_files if f.get('name', '').lower().endswith(pref_ext_setting.lower())]
                    if matches:
                        best_match = matches[0]
                
                selected_file = best_match if best_match else target_files[0]

            # Initial click by User: Prompt for standard clean stream selection UI
            else:
                srcs = []
                for i in target_files:
                    ext = i.get('name', '').split('.')[-1].upper()
                    size = self.format_bytes(self._safe_int(i.get('size')))
                    source = i.get('source', 'Unknown').capitalize()
                    
                    if content_type == 'video':
                        height = self._safe_int(i.get('height'))
                        res = f"{height}p" if height > 0 else "Unknown Res"
                        srcs.append(f"[{ext}] {res} | {size} | {source}")
                    else:
                        srcs.append(f"[{ext}] {size} | {source}")
                    
                ret = xbmcgui.Dialog().select(_language(30203) if _language(30203) else "Select Stream", srcs)
                if ret == -1:
                    xbmcplugin.setResolvedUrl(int(sys.argv[1]), False, listitem=xbmcgui.ListItem())
                    return
                selected_file = target_files[ret]
        else:
            selected_file = target_files[0]

        surl = f"https://{random.choice(workable_servers)}{item_dir}/{urllib.parse.quote(selected_file.get('name', ''), safe='/')}"

        # Apply cURL pipe injection for persistent connections and extended timeout
        surl = f"{surl}|Connection=keep-alive&Timeout=60"

        li = self.make_listitem({'title': resume_title}, content_type)
        li.setArt({'fanart': _fanart})
        li.setPath(surl)
        
        # Optimization for DVD ISO streaming
        if selected_file.get('name', '').lower().endswith('.iso'):
            if hasattr(li, 'setMimeType'):
                li.setMimeType('application/x-iso9660-image')
            else:
                li.setProperty('mimetype', 'application/x-iso9660-image')
                
            # Disable Kodi's internal network probe to preserve cache
            if hasattr(li, 'setContentLookup'):
                li.setContentLookup(False)
            li.setProperty('VideoPlayer.ContentLookup', 'false')
        
        # Intercept and process local resume data before handoff to prevent double-initialization
        res_data = self._get_resume()
        res_key = f"{item_id}_{ep_tag}"
        if res_key in res_data:
            time_pos = res_data[res_key].get('time', 0.0)
            if time_pos > 0:
                li.setProperty('StartOffset', str(time_pos))
                li.setProperty('ResumeTime', '0')

        xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, listitem=li)
        
        remaining_tags = []
        if do_queue:
            try:
                current_idx = sorted_tags.index(ep_tag)
                remaining_tags = sorted_tags[current_idx + 1:]
            except ValueError: pass
            
            if remaining_tags:
                # Capture user's format preferences to permanently pass to the queued episodes
                sel_ext = selected_file.get('name', '').split('.')[-1].lower()
                sel_height = str(selected_file.get('height', ''))
                sel_source = str(selected_file.get('source', ''))
                
                # Generate the playlist synchronously in the main thread to prevent Kodi UI race conditions
                playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO if content_type == 'video' else xbmc.PLAYLIST_MUSIC)
                for r_tag in remaining_tags:
                    q_url = f"{sys.argv[0]}?" + urllib.parse.urlencode({
                        'action': 'play_video',
                        'target': item_id,
                        'ep_tag': r_tag,
                        'content_type': content_type,
                        'queue': '0', 
                        'pref_ext': sel_ext,       # Queue inherits your format choice
                        'pref_height': sel_height, # Queue inherits your res choice
                        'pref_source': sel_source  # Queue inherits your source choice
                    })
                    q_li = self.make_listitem({'title': r_tag}, content_type)
                    q_li.setArt({'fanart': _fanart})
                    playlist.add(url=q_url, listitem=q_li)
                
        def background_tracker():
            player = xbmc.Player()
            monitor = xbmc.Monitor()
            if monitor.waitForAbort(5.0): return
            
            last_time_pos = 0
            last_pct = 0.0
            
            while player.isPlaying() and not monitor.abortRequested():
                try:
                    time_pos = player.getTime()
                    total = player.getTotalTime()
                    if total > 0:
                        last_time_pos = time_pos
                        last_pct = time_pos / total
                except Exception:
                    pass
                if monitor.waitForAbort(5.0): break
                
            if 0.03 < last_pct < 0.95:
                self._save_resume(item_id, ep_tag, resume_title, content_type, last_time_pos)
            elif last_pct >= 0.95:
                self._remove_resume(item_id, ep_tag)
                
        if content_type == 'video':
            t2 = threading.Thread(target=background_tracker)
            t2.daemon = True
            t2.start()

    def parameters(self, arg):
        val = self.args.get(arg, '')
        if isinstance(val, list):
            val = val[0]
        return val

    def make_listitem(self, labels, content_type):
        title_str = str(labels.get('title') or '')
        li = xbmcgui.ListItem(title_str)
        if _kodiver >= 20.0:
            if content_type == 'video':
                vtag = li.getVideoInfoTag()
                vtag.setTitle(title_str)
                vtag.setOriginalTitle(title_str)
                if labels.get('plot'):
                    plot_str = str(labels.get('plot') or '')
                    vtag.setPlot(plot_str)
                    vtag.setPlotOutline(plot_str)
                if labels.get('comment'):
                    vtag.setComment(str(labels.get('comment') or ''))
                if labels.get('mediatype'):
                    vtag.setMediaType(str(labels.get('mediatype') or ''))
                if labels.get('duration'):
                    try:
                        vtag.setDuration(int(labels.get('duration')))
                    except:
                        pass
            else:
                mtag = li.getMusicInfoTag()
                mtag.setTitle(title_str)
                if labels.get('comment'):
                    mtag.setComment(str(labels.get('comment') or ''))
                if labels.get('duration'):
                    try:
                        mtag.setDuration(int(labels.get('duration')))
                    except:
                        pass
        else:
            li.setInfo(type='video' if content_type == 'video' else 'music', infoLabels=labels)

        return li

    def log(self, description):
        xbmc.log(f"[ADD-ON] '{_plugin} v{_version}': {description}", xbmc.LOGINFO)

if __name__ == '__main__':
    Main()
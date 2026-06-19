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


class IATPlayer(xbmc.Player):
    """
    Custom Player subclass to safely handle Kodi's internal playback events
    for accurate resume point tracking and playlist auto-advancing.
    """
    def __init__(self, item_id, ep_tag, resume_title, content_type, search_type, main_instance):
        super().__init__()
        self.item_id = item_id
        self.ep_tag = ep_tag
        self.resume_title = resume_title
        self.content_type = content_type
        self.search_type = search_type
        self.main_instance = main_instance
        self.last_known_time = 0.0
        self.is_active = True

    def onPlayBackEnded(self):
        # Media finished completely natively (or playlist advanced). Wipe the resume tag.
        self.main_instance._remove_resume(self.item_id, self.ep_tag)
        self.is_active = False

    def onPlayBackStopped(self):
        # Attempt immediate fallback capture of time in case player is still responding
        try:
            current_time = self.getTime()
            if current_time > 0:
                self.last_known_time = current_time
        except Exception:
            pass

        # User manually stopped media early. Save the safely cached resume point.
        if self.last_known_time > 0:
            self.main_instance._save_resume(self.item_id, self.ep_tag, self.resume_title, self.content_type, self.search_type, float(self.last_known_time))
        self.is_active = False


class Main(object):
    def __init__(self):
        self.base_url = 'https://archive.org/'
        self.search_url = f'{self.base_url}services/search/beta/page_production/'
        self.img_path = f'{self.base_url}services/img/'
        self.headers = {
            'Referer': self.base_url,
            'User-Agent': 'Kodi-InternetArchiveTheater-Addon (Contact: https://github.com/PythonTrousers)'
        }
        
        # Cache parameters once on initialization
        self.args = urllib.parse.parse_qs(urllib.parse.urlparse(sys.argv[2]).query)
        
        # Pre-compile regex patterns for performance
        self.re_s_e = re.compile(r's\s*(\d+)[._ -]*e\s*(\d+)')
        self.re_x = re.compile(r'(\d+)\s*x\s*(\d+)')
        self.re_ep = re.compile(r'(?:ep|episode)[._ -]*(\d+)')
        self.re_track = re.compile(r'^(?:track\s*)?(\d{1,3})[\s._-]')
        
        # Revert to standard lists for reliable substring matching
        self.video_exts = ('.mp4', '.mkv', '.avi', '.mov', '.m4v', '.vob', '.iso', '.wmv', '.mpg', '.mpeg', '.flv', '.m2ts', '.ts', '.webm', '.ogv')
        self.audio_exts = ('.mp3', '.flac', '.ogg', '.m4a', '.wav', '.opus', '.aac', '.wma', '.aiff', '.aif', '.shn', '.m4b', '.ape', '.wv', '.iso')
        self.video_markers = ['mp4', 'mkv', 'avi', 'mov', 'm4v', 'h.264', 'h264', 'mpeg', 'matroska', 'vp8', 'vp9', 'webm', 'vob', 'iso', 'wmv', 'mpg', 'flv', 'm2ts', 'ts', 'ogv']
        self.audio_markers = ['mp3', 'flac', 'ogg', 'm4a', 'wav', 'vorbis', 'audio', 'opus', 'aac', 'wma', 'aiff', 'aif', 'shn', 'm4b', 'ape', 'wv', 'iso']

        # Static collections definitions (Used for initial seeding and UI shortcuts)
        self.cat_video = [
            ("opensource_movies", "Community Video", "General video and movie uploads"),
            ("dvdtray", "DVD Tray", "Full DVD ISO backups"),
            ("vhsvault", "The VHS Vault", "Raw VHS captures and preservation"),
            ("television_inbox", "Unsorted Television", "Raw TV captures"),
            ("laserdiscs", "Laserdisc Archive", "High quality laserdisc rips"),
            ("feature_films", "Feature Films", "Classic full length movies"),
            ("anime", "The Anime Cascade", "Anime episodes and series"),
            ("animationandcartoons", "Animation & Cartoons", "Classic cartoons"),
            ("classic_tv", "Classic TV", "Vintage television broadcasts"),
            ("SciFi_Horror", "Sci-Fi / Horror", "Sci-Fi and Horror films"),
            ("comedy_films", "Comedy Films", "Comedy films"),
            ("film_noir", "Film Noir", "Classic film noir"),
            ("bmovies", "B-Movies", "B-movie classics")
        ]
        self.cat_movie = [
            ("opensource_movies", "Community Video"),
            ("dvdtray", "DVD Tray"),
            ("vhsvault", "The VHS Vault"),
            ("laserdiscs", "Laserdisc Archive"),
            ("feature_films", "Feature Films"),
            ("animationandcartoons", "Animation & Cartoons"),
            ("SciFi_Horror", "Sci-Fi / Horror"),
            ("comedy_films", "Comedy Films"),
            ("film_noir", "Film Noir"),
            ("bmovies", "B-Movies")
        ]
        self.cat_tv = [
            ("opensource_movies", "Community Video"),
            ("television_inbox", "Unsorted Television"),
            ("dvdtray", "DVD Tray"),
            ("vhsvault", "The VHS Vault"),
            ("anime", "The Anime Cascade"),
            ("animationandcartoons", "Animation & Cartoons"),
            ("classic_tv", "Classic TV"),
            ("tvarchive", "Television Archive"),
            ("television", "Television"),
            ("laserdiscs", "Laserdisc Archive")
        ]
        self.cat_audio = [
            ("opensource_audio", "Community Audio", "Uncurated audio and music uploads"),
            ("album_recordings", "Long Playing Records (Vinyl)", "Vinyl LP preservation project"),
            ("folksoundomy_music", "Folksoundomy Music", "Full albums and soundboards"),
            ("audio_music", "Music, Arts & Culture", "General music collection"),
            ("etree", "Live Music Archive (Concerts)", "Lossless concert recordings"),
            ("78rpm", "78 RPMs & Cylinder Recordings", "Vintage 78 RPM records"),
            ("netlabels", "Netlabels (Indie Albums)", "Independent netlabel releases"),
            ("podcasts", "Podcasts & Radio", "Podcasts and radio broadcasts")
        ]

        # Prioritize URL parameters over asynchronous settings read to prevent race conditions
        content_type = self.parameters('content_type') or _settings('context') or 'all'
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
        elif action == 'search_collection_menu':
            self.search_collection_menu(content_type)
        elif action == 'list_favorite_collections':
            self.list_favorite_collections(content_type)
        elif action == 'add_favorite_collection':
            self._save_favorite_collection(self.parameters('category'), self.parameters('target'), urllib.parse.unquote(self.parameters('title')))
        elif action == 'remove_favorite_collection':
            self._remove_favorite_collection(self.parameters('category'), self.parameters('target'))
            xbmc.executebuiltin("Container.Refresh")
        elif action == 'restore_defaults':
            if xbmcgui.Dialog().yesno(_plugin, "Are you sure you want to restore all collections to their default settings? This will erase custom collections."):
                self._restore_defaults()
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
        elif action == 'view_changelog':
            self.show_changelog()
        else:
            if action == '':
                self.show_splash_screen()
                self._check_changelog_trigger()
            self.main_menu(content_type)

    def main_menu(self, content_type):
        if DEBUG:
            self.log(f'main_menu({content_type})')
            
        category = [
            {'title': 'Continue Watching', 'key': 'continue'},
            {'title': 'Popular Collections', 'key': 'popular'},
            {'title': 'Favorite Collections', 'key': 'fav_collections'},
            {'title': 'Search Collections', 'key': 'search_collections'},
            {'title': 'Search Movies', 'key': 'search_movie'},
            {'title': 'Search TV Shows', 'key': 'search_tv'},
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
            elif i['key'].startswith('search_') and i['key'] != 'search_collections':
                is_folder = False
            
            if i['key'] == 'search_movie':
                url = f"{sys.argv[0]}?action=search&content_type=video&search_type=movie"
            elif i['key'] == 'search_tv':
                url = f"{sys.argv[0]}?action=search&content_type=video&search_type=tv"
            elif i['key'] == 'search_audio':
                url = f"{sys.argv[0]}?action=search&content_type=audio&search_type=audio"
            elif i['key'] == 'search_collections':
                url = f"{sys.argv[0]}?action=search_collection_menu&content_type=all"
            elif i['key'] == 'fav_collections':
                url = f"{sys.argv[0]}?action=list_favorite_collections&content_type=all"
            elif i['key'] == 'history':
                url = f"{sys.argv[0]}?action=search_history"
                is_folder = True 
            elif i['key'] == 'continue':
                url = f"{sys.argv[0]}?action=continue_watching"
            elif i['key'] == 'popular':
                url = f"{sys.argv[0]}?action=list_collections&page=1&content_type=all"

            xbmcplugin.addDirectoryItems(int(sys.argv[1]), [(url, listitem, is_folder)])

        xbmcplugin.addSortMethod(handle=int(sys.argv[1]), sortMethod=xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.setContent(int(sys.argv[1]), 'addons')
        xbmcplugin.endOfDirectory(int(sys.argv[1]), True)

    def show_splash_screen(self):
        if DEBUG:
            self.log('show_splash_screen()')
            
        try:
            dialog = xbmcgui.WindowDialog()
            splash_image = xbmcgui.ControlImage(0, 0, 1280, 720, _fanart)
            dialog.addControl(splash_image)
            dialog.show()
            xbmc.sleep(1500) 
        except Exception as e:
            self.log(f"Splash screen error: {str(e)}")
        finally:
            dialog.close()

    # --- LOCAL DATA MANAGEMENT ---

    def _safe_int(self, val):
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

    def _seed_favorites(self):
        return {
            "movie": [{"slug": s, "title": t} for s, t in self.cat_movie],
            "tv": [{"slug": s, "title": t} for s, t in self.cat_tv],
            "audio": [{"slug": s, "title": t} for s, t, p in self.cat_audio]
        }

    def _get_favorites(self):
        fav_file = xbmcvfs.translatePath(f"{_addonpath}favorite_collections.json")
        if xbmcvfs.exists(fav_file):
            try:
                with open(fav_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "movie" in data:
                        return data
            except Exception:
                pass
        
        # Seed and generate missing/corrupt dictionary
        favs = self._seed_favorites()
        with open(fav_file, 'w', encoding='utf-8') as f:
            json.dump(favs, f)
        return favs

    def _save_favorite_collection(self, category, slug, title):
        favs = self._get_favorites()
        if category not in favs:
            favs[category] = []
            
        if any(f['slug'] == slug for f in favs[category]):
            xbmcgui.Dialog().notification(_plugin, f"Already in {category.capitalize()} Favorites.", _icon, 2000, False)
            return
            
        favs[category].append({'slug': slug, 'title': title})
        fav_file = xbmcvfs.translatePath(f"{_addonpath}favorite_collections.json")
        with open(fav_file, 'w', encoding='utf-8') as f:
            json.dump(favs, f)
        xbmcgui.Dialog().notification(_plugin, f"Saved to {category.capitalize()} Favorites.", _icon, 2000, False)

    def _remove_favorite_collection(self, category, slug):
        favs = self._get_favorites()
        if category in favs:
            favs[category] = [f for f in favs[category] if f['slug'] != slug]
            fav_file = xbmcvfs.translatePath(f"{_addonpath}favorite_collections.json")
            with open(fav_file, 'w', encoding='utf-8') as f:
                json.dump(favs, f)
            xbmcgui.Dialog().notification(_plugin, "Removed from Favorites.", _icon, 2000, False)

    def _restore_defaults(self):
        fav_file = xbmcvfs.translatePath(f"{_addonpath}favorite_collections.json")
        favs = self._seed_favorites()
        with open(fav_file, 'w', encoding='utf-8') as f:
            json.dump(favs, f)
        xbmcgui.Dialog().notification(_plugin, "Collections restored to defaults.", _icon, 3000, False)

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

    def _save_resume(self, item_id, ep_tag, title, content_type, search_type, time_pos):
        res = self._get_resume()
        key = f"{item_id}_{ep_tag}"
        res[key] = {
            'item_id': item_id,
            'ep_tag': ep_tag,
            'title': title,
            'content_type': content_type,
            'search_type': search_type,
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
        elif content_type == 'audio':
            return any(marker in formats_str for marker in self.audio_markers)
        else: # 'all' or fallback
            combined = self.video_markers + self.audio_markers
            return any(marker in formats_str for marker in combined)

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
        while size > 1024 and n < 4:
            size /= 1024.0
            n += 1
        return f"{size:.2f} {slabels.get(n, 'PB')}"

    # --- UI VIEWS ---
    
    def _check_changelog_trigger(self):
        last_version = _settings('last_run_version')
        if last_version != _version:
            self.show_changelog()
            _addon.setSetting('last_run_version', _version)

    def show_changelog(self):
        changelog_path = xbmcvfs.translatePath(f"{_addon.getAddonInfo('path')}/changelog.txt")
        if xbmcvfs.exists(changelog_path):
            try:
                with open(changelog_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                xbmcgui.Dialog().textviewer(f"{_plugin} - Release Notes", text)
            except Exception as e:
                self.log(f"Error reading changelog: {str(e)}")
        else:
            xbmcgui.Dialog().notification(_plugin, "No changelog found.", _icon, 3000, False)

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
            
            if stype == 'collection':
                stype_display = "Collection"
                url = f"{sys.argv[0]}?" + urllib.parse.urlencode({
                    'action': 'search_collection_menu',
                    'keyword': entry['keyword'],
                    'content_type': entry['content_type']
                })
            else:
                stype_display = "TV" if stype == 'tv' else stype.capitalize()
                url = f"{sys.argv[0]}?" + urllib.parse.urlencode({
                    'action': 'search',
                    'keyword': entry['keyword'],
                    'content_type': entry['content_type'],
                    'search_type': stype
                })
                
            title = f"{urllib.parse.unquote(entry['keyword'])} ({stype_display})"
            listitem = xbmcgui.ListItem(title)
            listitem.setArt({'icon': _icon, 'fanart': _fanart})
            listitem.setProperty('IsPlayable', 'false')
            
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
            
            time_pos = data.get('time', 0.0)
            if time_pos > 0:
                if _kodiver >= 20.0 and data['content_type'] in ['video', 'all']:
                    listitem.getVideoInfoTag().setResumePoint(float(time_pos))
                else:
                    listitem.setProperty('resumetime', str(time_pos))
            
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
                'content_type': data['content_type'],
                'search_type': data.get('search_type', '')
            })
            items_to_add.append((url, listitem, False))
            
        if items_to_add:
            xbmcplugin.addDirectoryItems(int(sys.argv[1]), items_to_add)
            
        xbmcplugin.setContent(int(sys.argv[1]), 'videos')
        xbmcplugin.endOfDirectory(int(sys.argv[1]), cacheToDisc=False)

    def list_favorite_collections(self, content_type):
        fav_category = self.parameters('fav_category')
        
        # Sub-folder Routing
        if not fav_category:
            folders = [
                ("Movie Collections", "movie", "video"),
                ("TV Collections", "tv", "video"),
                ("Audio & Music Collections", "audio", "audio")
            ]
            items_to_add = []
            for title, cat, c_type in folders:
                listitem = xbmcgui.ListItem(title)
                listitem.setArt({'icon': 'DefaultFolder.png', 'thumb': 'DefaultFolder.png', 'fanart': _fanart})
                url = f"{sys.argv[0]}?" + urllib.parse.urlencode({
                    'action': 'list_favorite_collections',
                    'fav_category': cat,
                    'content_type': c_type
                })
                items_to_add.append((url, listitem, True))
            
            xbmcplugin.addDirectoryItems(int(sys.argv[1]), items_to_add)
            xbmcplugin.setContent(int(sys.argv[1]), 'files')
            xbmcplugin.endOfDirectory(int(sys.argv[1]), cacheToDisc=False)
            return

        # Fetch Category Lists
        favs = self._get_favorites()
        category_list = favs.get(fav_category, [])
        
        if not category_list:
            xbmcgui.Dialog().notification(_plugin, f"No favorited {fav_category} collections found.", _icon, 3000, False)
            xbmcplugin.endOfDirectory(int(sys.argv[1]), True)
            return
            
        items_to_add = []
        for f in category_list:
            listitem = xbmcgui.ListItem(f"{f['title']}")
            listitem.setArt({'icon': self.img_path + f['slug'], 'thumb': self.img_path + f['slug'], 'fanart': _fanart})
            listitem.setProperty('IsPlayable', 'false')
            
            ctx_url = f"{sys.argv[0]}?action=remove_favorite_collection&category={fav_category}&target={f['slug']}"
            listitem.addContextMenuItems([('Remove from Favorites', f"RunPlugin({ctx_url})")])
            
            url = f"{sys.argv[0]}?" + urllib.parse.urlencode({
                'action': 'list_items',
                'page': 1,
                'target': f['slug'],
                'content_type': content_type,
                'search_type': fav_category
            })
            items_to_add.append((url, listitem, True))
            
        xbmcplugin.addDirectoryItems(int(sys.argv[1]), items_to_add)
        xbmcplugin.setContent(int(sys.argv[1]), 'videos' if content_type in ['video', 'all'] else 'albums')
        xbmcplugin.endOfDirectory(int(sys.argv[1]), cacheToDisc=False)

    def clear_cache(self):
        if DEBUG:
            self.log('clear_cache()')
        cache.cache_clear()
        xbmcgui.Dialog().notification(_plugin, _language(30201), _icon, 3000, False)

    # --- API COMMUNICATORS ---

    def fetch_archive_metadata(self, query_type, target, filter_map, page, sort_param=None):
        cd = {}
        params = {
            'hits_per_page': 100,
            'page': page,
            'aggregations': 'false',
            'client_url': self.base_url
        }
        
        # Only attach the filter_map if it actually contains valid parameters to prevent HTTP 400 Bad Request errors
        if filter_map and filter_map != '{}':
            params['filter_map'] = filter_map
        
        if query_type == 'search':
            params['service_backend'] = 'metadata'
            params['user_query'] = target
            if sort_param:
                params['sort'] = sort_param
        elif query_type == 'collection':
            params['page_type'] = 'collection_details'
            params['page_target'] = target
            
        resp = client.request(self.search_url, headers=self.headers, params=params)
        
        if resp and isinstance(resp, dict):
            cd = resp.get('response', {}).get('body', {}).get('hits', {})
        return cd

    # --- CORE LISTERS ---

    def list_collections(self, page, content_type):
        search_type = self.parameters('search_type')
        target = 'movies' if content_type == 'video' else 'audio'
        filter_map = '{"mediatype":{"collection":"inc"}}'
        data = cache.get(self.fetch_archive_metadata, cache_duration, 'collection', target, filter_map, page)
        
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
                
                count = fields.get('item_count')
                
                labels = {
                    'title': f"{title} [I]({count:,} items)[/I]",
                    'plot' if content_type in ['video', 'all'] else 'comment': plot
                }
                listitem = self.make_listitem(labels, content_type)
                listitem.setArt({'icon': self.img_path + slug, 'thumb': self.img_path + slug, 'fanart': _fanart})
                listitem.setProperty('IsPlayable', 'false')
                
                ctx_items = [
                    ('Save to Movie Collections', f"RunPlugin({sys.argv[0]}?action=add_favorite_collection&target={slug}&title={urllib.parse.quote(str(title))}&category=movie)"),
                    ('Save to TV Collections', f"RunPlugin({sys.argv[0]}?action=add_favorite_collection&target={slug}&title={urllib.parse.quote(str(title))}&category=tv)"),
                    ('Save to Audio Collections', f"RunPlugin({sys.argv[0]}?action=add_favorite_collection&target={slug}&title={urllib.parse.quote(str(title))}&category=audio)")
                ]
                listitem.addContextMenuItems(ctx_items)
                
                url = f"{sys.argv[0]}?" + urllib.parse.urlencode({
                    'action': 'list_items',
                    'page': 1,
                    'target': slug,
                    'content_type': content_type,
                    'search_type': search_type
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
                    'content_type': content_type,
                    'search_type': search_type
                })
                items_to_add.append((url, listitem, True))

            if items_to_add:
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), items_to_add)

            xbmcplugin.setContent(int(sys.argv[1]), 'videos' if content_type in ['video', 'all'] else 'albums')
            xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
            xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_TITLE)
            xbmcplugin.endOfDirectory(int(sys.argv[1]), cacheToDisc=True)
        else:
            xbmcgui.Dialog().notification(_plugin, "Error retrieving collections.", _icon, 3000, False)
            xbmcplugin.endOfDirectory(int(sys.argv[1]), True)

    def search_collection_menu(self, content_type):
        keyword = urllib.parse.unquote(self.parameters('keyword'))
        page = int(self.parameters('page') or 1)

        if keyword:
            self.execute_collection_search(keyword, page, content_type)
        else:
            keyboard = xbmc.Keyboard()
            keyboard.setHeading("Search Collections")
            keyboard.doModal()
            if keyboard.isConfirmed() and len(keyboard.getText()) > 2:
                search_text = keyboard.getText()
                self._save_history(search_text, content_type, 'collection')
                self.execute_collection_search(search_text, 1, content_type)
            else:
                xbmcplugin.endOfDirectory(int(sys.argv[1]), True)

    def execute_collection_search(self, keyword, page, content_type):
        filter_map = '{"mediatype":{"collection":"inc"}}'
        data = cache.get(self.fetch_archive_metadata, cache_duration, 'search', keyword, filter_map, page)
        
        if data:
            items = data.get('hits', [])
            if not items:
                xbmcgui.Dialog().notification(_plugin, "No collections found.", _icon, 3000, False)
                xbmcplugin.endOfDirectory(int(sys.argv[1]), True)
                return
                
            items_to_add = []
            for item in items:
                fields = item.get('fields', {})
                title = fields.get('title')
                title = title[0] if isinstance(title, list) and title else (title or fields.get('identifier'))
                slug = fields.get('identifier')
                plot = fields.get('description')
                plot = unescape(plot[0] if isinstance(plot, list) and plot else (plot or ''))
                
                listitem = self.make_listitem({'title': f"[COLOR gold]{title}[/COLOR]", 'plot' if content_type in ['video', 'all'] else 'comment': plot}, content_type)
                listitem.setArt({'icon': self.img_path + slug, 'thumb': self.img_path + slug, 'fanart': _fanart})
                listitem.setProperty('IsPlayable', 'false')
                
                ctx_items = [
                    ('Save to Movie Collections', f"RunPlugin({sys.argv[0]}?action=add_favorite_collection&target={slug}&title={urllib.parse.quote(str(title))}&category=movie)"),
                    ('Save to TV Collections', f"RunPlugin({sys.argv[0]}?action=add_favorite_collection&target={slug}&title={urllib.parse.quote(str(title))}&category=tv)"),
                    ('Save to Audio Collections', f"RunPlugin({sys.argv[0]}?action=add_favorite_collection&target={slug}&title={urllib.parse.quote(str(title))}&category=audio)")
                ]
                listitem.addContextMenuItems(ctx_items)
                
                url = f"{sys.argv[0]}?" + urllib.parse.urlencode({
                    'action': 'list_items', 'page': 1, 'target': slug, 'content_type': content_type
                })
                items_to_add.append((url, listitem, True))
                
            if items_to_add:
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), items_to_add)
                
            total = data.get('total', 0)
            if page * 100 < total:
                lastpg = math.ceil(total / 100)
                listitem = self.make_listitem({'title': f"[COLOR lime]{_language(30204)}...[/COLOR] ({page+1}/{lastpg})"}, content_type)
                listitem.setArt({'icon': _icon, 'thumb': _icon, 'fanart': _fanart})
                listitem.setProperty('IsPlayable', 'false')
                
                params = {
                    'action': 'search_collection_menu',
                    'keyword': keyword,
                    'content_type': content_type,
                    'page': page + 1
                }
                url = f"{sys.argv[0]}?" + urllib.parse.urlencode(params)
                items_to_add.append((url, listitem, True))

            xbmcplugin.setContent(int(sys.argv[1]), 'videos' if content_type in ['video', 'all'] else 'albums')
            xbmcplugin.endOfDirectory(int(sys.argv[1]), True)
        else:
            xbmcplugin.endOfDirectory(int(sys.argv[1]), True)

    def list_items(self, target, page, content_type):
        search_type = self.parameters('search_type')
        
        # Enforce an empty string rather than empty brackets to prevent HTTP 400 Bad Request rejection
        filter_map = ''
        
        data = cache.get(self.fetch_archive_metadata, cache_duration, 'collection', target, filter_map, page)
        
        if data:
            items = data.get('hits')
            if not items:
                xbmcgui.Dialog().notification(_plugin, "No playable media found.", _icon, 3000, False)
                xbmcplugin.endOfDirectory(int(sys.argv[1]), True)
                return
                
            items_to_add = []
            for item in items:
                fields = item.get('fields', {})
                
                is_collection = False
                mediatypes = fields.get('mediatype', [])
                if isinstance(mediatypes, list):
                    is_collection = any('collection' in str(m).lower() for m in mediatypes)
                elif isinstance(mediatypes, str):
                    is_collection = 'collection' in mediatypes.lower()
                
                if not is_collection and not self._has_playable_media(fields, content_type): 
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
                    'plot' if content_type in ['video', 'all'] else 'comment': plot
                }
                
                listitem = self.make_listitem(labels, content_type)
                
                if is_collection:
                    listitem.setArt({'icon': 'DefaultFolder.png', 'thumb': 'DefaultFolder.png', 'fanart': _fanart})
                    url = f"{sys.argv[0]}?" + urllib.parse.urlencode({
                        'action': 'list_items',
                        'page': 1,
                        'target': slug,
                        'content_type': content_type,
                        'search_type': search_type
                    })
                else:
                    listitem.setArt({'icon': self.img_path + slug, 'thumb': self.img_path + slug, 'fanart': _fanart})
                    url = f"{sys.argv[0]}?" + urllib.parse.urlencode({
                        'action': 'expand_item',
                        'target': slug,
                        'content_type': content_type,
                        'search_type': search_type
                    })
                
                listitem.setProperty('IsPlayable', 'false')
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
                    'content_type': content_type,
                    'search_type': search_type
                })
                items_to_add.append((url, listitem, True))

            if items_to_add:
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), items_to_add)

            xbmcplugin.setContent(int(sys.argv[1]), 'videos' if content_type in ['video', 'all'] else 'songs')
            xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
            xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_TITLE)
            xbmcplugin.endOfDirectory(int(sys.argv[1]), cacheToDisc=True)
        else:
            xbmcgui.Dialog().notification(_plugin, "Error retrieving items.", _icon, 3000, False)
            xbmcplugin.endOfDirectory(int(sys.argv[1]), True)

    def search(self, content_type):
        search_type = self.parameters('search_type') or 'video'
        prefilled_keyword = urllib.parse.unquote(self.parameters('keyword'))
        
        favs = self._get_favorites()

        if search_type == 'movie':
            base_cols = [(f['title'], f['slug']) for f in favs.get('movie', [])]
            collections = [("None (Search All of Internet Archive)", "none"), ("All Curated Collections", "all")] + base_cols
            heading = "Search Movies"
        elif search_type == 'tv':
            base_cols = [(f['title'], f['slug']) for f in favs.get('tv', [])]
            collections = [("None (Search All of Internet Archive)", "none"), ("All Curated Collections", "all")] + base_cols
            heading = "Search TV Shows"
        elif search_type == 'audio':
            base_cols = [(f['title'], f['slug']) for f in favs.get('audio', [])]
            collections = [("None (Search All of Internet Archive)", "none"), ("All Curated Collections", "all")] + base_cols
            heading = "Search Audio & Music"
        else:
            heading = f"Search {content_type.capitalize()}"
            collections = [("None (Search All of Internet Archive)", "none"), ("All Curated Collections", "all")]
            
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
        
        if auto_select_col:
            if search_type == 'movie':
                collection_str = _settings('default_movie_collection') or 'all'
            elif search_type == 'tv':
                collection_str = _settings('default_tv_collection') or 'all'
            else:
                collection_str = _settings('default_audio_collection') or 'all'
        elif collections:
            col_names = [c[0] for c in collections]
            selected_indices = xbmcgui.Dialog().multiselect("Select Collections", col_names)
            
            if selected_indices is None:
                xbmcplugin.endOfDirectory(int(sys.argv[1]), True)
                return
                
            if not selected_indices:
                collection_str = "all"
            else:
                selected_slugs = [collections[i][1] for i in selected_indices]
                if "none" in selected_slugs:
                    collection_str = "none"
                elif "all" in selected_slugs:
                    collection_str = "all"
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
        
        f_map = {}
        query_string = search_text
        sort_param = None
        
        # 1. Routing Trap Fix & Global Assignment
        if not collection_str:
            if search_type == 'movie':
                collection_str = _settings('default_movie_collection') or 'all'
            elif search_type == 'tv':
                collection_str = _settings('default_tv_collection') or 'all'
            else:
                collection_str = _settings('default_audio_collection') or 'all'
                
        # 2. Collection Injection (Bypassed if not targeted)
        if collection_str == "none":
            pass # Search everything globally, bypassing collection filters entirely
        elif collection_str == "all":
            favs = self._get_favorites()
            cols = [f['slug'] for f in favs.get(search_type, [])]
            if cols:
                f_map["collection"] = {c: "inc" for c in cols}
        elif collection_str != "none":
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
            
        # Ensure we pass an empty string instead of an empty dictionary string if the filter map is blank
        filter_map_json = json.dumps(f_map, separators=(',', ':')) if f_map else ''
            
        data = cache.get(self.fetch_archive_metadata, cache_duration, 'search', query_string, filter_map_json, page, sort_param)
        
        if data:
            items = data.get('hits')
            if not items:
                xbmcgui.Dialog().notification(_plugin, "No media matching format found.", _icon, 3000, False)
                xbmcplugin.endOfDirectory(int(sys.argv[1]), True)
                return
                
            items_to_add = []
            
            for item in items:
                fields = item.get('fields', {})
                
                is_collection = False
                mediatypes = fields.get('mediatype', [])
                if isinstance(mediatypes, list):
                    is_collection = any('collection' in str(m).lower() for m in mediatypes)
                elif isinstance(mediatypes, str):
                    is_collection = 'collection' in mediatypes.lower()
                    
                if not is_collection and not self._has_playable_media(fields, content_type): 
                    continue
                
                if not is_collection and search_type in ['movie', 'tv']:
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
                    'plot' if content_type in ['video', 'all'] else 'comment': plot
                }
                listitem = self.make_listitem(labels, content_type)
                
                if is_collection:
                    listitem.setArt({'icon': 'DefaultFolder.png', 'thumb': 'DefaultFolder.png', 'fanart': _fanart})
                    url = f"{sys.argv[0]}?" + urllib.parse.urlencode({
                        'action': 'list_items',
                        'page': 1,
                        'target': slug,
                        'content_type': content_type,
                        'search_type': search_type
                    })
                else:
                    listitem.setArt({'icon': self.img_path + slug, 'thumb': self.img_path + slug, 'fanart': _fanart})
                    url = f"{sys.argv[0]}?" + urllib.parse.urlencode({
                        'action': 'expand_item',
                        'target': slug,
                        'content_type': content_type,
                        'search_type': search_type
                    })
                
                listitem.setProperty('IsPlayable', 'false')
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

            xbmcplugin.setContent(int(sys.argv[1]), 'videos' if content_type in ['video', 'all'] else 'songs')
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
        search_type = self.parameters('search_type')
        api_url = f"{self.base_url}metadata/{item_id}"
        jd = cache.get(client.request, cache_duration, api_url)

        if not isinstance(jd, dict) or 'files' not in jd:
            xbmcgui.Dialog().notification(_plugin, "No playable media found.", _icon, 3000, False)
            xbmcplugin.endOfDirectory(int(sys.argv[1]), True)
            return

        if content_type == 'video':
            valid_exts = self.video_exts
        elif content_type == 'audio':
            valid_exts = self.audio_exts
        else:
            valid_exts = self.video_exts + self.audio_exts

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
            time_pos = 0.0
            if res_key in res_data:
                display_title = f"{display_title} [I](Resume)[/I]"
                time_pos = res_data[res_key].get('time', 0.0)
            
            listitem = self.make_listitem({'title': display_title}, content_type)
            listitem.setArt({'fanart': _fanart})
            listitem.setProperty('IsPlayable', 'true')
            
            if time_pos > 0:
                if _kodiver >= 20.0 and content_type in ['video', 'all']:
                    listitem.getVideoInfoTag().setResumePoint(float(time_pos))
                else:
                    listitem.setProperty('resumetime', str(time_pos))
            
            url = f"{sys.argv[0]}?" + urllib.parse.urlencode({
                'action': 'play_video',
                'target': item_id,
                'ep_tag': tag,
                'content_type': content_type,
                'search_type': search_type
            })
            items_to_add.append((url, listitem, False))
            
        if items_to_add:
            xbmcplugin.addDirectoryItems(int(sys.argv[1]), items_to_add)
            
        xbmcplugin.setContent(int(sys.argv[1]), 'videos' if content_type in ['video', 'all'] else 'songs')
        xbmcplugin.endOfDirectory(int(sys.argv[1]), cacheToDisc=False)

    def play_video(self, item_id, content_type):
        ep_tag = self.parameters('ep_tag')
        search_type = self.parameters('search_type')
        
        # Determine if Kodi is auto-advancing in the background or if we triggered our internal queue
        is_background = self.parameters('queue') == '0'
        try:
            if xbmc.Player().isPlaying():
                is_background = True
        except Exception:
            pass
        
        # When queue=0 it means Kodi's playlist is automatically playing this next background item.
        auto_play_setting = _settings('auto_play_queue') != 'false'
        
        # Do not manually queue if this originated from a movie search or if we are already in the background
        do_queue = not is_background and auto_play_setting and search_type != 'movie'

        # Access Kodi's Home Window to store/retrieve persistent session properties for native auto-advancing
        window = xbmcgui.Window(10000)

        # Extract playback memory (if queued by background playlist OR native Kodi auto-advance)
        pref_ext = self.parameters('pref_ext') or window.getProperty('ia_pref_ext')
        pref_height = self.parameters('pref_height') or window.getProperty('ia_pref_height')
        pref_source = self.parameters('pref_source') or window.getProperty('ia_pref_source')

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

        if content_type == 'video':
            valid_exts = self.video_exts
        elif content_type == 'audio':
            valid_exts = self.audio_exts
        else:
            valid_exts = self.video_exts + self.audio_exts

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
            if content_type in ['video', 'all']:
                target_files.sort(key=lambda i: (self._safe_int(i.get('height')), i.get('source', ''), self._safe_int(i.get('size'))), reverse=True)
            else:
                target_files.sort(key=lambda i: self._safe_int(i.get('size')), reverse=True)

            # If an automated playlist queue is playing, force exact match to previous video settings WITHOUT throwing Dialog Menu
            if is_background and pref_ext:
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
                if content_type in ['video', 'all'] and max_res < 99999:
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
                    
                    if content_type == 'video' or (content_type == 'all' and f".{ext.lower()}" in self.video_exts):
                        height = self._safe_int(i.get('height'))
                        res = f"{height}p" if height > 0 else "Unknown Res"
                        srcs.append(f"[{ext}] {res} | {size} | {source}")
                    else:
                        srcs.append(f"[{ext}] {size} | {source}")
                    
                ret = xbmcgui.Dialog().select(_language(30203) if _language(30203) else "Select Stream", srcs)
                if ret == -1:
                    xbmcplugin.setResolvedUrl(int(sys.argv[1]), False, listitem=xbmcgui.ListItem())
                    return
                
                # Pull the user's manual selection to the front of the list to prioritize it in the fallback loop
                selected_file = target_files.pop(ret)
                target_files.insert(0, selected_file)
                
                # Save the explicit manual selection to Window memory for native Kodi auto-advancing
                window.setProperty('ia_pref_ext', selected_file.get('name', '').split('.')[-1].lower())
                window.setProperty('ia_pref_height', str(selected_file.get('height', '')))
                window.setProperty('ia_pref_source', str(selected_file.get('source', '')).lower())
        else:
            selected_file = target_files[0]
            # Save format memory even if it was the only option, so the next episode matches it
            window.setProperty('ia_pref_ext', selected_file.get('name', '').split('.')[-1].lower())
            window.setProperty('ia_pref_height', str(selected_file.get('height', '')))
            window.setProperty('ia_pref_source', str(selected_file.get('source', '')).lower())

        # --- DERIVATIVE FALLBACK LOOP & SERVER CHECK ---
        successful_file = None
        successful_surl = ""

        # Iterate through the sorted target files (prioritizing the chosen/best match format)
        for candidate_file in target_files:
            node = random.choice(workable_servers)
            test_surl = f"https://{node}{item_dir}/{urllib.parse.quote(candidate_file.get('name', ''), safe='/')}"
            
            try:
                # 3-second strict timeout to fast-fail dead Archive.org nodes
                req = urllib.request.Request(test_surl, method='HEAD')
                urllib.request.urlopen(req, timeout=3.0)
                
                # If we get here, the node is alive and the file exists
                successful_file = candidate_file
                successful_surl = test_surl
                break 
            except Exception as e:
                if DEBUG:
                    self.log(f"Server dead/unresponsive for derivative format ({test_surl}): {str(e)}")
                continue # Catch exception and seamlessly try the next format derivative in the list

        if not successful_file:
            xbmcgui.Dialog().notification(_plugin, "All stream derivatives unresponsive. Skipping.", _icon, 3000, False)
            xbmcplugin.setResolvedUrl(int(sys.argv[1]), False, listitem=xbmcgui.ListItem())
            return

        # Re-assign the confirmed working file as our selected file
        selected_file = successful_file
        
        # Explicitly disable queue generation if the final working file is a DVD ISO
        if selected_file.get('name', '').lower().endswith('.iso'):
            do_queue = False

        # Apply cURL pipe injection for persistent connections, extended timeout, and transparent User-Agent spoofing to bypass throttling
        final_surl = f"{successful_surl}|Connection=keep-alive&Timeout=60&User-Agent=Kodi-InternetArchiveTheater-Addon (Contact: https://github.com/PythonTrousers)"

        li = self.make_listitem({'title': resume_title}, content_type)
        li.setArt({'fanart': _fanart})
        li.setPath(final_surl)
        
        # Explicitly suppress Kodi's network probe and manually set MIME type ONLY for DVD ISOs
        # This allows native HTTP header probing for standard media to bypass FFmpeg deep-probe lag
        if selected_file.get('name', '').lower().endswith('.iso'):
            if hasattr(li, 'setContentLookup'):
                li.setContentLookup(False)
            li.setProperty('VideoPlayer.ContentLookup', 'false')
            if hasattr(li, 'setMimeType'):
                li.setMimeType('application/x-iso9660-image')
            else:
                li.setProperty('mimetype', 'application/x-iso9660-image')
        
        # Intercept and process local resume data before handoff to prevent double-initialization
        res_data = self._get_resume()
        res_key = f"{item_id}_{ep_tag}"
        if res_key in res_data:
            time_pos = res_data[res_key].get('time', 0.0)
            if time_pos > 0:
                if _kodiver >= 20.0 and content_type in ['video', 'all']:
                    li.getVideoInfoTag().setResumePoint(float(time_pos))
                else:
                    li.setProperty('resumetime', str(time_pos))

        # Initialize the event-driven custom player instance
        player = IATPlayer(item_id, ep_tag, resume_title, content_type, search_type, self)
        
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
                playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO if content_type in ['video', 'all'] else xbmc.PLAYLIST_MUSIC)
                for r_tag in remaining_tags:
                    q_url = f"{sys.argv[0]}?" + urllib.parse.urlencode({
                        'action': 'play_video',
                        'target': item_id,
                        'ep_tag': r_tag,
                        'content_type': content_type,
                        'search_type': search_type,
                        'queue': '0', 
                        'pref_ext': sel_ext,       # Queue inherits your format choice
                        'pref_height': sel_height, # Queue inherits your res choice
                        'pref_source': sel_source  # Queue inherits your source choice
                    })
                    q_li = self.make_listitem({'title': r_tag}, content_type)
                    q_li.setArt({'fanart': _fanart})
                    playlist.add(url=q_url, listitem=q_li)

        # Main-Thread Tracking Loop Integration (Replaces dead background t2 thread)
        if content_type in ['video', 'all']:
            monitor = xbmc.Monitor()
            # Suspend the script for 2 seconds to allow the player to fully initialize before starting playback state assertions
            monitor.waitForAbort(2.0)
            cleared_threshold = False
            
            while player.is_active and not monitor.abortRequested():
                try:
                    if player.isPlaying():
                        time_pos = player.getTime()
                        total = player.getTotalTime()
                        
                        if total > 0:
                            pct = time_pos / total
                            
                            # Keep track of time for early stops
                            if 0.01 < pct < 0.95:
                                player.last_known_time = time_pos
                                
                            # Proactive 95% threshold clearing before Native auto-advance destroys the player class
                            elif pct >= 0.95 and not cleared_threshold:
                                player.last_known_time = 0.0
                                self._remove_resume(item_id, ep_tag)
                                cleared_threshold = True
                    else:
                        # Player object transitioned via manual playlist forward without firing explicit stop
                        break
                except Exception:
                    # Player was destroyed natively by Kodi
                    break
                    
                # Suspend main thread to yield CPU to Kodi while keeping script variables alive
                monitor.waitForAbort(1.0)
            
            player.is_active = False

    def parameters(self, arg):
        val = self.args.get(arg, '')
        if isinstance(val, list):
            val = val[0]
        return val

    def make_listitem(self, labels, content_type):
        title_str = str(labels.get('title') or '')
        li = xbmcgui.ListItem(title_str)
        if _kodiver >= 20.0:
            if content_type in ['video', 'all']:
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
            li.setInfo(type='video' if content_type in ['video', 'all'] else 'music', infoLabels=labels)

        return li

    def log(self, description):
        xbmc.log(f"[ADD-ON] '{_plugin} v{_version}': {description}", xbmc.LOGINFO)

if __name__ == '__main__':
    Main()
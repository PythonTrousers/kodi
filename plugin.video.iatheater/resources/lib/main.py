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
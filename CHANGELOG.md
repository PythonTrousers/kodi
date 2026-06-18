# Patch Notes & Changelog

## [0.3.0] - 2026-06-17
### Internet Archive Theater (IAT) Major Update
Version 0.3.0 implements major structural refactors, a brand-new collection search system, intelligent server routing, and comprehensive local storage capabilities. 

**UI & Feature Additions**
* **Collection Search:** 
  * Replaced the generic "Search All Videos" menu route.
  * Added dynamic "Search Collections" and "Favorite Collections" targets.
* **Favorite Collections System:** 
  * Implemented local JSON data management.
  * Enables users to save custom curations for quick access.
* **Smart Search Routing:** 
  * Dynamically populates the UI selection array from class properties and user favorites.
  * Integrated "None" wildcard and "All Curated Collections" options.
* **Collection History:** 
  * Added conditional routing to `list_history`.
  * Correctly identifies and relaunches successfully saved "collection" searches.

**Playback & Networking Optimizations**
* **Intelligent Server Fallback:** 
  * Integrated a 3-second `urllib.request` node fallback loop.
  * Gracefully skips dead Archive.org servers before crashing the stream.
* **Continuous Playlist Memory:** 
  * Playlist queues now actively inherit your specific settings.
  * Locks in `pref_ext`, `pref_height`, and `pref_source` for flawless auto-advancing.
* **DVD ISO Special Handling:** 
  * Added `.iso` support to audio arrays.
  * Explicitly disabled automated queue generation for ISO targets to prevent UI lockups.
  * Disabled Kodi `ContentLookup` and set explicit MIME types for rapid ISO parsing.
* **Proxy Headers:** 
  * Appended strict `User-Agent` and `Keep-Alive` proxy headers to backend requests.
  * Effectively bypasses persistent backend throttling limitations.

**Under-the-Hood Structural Fixes**
* **Class Migration:** 
  * Migrated static collection definitions (`cat_video`, `cat_movie`, etc.).
  * Integrated directly into `__init__` class properties for global access.
* **API Communicator:** 
  * Created a unified `fetch_archive_metadata` handler.
  * Actively prevents `HTTP 400` errors by safely stripping empty `filter_map` parameters.
* **Math Fix:** 
  * Corrected a loop indentation bug inside `format_bytes`.
  * Accurately calculates and stringifies MB/GB file sizes in the UI.

## Repository Generator Tools
### Build Script Updates (`_generator.py`)
* **Automated Cleanups:** 
  * Updated `create_zip` and `sync_root_zip` functions.
  * Dynamically sweeps directories and deletes pre-existing `.zip` files before packaging.
  * Ensures only the current iteration dictated by `addon.xml` is maintained.

---

## [0.2.2 & 0.2.3] - Hotfixes - 2026-06-16
### Playback & Search Stability Updates
* **Playlist Stability (0.2.2):**
  * Removed background threading for playlist generation in `play_video`.
  * Executing synchronously prevents concurrent `busydialogs` crashes in Kodi during track transitions.
* **Search Fixes (0.2.3):**
  * Fixed collection string slicing typo within the `search_word` function.
  * Removed `downloads desc` sorting parameter to resolve image server timeouts.

---

## [0.2.1] - 2026-06-16
### Routing & UI Adjustments
* **Search Routing:** Fixed general video search routing trap.
* **Sorting Logic:** Implemented hybrid relevance sorting.
* **UI Bypass:** Added "None" global bypass option to collection dialogs.

---

## [0.2.0 Beta] - 2026-06-16
### Initial Launch & Repository Infrastructure
Initial commit of Internet Archive Theater (IAT) and the master PythonTrousers distribution hub.

**Repository Infrastructure Initialization**
* **Root Scraping:** Added `index.html` and moved the repository installation zip to the root directory to bypass Kodi subdirectory scraping limitations.
* **URL Routing:** Switched internal polling URLs to `raw.githubusercontent.com` to bypass GitHub Pages HTML caching issues.
* **Generator Automation:** Updated `_generator.py` to automate root zip synchronization.
* **Parser Fixes:** Replaced invalid NBSP whitespace characters in `addon.xml` with standard ASCII spaces to prevent Kodi parser crashes.

**Documentation Updates**
* **README Overhaul:** Established repository documentation and troubleshooting guides.
* **Navigation Fixes:** Hardcoded explicit HTML anchors to bypass GitHub's automatic link generation and fix broken Table of Contents navigation.
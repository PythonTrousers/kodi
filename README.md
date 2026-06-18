# PythonTrousers Kodi Repository

Welcome to the official Kodi repository for PythonTrousers. This repository hosts custom media plugins and applications, built with a focus on clean architecture, optimized playback, and open-source accessibility.

## 🗂️ Table of Contents
* [About This Repository](#about)
* [AI Transparency Statement](#ai)
* [Available Add-ons](#addons)
* [Internet Archive Theater (IAT)](#iat)
  * [Features & Additions](#features)
  * [Under-the-Hood Optimizations](#optimizations)
* [How to Install](#install)
* [User Guide & Tutorial](#tutorial)
* [Troubleshooting & Fixes](#troubleshooting)
* [For Developers: Repository Architecture](#developers)
* [Patch Notes & Changelog](CHANGELOG.md)

---

## <a id="about"></a>ℹ️ About This Repository
This repository serves as the central distribution hub for current and future Kodi addons developed by PythonTrousers. It utilizes a zero-configuration raw backend delivery system, allowing seamless updates directly to your Kodi devices.

## <a id="ai"></a>🤖 AI Transparency Statement
In the spirit of open-source transparency, please note that the addons in this repository utilize generative AI assistance during development. AI tools are used to assist with code formatting, logic rewrites, architectural structuring, and debugging, ensuring faster deployment and highly optimized scripts.

---

## <a id="addons"></a>📦 Available Add-ons

### <a id="iat"></a>Internet Archive Theater (v0.3.0)
**Internet Archive Theater (IAT)** is a dedicated video and audio plugin designed to interface with the Internet Archive. It provides a highly optimized, structured viewing experience for public domain and archived media directly within Kodi.

*Note: This addon is a massive, heavily modified fork and spiritual successor to the original `plugin.video.archive.org` by gujal. Because the original addon was abandoned and broken by API changes, IAT was built from the ground up as a standalone app with entirely rewritten logic, custom UI flows, and expanded playback capabilities.*

#### <a id="features"></a>Features & Additions
* **Continue Watching (Resume Data):** Added custom local JSON tracking to remember where you left off in a video, accessible via a dedicated menu.
* **Search History Tracking:** Your recent searches are now locally saved, making it easy to jump back into a previous query without retyping.
* **Granular Search Categories:** Replaced the old "Search All" with specific searches for Movies, TV Shows, and Audio, which intelligently target specific Internet Archive collections.
* **Curated Collection Shortcuts:** Added built-in shortcuts to popular media hubs (e.g., The VHS Vault, DVD Tray, Laserdisc Archive, Classic TV, etc.).
* **Favorite Collections:** Save custom Archive collections to a local favorites list for quick access. 
* **Collection Search:** A dedicated search route to discover and browse user-curated collections globally across the Internet Archive.
* **Binge-Watching / Auto-Play Queue:** Added a threaded background tracker that automatically queues up the next episode or track in a playlist sequence.
* **Smart Stream Selection:** Replaced raw file dumps with a clean selection menu. The addon now extracts and displays resolution, file size, and source format.
* **Expanded Settings UI:** A massive settings overhaul allows you to set preferred video/audio formats, cap maximum resolutions, enable/disable auto-play, and configure manual or automatic collection overrides.
* **Custom Visuals:** Added a native Kodi splash screen on startup to improve the aesthetic experience.

#### <a id="optimizations"></a>Under-the-Hood Optimizations
* **Strict Media Filtering:** Advanced regex and extension filtering automatically removes unplayable files, text documents, and junk data from your search results.
* **Smart Duration Parsing:** The new logic parses runtimes to automatically filter out promos, short clips, and trailers (e.g., hiding videos under 45 minutes when searching for "Movies").
* **cURL Pipe Injection:** Streaming URLs are now injected with `|Connection=keep-alive&Timeout=60` to enforce persistent connections and prevent arbitrary dropouts. They also utilize transparent User-Agent spoofing to bypass backend throttling.
* **Intelligent Server Routing:** Integrated a 3-second network fallback loop to intelligently bypass dead or unresponsive Archive.org data servers before stream failures occur.
* **Continuous Memory Inheritance:** Playlist queues automatically inherit your specific format, resolution, and source preferences to ensure seamless auto-advancing across episodes.
* **DVD ISO Playback Optimization:** Explicitly sets the MIME type to `application/x-iso9660-image` and disables Kodi's internal network probe on ISO files, completely eliminating pre-buffer freezing. Automated playlist queueing is explicitly disabled for ISO targets.
* **Episode Identification Regex:** The addon uses pre-compiled regex parameters to parse standard TV episode formats (e.g., S01E02) out of chaotic raw filenames.
* **Performance Enhancements:** Migrated to modern f-strings, implemented safe Kodi version parsing via the official API, and heavily optimized the local cache retrieval logic.

---

## <a id="install"></a>⚙️ How to Install

To install this repository and access the add-ons on your Kodi device (Raspberry Pi, Android, PC, etc.), follow these steps:

1. Open Kodi and navigate to the **Settings** gear icon.
2. Open **File Manager** and select **Add source**.
3. Click on `<None>` and enter the following URL exactly:
   `https://pythontrousers.github.io/kodi/`
4. Name the media source **PythonTrousers** and click **OK**.
5. Return to the Kodi home screen, click **Add-ons**, and click the open box icon at the top left.
6. Select **Install from zip file** *(If prompted, enable "Unknown sources" in your settings)*.
7. Select **PythonTrousers**, then click on the `repository.pythontrousers` folder, and select the `repository.pythontrousers-0.3.0.zip` file.
8. Once the repository installed notification appears, select **Install from repository**.
9. Select **PythonTrousers Repository** -> **Video add-ons** -> **Internet Archive Theater** and hit **Install**.

---

## <a id="tutorial"></a>📖 User Guide & Tutorial

Internet Archive Theater (IAT) offers a robust set of features to navigate the massive library of the Internet Archive. Here is how to get the most out of the addon:

### Navigating Categories & Shortcuts
Instead of sifting through raw data, use the dedicated **Movies**, **TV Shows**, and **Audio** hubs on the main menu. These hubs contain built-in shortcuts to highly curated, popular Archive vaults (like *The VHS Vault*, *Classic TV*, and *The Live Music Archive*), instantly filtering out irrelevant text and image files.

### Mastering the Search System
The search functionality has been completely rewritten for precision:
* **Granular Searching:** Searching within a specific hub (e.g., Movies) will automatically restrict results to video files and apply duration filters to hide short clips.
* **Global Collection Search:** Use the **Search Collections** route on the main menu to look for specific user-curated vaults across the entire Internet Archive.
* **The "None" Wildcard:** When prompted to select a collection to search within, choosing **None (Global Bypass)** will strip all filters and search the entire Archive database for your keyword.

### Managing Favorite Collections
If you find a specific Archive collection you love, you can save it locally to your Kodi device:
1. Highlight any collection folder or search result.
2. Open the Kodi Context Menu (usually 'C' on a keyboard, or long-press on a remote).
3. Select **Save to Favorite Collections**.
4. Access your saved curations anytime via the **Favorite Collections** route on the main menu.

### Playback, Queues, & Auto-Play
IAT is designed for seamless binge-watching:
* **Smart Stream Selection:** When you click a video, you will be prompted to select your preferred resolution and format (e.g., 1080p MP4 vs. original source). 
* **Auto-Play Tracking:** The addon runs a background tracker. If you are watching a playlist or an episodic collection, it will automatically inherit your quality preferences and queue up the next track perfectly. *(Note: Queueing is automatically disabled for DVD ISO files).*
* **Continue Watching:** The addon locally logs your playback history. Access the **Continue Watching** menu to instantly resume videos from exactly where you left off.

### Configuring Settings
Customize your viewing experience by opening the Add-on Settings menu:
* **Playback Preferences:** Hardcode your preferred video/audio formats and set a maximum resolution cap (great for slower network connections).
* **Auto-Play Toggles:** Enable or disable the automated playlist queueing system.
* **Collection Overrides:** Configure manual or automatic routing for specific data hubs.

---

## <a id="troubleshooting"></a>🔧 Troubleshooting & Fixes

### Stuttering, Freezing, or Tracking Issues (Disabling HTTP2)
Newer versions of Kodi (v19 Matrix and above) utilize HTTP2 by default for network connections. While generally beneficial, HTTP2 can cause severe stuttering, freezing, and playback tracking issues when streaming large files from specific backend servers like the Internet Archive.

If you are experiencing buffering loops or the addon fails to track your resume points, **disabling HTTP2 in Kodi** is the recommended fix.

**How to disable HTTP2:**
1. Locate your Kodi `userdata` folder. The location depends on your operating system:
   * **Windows:** `%APPDATA%\Kodi\userdata`
   * **Linux / Raspberry Pi:** `~/.kodi/userdata/`
   * **Android:** `Android/data/org.xbmc.kodi/files/.kodi/userdata/`
   * **macOS:** `~/Library/Application Support/Kodi/userdata/`
2. Look for a file named `advancedsettings.xml`. If it does not exist, create a new text document and name it `advancedsettings.xml`.
3. Open the file in any text editor and add the following code:
```xml
<advancedsettings>
    <network>
        <disablehttp2>true</disablehttp2>
    </network>
</advancedsettings>
```
   *(Note: If you already have an `advancedsettings.xml` file, simply add the `<network>` block inside your existing `<advancedsettings>` tags).*
4. Save the file and **restart Kodi**. Your streams should now initialize via standard HTTP/1.1, resolving the stuttering.

---

## <a id="developers"></a>🛠 For Developers: Repository Architecture

This repository uses a zero-configuration raw backend delivery system managed by a local build script. 

To publish updates or add new plugins:
1. Update your plugin's code and iterate the version number in its `addon.xml`.
2. Run `python _generator.py` from the root directory. This script will automatically:
   * Sweep the target directory and permanently delete any obsolete `.zip` archives to prevent version conflicts.
   * Package the new plugin release into standard Kodi `.zip` formats.
   * Rebuild the master `addons.xml` index.
   * Generate a new `addons.xml.md5` checksum hash.
3. Commit and push the changes to the `main` branch. GitHub Pages will automatically serve the updated index to Kodi clients.
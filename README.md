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

### <a id="iat"></a>Internet Archive Theater (v0.3.1)
**Internet Archive Theater (IAT)** is a dedicated video and audio plugin designed to interface with the Internet Archive. It provides a highly optimized, structured viewing experience for public domain and archived media directly within Kodi.

*Note: This addon is a massive, heavily modified fork and spiritual successor to the original `plugin.video.archive.org` by gujal. Because the original addon was abandoned and broken by API changes, IAT was built from the ground up as a standalone app with entirely rewritten logic, custom UI flows, and expanded playback capabilities.*

#### <a id="features"></a>Features & Additions
* **Continue Watching (Resume Data):** Added custom local JSON tracking to remember where you left off in a video. Seamlessly integrates with Kodi's native UI to prompt you to resume or restart upon selection.
* **Search History Tracking:** Your recent searches are now locally saved, making it easy to jump back into a previous query without retyping.
* **Granular Search Categories:** Replaced the old "Search All" with specific searches for Movies, TV Shows, and Audio, which intelligently target specific Internet Archive collections.
* **Curated Collection Shortcuts:** Added built-in shortcuts to popular media hubs (e.g., The VHS Vault, DVD Tray, Laserdisc Archive, Classic TV, etc.).
* **Favorite Collections Subfolders:** Save custom Archive collections to a local favorites list. Your saved vaults are now automatically organized into distinct Movie, TV, and Audio subfolders to prevent clutter.
* **Collection Search:** A dedicated search route to discover and browse user-curated collections globally across the Internet Archive.
* **Binge-Watching / Auto-Play Queue:** Added a threaded background tracker that automatically queues up the next episode or track in a playlist sequence.
* **Smart Stream Selection:** Replaced raw file dumps with a clean selection menu. The addon now extracts and displays resolution, file size, and source format.
* **Expanded Settings UI:** A massive settings overhaul allows you to set preferred video/audio formats, cap maximum resolutions, enable/disable auto-play, and easily restore your collections back to their default factory settings. 
* **Custom Visuals:** Added a native Kodi splash screen on startup to improve the aesthetic experience.

#### <a id="optimizations"></a>Under-the-Hood Optimizations
* **Strict Media Filtering:** Advanced regex and extension filtering automatically removes unplayable files, text documents, and junk data from your search results.
* **Smart Duration Parsing:** The new logic parses runtimes to automatically filter out promos, short clips, and trailers (e.g., hiding videos under 45 minutes when searching for "Movies").
* **cURL Pipe Injection:** Streaming URLs are now injected with `|Connection=keep-alive&Timeout=60` to enforce persistent connections and prevent arbitrary dropouts. They also utilize transparent User-Agent spoofing to bypass backend throttling.
* **Intelligent Server Routing:** Integrated a 3-second network fallback loop to intelligently bypass dead or unresponsive Archive.org data servers before stream failures occur.
* **Continuous Memory Inheritance:** Playlist queues automatically inherit your specific format, resolution, and source preferences to ensure seamless auto-advancing across episodes.
* **Native Resume Support:** Utilizes modern `InfoTagVideo` metadata tags to bypass forced starts and organically trigger Kodi's built-in "Resume" dialog prompts in v20+. 
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
7. Select **PythonTrousers** and then select the `repository.pythontrousers-0.x.x.zip` file.
8. Once the repository installed notification appears, select **Install from repository**.
9. Select **PythonTrousers Repository** -> **Video add-ons** -> **Internet Archive Theater** and hit **Install**.

---

## <a id="tutorial"></a>📖 User Guide & Tutorial

Internet Archive Theater (IAT) offers a robust set of features to navigate the massive library of the Internet Archive. Here is a breakdown of how to use the addon effectively:

### 1. Main Menu Breakdown
The main menu is your starting point and is divided into specific functional routes:
* **Continue Watching:** Access your locally saved resume points to instantly pick up videos exactly where you left off.
* **Search Movies, TV Shows, Audio:** These are dedicated search tools curated to find your specified media. 
* **Search Collections:** A dedicated search tool used strictly to find user-created metadata vaults (Collections) across the entire Archive.
* **Favorite Collections:** A quick-access hub containing any collections you have manually saved, sorted cleanly into specific media categories.

### 2. Finding & Favoriting Collections
The Internet Archive is built on "Collections" (folders containing specific types of media). 
* **Searching for Collections:** Select the **Search Collections** option from the main menu to look for specific themes or curators (e.g., searching "Laserdisc" will return vaults specifically dedicated to laserdisc rips). You can also browse the popular collections section.
* **Favoriting Collections:** Once you find a collection you want to keep track of, highlight it, open the Kodi Context Menu (usually 'C' on a keyboard, or long-press the 'OK' button on a remote), and choose to save it to your Movie, TV, or Audio Collections. This sends the collection to its respective subfolder in your favorites for permanent quick access. 

### 3. Search Optimization
To get the absolute best results when searching for specific media files:
* **Contextual Searching:** Always initiate your search from within the relevant hub. Searching for a film inside the **Movies** hub will automatically filter out text files, images, and audio tracks, and will apply duration logic to hide short promo clips.
* **Targeting specific Vaults:** When you initiate a keyword search, the addon will ask you which collection you want to search inside. Any collection you have saved to your "Favorite Collections" for that corresponding category will automatically populate in this selection menu. This allows you to specifically search for a movie *only* within your custom high-quality vaults.
* **The Global Bypass:** If you cannot find what you are looking for in the curated lists, select the **None (Global Bypass)** option when asked where to search. This completely strips all specified collections and searches the entire Internet Archive database for your keyword.

### 4. Configuring Settings
You can fine-tune the addon's performance to match your hardware and network speed by opening the Add-on Settings:
* **Playback Preferences:** Hardcode your preferred video and audio formats (e.g., MP4 vs. MKV). You can also set a maximum resolution cap (like 720p or 1080p), which is highly recommended for slower internet connections.
* **Default Collections:** Choose to default your searches to either the Global Bypass (None) or All Curated Collections for Movies, TV Shows, and Audio.
* **Auto-Play Next Episode/Track:** Toggle the background playlist queueing system on or off. When enabled, the addon will automatically track your quality preferences based on the first file selected and continuously play the next episode or track in a list.
* **Auto-Select Best Stream:** Toggle to automatically select your preferred file format. Playback will fallback to the next available format if the preferred format is unavailable. 
* **Auto-Select Search Collection:** Toggle to bypass the collections selection menu when searching. The addon will instead automatically route your query to your designated Default Collections.
* **Maintenance & Debugging:** Adjust network timeout limits, clear the addon's local cache, restore your collections to default settings, or enable debug logging for troubleshooting.

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
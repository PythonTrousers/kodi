# PythonTrousers Kodi Repository

Welcome to the official Kodi repository for PythonTrousers. This repository hosts custom media plugins and applications, built with a focus on clean architecture, optimized playback, and open-source accessibility.

## 🗂️ Table of Contents
* [About This Repository](#-about-this-repository)
* [AI Transparency Statement](#-ai-transparency-statement)
* [Available Add-ons](#-available-add-ons)
* [Internet Archive Theater (IAT)](#internet-archive-theater-iat)
  * [Features & Additions](#features--additions)
  * [Under-the-Hood Optimizations](#under-the-hood-optimizations)
* [How to Install](#-how-to-install)
* [Troubleshooting & Fixes](#-troubleshooting--fixes)
* [For Developers: Repository Architecture](#-for-developers-repository-architecture)

---

## ℹ️ About This Repository
This repository serves as the central distribution hub for current and future Kodi addons developed by PythonTrousers. It utilizes a zero-configuration raw backend delivery system, allowing seamless updates directly to your Kodi devices.

## 🤖 AI Transparency Statement
In the spirit of open-source transparency, please note that the addons in this repository utilize generative AI assistance during development. AI tools are used to assist with code formatting, logic rewrites, architectural structuring, and debugging, ensuring faster deployment and highly optimized scripts.

---

## 📦 Available Add-ons

### Internet Archive Theater (v0.2.0 Beta)
**Internet Archive Theater (IAT)** is a dedicated video and audio plugin designed to interface with the Internet Archive. It provides a highly optimized, structured viewing experience for public domain and archived media directly within Kodi.

*Note: This addon is a massive, heavily modified fork and spiritual successor to the original `plugin.video.archive.org` by gujal. Because the original addon was abandoned and broken by API changes, IAT was built from the ground up as a standalone app with entirely rewritten logic, custom UI flows, and expanded playback capabilities.*

#### Features & Additions
* **Continue Watching (Resume Data):** Added custom local JSON tracking to remember where you left off in a video, accessible via a dedicated menu.
* **Search History Tracking:** Your recent searches are now locally saved, making it easy to jump back into a previous query without retyping.
* **Granular Search Categories:** Replaced the old "Search All" with specific searches for Movies, TV Shows, and Audio, which intelligently target specific Internet Archive collections.
* **Curated Collection Shortcuts:** Added built-in shortcuts to popular media hubs (e.g., The VHS Vault, DVD Tray, Laserdisc Archive, Classic TV, etc.).
* **Binge-Watching / Auto-Play Queue:** Added a threaded background tracker that automatically queues up the next episode or track in a playlist sequence.
* **Smart Stream Selection:** Replaced raw file dumps with a clean selection menu. The addon now extracts and displays resolution, file size, and source format.
* **Expanded Settings UI:** A massive settings overhaul allows you to set preferred video/audio formats, cap maximum resolutions, enable/disable auto-play, and configure manual or automatic collection overrides.
* **Custom Visuals:** Added a native Kodi splash screen on startup to improve the aesthetic experience.

#### Under-the-Hood Optimizations
* **Strict Media Filtering:** Advanced regex and extension filtering automatically removes unplayable files, text documents, and junk data from your search results.
* **Smart Duration Parsing:** The new logic parses runtimes to automatically filter out promos, short clips, and trailers (e.g., hiding videos under 45 minutes when searching for "Movies").
* **cURL Pipe Injection:** Streaming URLs are now injected with `|Connection=keep-alive&Timeout=60` to enforce persistent connections and prevent arbitrary dropouts.
* **DVD ISO Playback Optimization:** Explicitly sets the MIME type to `application/x-iso9660-image` and disables Kodi's internal network probe on ISO files, completely eliminating pre-buffer freezing.
* **Episode Identification Regex:** The addon now uses pre-compiled regex parameters to parse standard TV episode formats (e.g., S01E02) out of chaotic raw filenames.
* **Performance Enhancements:** Migrated to modern f-strings, implemented safe Kodi version parsing via the official API, and heavily optimized the local cache retrieval logic.

---

## ⚙️ How to Install

To install this repository and access the add-ons on your Kodi device (Raspberry Pi, Android, PC, etc.), follow these steps:

1. Open Kodi and navigate to the **Settings** gear icon.
2. Open **File Manager** and select **Add source**.
3. Click on `<None>` and enter the following URL exactly:
   `https://pythontrousers.github.io/kodi/`
4. Name the media source **PythonTrousers** and click **OK**.
5. Return to the Kodi home screen, click **Add-ons**, and click the open box icon at the top left.
6. Select **Install from zip file** *(If prompted, enable "Unknown sources" in your settings)*.
7. Select **PythonTrousers**, then click on the `repository.pythontrousers` folder, and select the `repository.pythontrousers-0.2.0.zip` file.
8. Once the repository installed notification appears, select **Install from repository**.
9. Select **PythonTrousers Repository** -> **Video add-ons** -> **Internet Archive Theater** and hit **Install**.

---

## 🔧 Troubleshooting & Fixes

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

## 🛠 For Developers: Repository Architecture

This repository uses a zero-configuration raw backend delivery system managed by a local build script. 

To publish updates or add new plugins:
1. Update your plugin's code and iterate the version number in its `addon.xml`.
2. Run `python _generator.py` from the root directory. This script will automatically:
   * Package the new plugin release into standard Kodi `.zip` formats.
   * Rebuild the master `addons.xml` index.
   * Generate a new `addons.xml.md5` checksum hash.
3. Commit and push the changes to the `main` branch. GitHub Pages will automatically serve the updated index to Kodi clients.
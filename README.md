# PythonTrousers Kodi Repository

Welcome to the official Kodi repository for PythonTrousers. This repository hosts custom media plugins and applications, built with a focus on clean architecture and open-source accessibility.

## 📦 Available Add-ons

* **Internet Archive Theater (v0.2.0 Beta)** A dedicated video plugin designed to interface with the Internet Archive, providing an optimized, structured viewing experience for public domain and archived media directly within Kodi. 

## ⚙️ How to Install

To install this repository and access the add-ons on your Kodi device (Raspberry Pi, Android, PC, etc.), follow these steps:

1. Open Kodi and navigate to the **Settings** gear icon.
2. Open **File Manager** and select **Add source**.
3. Click on `<None>` and enter the following URL exactly:
   `https://pythontrousers.github.io/kodi/`
4. Name the media source **PythonTrousers** and click OK.
5. Return to the Kodi home screen, click **Add-ons**, and click the open box icon at the top left.
6. Select **Install from zip file** (If prompted, enable "Unknown sources" in your settings).
7. Select **PythonTrousers**, then click on the `repository.pythontrousers` folder, and select the `repository.pythontrousers-0.2.0.zip` file.
8. Once the repository installed notification appears, select **Install from repository**.
9. Select **PythonTrousers Repository** -> **Video add-ons** -> **Internet Archive Theater** and hit Install.

## 🛠 For Developers: Repository Architecture

This repository uses a zero-configuration raw backend delivery system managed by a local build script. 

To publish updates or add new plugins:
1. Update your plugin's code and iterate the version number in its `addon.xml`.
2. Run `python _generator.py` from the root directory. This script will automatically:
   * Package the new plugin release into standard Kodi `.zip` formats.
   * Rebuild the master `addons.xml` index.
   * Generate a new `addons.xml.md5` checksum hash.
3. Commit and push the changes to the `main` branch. GitHub Pages will automatically serve the updated index to Kodi clients.
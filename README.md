# CiefpYouTube - Enigma2 YouTube Player Extension

[![Python Version](https://img.shields.io/badge/python-3.x-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Enigma2-orange.svg)](https://github.com/ciefp/CiefpYouTube)
[![License](https://img.shields.io/badge/license-GPL--2.0-green.svg)](LICENSE)

**CiefpYouTube** is a powerful, lightweight, and user-friendly Enigma2 plugin designed for satellite receiver users (such as Vu+, Dreambox, Zgemma, etc.) running modern images like OpenATV, OpenPLi, Pure2, and OpenViX. It allows you to seamlessly browse, search, and stream YouTube videos directly on your TV screen using only your remote control.

Unlike heavy alternatives, this plugin focuses on speed, ease of use, and deep integration with standard Enigma2 media players.

---

## 🚀 Features

- **Smooth Video Playback:** Supports standard Enigma2 service players (ServiceApp, Exteplayer3, or GstPlayer) for stutter-free YouTube streaming.
- **Advanced Search & Filters:** Easily search for videos, channels, and playlists with an on-screen virtual keyboard.
- **Remote Control Optimized:** Intuitive navigation using standard colored buttons (Red, Green, Yellow, Blue) and arrow keys.
- **Custom Playlists & Favorites:** Save your favorite channels and videos directly within the plugin for quick access.
- **Resolution Control:** Select your preferred default video quality (e.g., 720p, 1080p) to match your internet connection.
- **Auto-Update System:** Built-in mechanism that checks GitHub for the latest version and prompts for a one-click update on startup.
- **Multi-Image Compatibility:** Fully compatible with both Python 2 (older images) and Python 3 (modern OpenATV 7.x+, OpenPLi 9.x+) environments.

---

## 🛠️ Installation

Choose **one** of the following methods to install the plugin on your Enigma2 set-top box.

### Method 1: The Quick Terminal Command (Recommended)
Connect to your receiver via SSH/Telnet (using PuTTY or Terminal) and run the following command:

```bash
wget -O - [https://raw.githubusercontent.com/ciefp/CiefpYouTube/main/installer.sh](https://raw.githubusercontent.com/ciefp/CiefpYouTube/main/installer.sh) | bash
(Note: If an installer.sh script is provided in your repository, this is the cleanest way. Make sure to update the URL accordingly).

Method 2: Manual FTP Installation (.ipk / .deb)
Download the latest release .ipk (for OpenATV/OpenPLi) or .deb (for DreamOS) from the Releases section.

Transfer the file to your receiver's /tmp directory using an FTP client (FileZilla, WinSCP).

Connect via SSH/Telnet and execute:

```


## 🔑 YouTube API Configuration (Optional but Recommended)
To avoid standard API quota limitations and personal limitations, 
you can configure your own YouTube API Key:

Go to the Google Developers Console.

Create a new project and enable the YouTube Data API v3.

Generate an API Key.

Open the plugin configuration menu on your TV screen, 
or manually paste your key into the configuration file located at:
/etc/enigma2/ciefpyoutube/api_key.txt

Save the file and restart the plugin.

## 🎮 Remote Control Layout
⬅️/➡️ / ⬆️/⬇️: Navigate through video feeds, menus, and search results.

OK: Play selected video / Confirm selection.

🔴 Red Button: Exit / Close active screen.

🟢 Green Button: Open Search / Save settings.

🟡 Yellow Button: Video Quality / Resolution toggle.

🔵 Blue Button: Add to Favorites / History.

🔢 Number Keys: Quick skip inside the video player (e.g., 1/3/7 for back, 4/6/9 for forward).

## ❓ Troubleshooting & Dependencies
If the plugin crashes or fails to play videos, ensure you have the necessary dependencies installed via SSH:


# Update package feed
opkg update

# Install required python components
opkg install python3-requests python3-urllib3

# Recommended for optimal playback (ServiceApp)
opkg install enigma2-plugin-systemplugins-serviceapp exteplayer3 ffmpeg
Green Screen (GSOD) on startup? Check if your image is running Python 3. 
If you encounter an experimental image bug, please open a GitHub Issue and attach the crashlog found in /home/root/logs/ or /tmp/.

Video loading forever? Try changing the player engine in Menu > Setup > System > ServiceApp to exteplayer3
 or lower the default video resolution in the plugin settings.

## 🤝 Contributing & Support
Bug Reports & Feature Requests: Please use the GitHub Issues section.

Translations: If you would like to translate the plugin into your native language, feel free to submit a Pull Request with updated .po files.

Community: Follow and connect with the author on X (Twitter): @ciefp.

## Disclaimer: 
This plugin is not officially affiliated with, authorized, maintained, or endorsed by YouTube or Google LLC. 
It is an open-source educational project built purely for the Enigma2 community.
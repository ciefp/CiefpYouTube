# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Components.MenuList import MenuList
from Components.ActionMap import ActionMap
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.config import config, ConfigSubsection, ConfigSelection, ConfigText, getConfigListEntry
from Components.ConfigList import ConfigListScreen
from Components.Sources.StaticText import StaticText
import urllib.parse
import threading
import glob
import os
import json

from .extractor import ShortsExtractor
from .shortsplayer import CiefpShortsPlayer

PLUGIN_NAME = "CiefpYouTube"
PLUGIN_VERSION = "1.2"
USER_CHANNELS_FILE = "/usr/lib/enigma2/python/Plugins/Extensions/CiefpYouTube/user_channels.json"
LIVE_CHANNELS_FILE = "/usr/lib/enigma2/python/Plugins/Extensions/CiefpYouTube/live_channels.json"
PLAYLISTS_DIR = "/usr/lib/enigma2/python/Plugins/Extensions/CiefpYouTube/playlists/"
SETTINGS_FILE = "/usr/lib/enigma2/python/Plugins/Extensions/CiefpYouTube/settings.json"

def load_settings():
    default_settings = {
        'quality': '1080',
        'max_results': '50',
        'mini_skin_opacity': '50',
        'player_type': '4097',  # DODANO: default media player (4097 = GStreamer)
    }

    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                data = json.load(f)
                default_settings.update(data)
        except:
            pass
    return default_settings

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
        return True
    except:
        return False

def get_player_type():
    """Vraća tip playera iz settings (4097, 5001 ili 5002)"""
    settings = load_settings()
    return settings.get('player_type', '4097')

class SettingsScreen(Screen, ConfigListScreen):
    skin = """
        <screen position="center,center" size="900,600" title="CiefpYouTube Settings" backgroundColor="#660033">
            <widget name="config" position="30,30" size="840,440" scrollbarMode="showOnDemand" />

            <!-- Bottom buttons bar -->
            <eLabel position="20,500" size="860,70" backgroundColor="#2a2a2a" zPosition="1" />

            <!-- Red button (Exit) -->
            <eLabel position="40,515" size="30,30" backgroundColor="#ff0000" zPosition="2" />
            <eLabel text="Exit" position="80,510" size="100,40" font="Regular;24" foregroundColor="#ffffff" backgroundColor="#00000000" transparent="1" zPosition="2" />

            <!-- Green button (Save) -->
            <eLabel position="220,515" size="30,30" backgroundColor="#00ff00" zPosition="2" />
            <eLabel text="Save" position="260,510" size="100,40" font="Regular;24" foregroundColor="#ffffff" backgroundColor="#00000000" transparent="1" zPosition="2" />

            <!-- Yellow button (Delete All) -->
            <eLabel position="400,515" size="30,30" backgroundColor="#ffff00" zPosition="2" />
            <eLabel text="Delete All" position="440,510" size="120,40" font="Regular;24" foregroundColor="#ffffff" backgroundColor="#00000000" transparent="1" zPosition="2" />

            <!-- Blue button (Delete Select) -->
            <eLabel position="600,515" size="30,30" backgroundColor="#0000ff" zPosition="2" />
            <eLabel text="Delete Sel" position="640,510" size="120,40" font="Regular;24" foregroundColor="#ffffff" backgroundColor="#00000000" transparent="1" zPosition="2" />
        </screen>
    """

    def __init__(self, session, callback):
        Screen.__init__(self, session)
        self.session = session
        self.callback = callback

        self.settings = load_settings()

        # Quality choices
        self.quality_choices = [
            ("best", "Best Available (4K/8K)"),
            ("2160", "4K UHD (2160p)"),
            ("1080", "Full HD (1080p)"),
            ("720", "HD Ready (720p)")
        ]

        # Results choices
        self.results_choices = [
            ("10", "10 videos"), ("20", "20 videos"), ("30", "30 videos"),
            ("40", "40 videos"), ("50", "50 videos"), ("100", "100 videos"),
            ("150", "150 videos"), ("200", "200 videos"), ("250", "250 videos"),
            ("300", "300 videos")
        ]

        # Opacity choices
        self.mini_opacity_choices = [
            ("100", "100%"), ("90", "90%"), ("80", "80%"), ("70", "70%"),
            ("60", "60%"), ("50", "50% (Default)"), ("40", "40%"),
            ("30", "30%"), ("20", "20%"), ("10", "10%"), ("0", "0%")
        ]

        self.mini_opacity_entry = ConfigSelection(
            choices=self.mini_opacity_choices,
            default=self.settings.get('mini_skin_opacity', '50'))

        self.quality_entry = ConfigSelection(choices=self.quality_choices, default=self.settings.get('quality', '1080'))
        self.results_entry = ConfigSelection(choices=self.results_choices,
                                             default=self.settings.get('max_results', '30'))

        # DODANO: Player type choice
        self.player_choices = [
            ("4097", "GStreamer Media Player (Preporučeno)"),
            ("5002", "DVB Player (Originalni)"),
            ("5001", "Exteplayer3 (ako je instaliran ServiceApp)"),
        ]
        self.player_entry = ConfigSelection(choices=self.player_choices,
                                            default=self.settings.get('player_type', '4097'))

        self.list = []
        self.list.append(getConfigListEntry("Video Quality:", self.quality_entry))
        self.list.append(getConfigListEntry("Max Results per Search:", self.results_entry))
        self.list.append(getConfigListEntry("Mini Skin Opacity:", self.mini_opacity_entry))
        self.list.append(getConfigListEntry("Media Player Type:", self.player_entry))  # DODANO

        ConfigListScreen.__init__(self, self.list, session=self.session)

        self["key_red"] = StaticText("Exit")
        self["key_green"] = StaticText("Save")
        self["key_yellow"] = StaticText("Delete All")
        self["key_blue"] = StaticText("Delete Select")

        self["actions"] = ActionMap(["SetupActions", "ColorActions"], {
            "red": self.cancel,
            "green": self.save,
            "yellow": self.delete_all_playlists,
            "blue": self.delete_select_playlist,
            "cancel": self.cancel,
            "ok": self.save,
        }, -2)

    def delete_all_playlists(self):
        """Briše sve plejliste iz PLAYLISTS_DIR"""
        if not os.path.exists(PLAYLISTS_DIR):
            self.session.open(MessageBox, "No playlists directory found!", MessageBox.TYPE_INFO)
            return

        # Count files
        playlist_files = glob.glob(os.path.join(PLAYLISTS_DIR, "*.json"))

        if not playlist_files:
            self.session.open(MessageBox, "No playlist files to delete!", MessageBox.TYPE_INFO)
            return

        msg = f"Are you sure you want to delete ALL {len(playlist_files)} playlist(s)?\n\nThis action cannot be undone!"
        self.session.openWithCallback(self.confirm_delete_all, MessageBox, msg, MessageBox.TYPE_YESNO)

    def confirm_delete_all(self, answer):
        if answer:
            deleted = 0
            for f in glob.glob(os.path.join(PLAYLISTS_DIR, "*.json")):
                try:
                    os.remove(f)
                    deleted += 1
                except:
                    pass
            self.session.open(MessageBox, f"Deleted {deleted} playlist(s)!", MessageBox.TYPE_INFO)

    def delete_select_playlist(self):
        """Briše selektovanu plejlistu"""
        if not os.path.exists(PLAYLISTS_DIR):
            self.session.open(MessageBox, "No playlists directory found!", MessageBox.TYPE_INFO)
            return

        playlist_files = glob.glob(os.path.join(PLAYLISTS_DIR, "*.json"))

        if not playlist_files:
            self.session.open(MessageBox, "No playlist files to delete!", MessageBox.TYPE_INFO)
            return

        # Kreiraj listu za ChoiceBox
        choices = []
        for f in playlist_files:
            try:
                with open(f, 'r') as file:
                    data = json.load(file)
                    name = data.get("playlist_name", os.path.basename(f))
                    choices.append((f"{name}", f))
            except:
                choices.append((os.path.basename(f), f))

        self.session.openWithCallback(self.confirm_delete_select, ChoiceBox, title="Select playlist to delete:",
                                      list=choices)

    def confirm_delete_select(self, choice):
        if choice:
            filepath = choice[1]
            try:
                # Pročitaj ime za poruku
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    name = data.get("playlist_name", os.path.basename(filepath))

                msg = f"Delete playlist '{name}'?"
                self.session.openWithCallback(lambda x: self.do_delete(x, filepath, name), MessageBox, msg,
                                              MessageBox.TYPE_YESNO)
            except:
                pass

    def do_delete(self, answer, filepath, name):
        if answer:
            try:
                os.remove(filepath)
                self.session.open(MessageBox, f"Playlist '{name}' deleted!", MessageBox.TYPE_INFO)
            except Exception as e:
                self.session.open(MessageBox, f"Error deleting: {str(e)}", MessageBox.TYPE_ERROR)

    def save(self):
        self.settings['quality'] = self.quality_entry.value
        self.settings['max_results'] = self.results_entry.value
        self.settings['mini_skin_opacity'] = self.mini_opacity_entry.value
        self.settings['player_type'] = self.player_entry.value  # DODANO
        save_settings(self.settings)
        if self.callback:
            self.callback(True)
        self.close()

    def cancel(self):
        if self.callback:
            self.callback(False)
        self.close()

class CiefpYouTubeMainMenu(Screen):
    skin = """
        <screen position="0,0" size="1920,1080" title="CiefpYouTube v2.1" backgroundColor="#660033" flags="wfNoBorder">
            <eLabel position="0,0" size="1920,100" backgroundColor="#1a1a1a" zPosition="-1" />
            <eLabel text="..:: CiefpYouTube ::.." position="60,25" size="600,50" font="Regular;40" foregroundColor="#ffffff" backgroundColor="#00000000" transparent="1" />
            
            <widget name="menu" position="150,150" size="500,650" scrollbarMode="showOnDemand" itemHeight="55" font="Regular;28" foregroundColor="#ffffff" backgroundColor="#1a1a1a" zPosition="2" />
            
            <widget name="youtube_icon" position="800,150" size="1000,650" zPosition="1" alphatest="on" />
            
            <eLabel position="0,900" size="1920,50" backgroundColor="#1a1a1a" zPosition="1" />
            <widget name="status" position="0,900" size="1920,50" font="Regular;24" halign="center" foregroundColor="#ffcc00" backgroundColor="#1a1a1a" transparent="1" zPosition="2" />
            
            <!-- Colored buttons -->
            <eLabel position="0,980" size="1920,100" backgroundColor="#1a1a1a" zPosition="1" />
            <eLabel position="60,1015" size="30,30" backgroundColor="red" zPosition="2" />
            <eLabel text="EXIT"  position="105,1010" size="150,40" font="Regular;30" foregroundColor="#ffffff" backgroundColor="#1a1a1a" transparent="1" zPosition="2" />
            
            <eLabel position="300,1015" size="30,30" backgroundColor="green" zPosition="2" />
            <eLabel text="SEARCH"  position="345,1010" size="150,40" font="Regular;30" foregroundColor="#ffffff" backgroundColor="#1a1a1a" transparent="1" zPosition="2" />
            
            <eLabel position="510,1015" size="30,30" backgroundColor="yellow" zPosition="2" />
            <eLabel text="SETTINGS" position="555,1010" size="200,40" font="Regular;30" foregroundColor="#ffffff" backgroundColor="#1a1a1a" transparent="1" zPosition="2" />
            
            <eLabel position="755,1015" size="30,30" backgroundColor="blue" zPosition="2" />
            <eLabel text="ABOUT" position="795,1010" size="150,40" font="Regular;30" foregroundColor="#ffffff" backgroundColor="#1a1a1a" transparent="1" zPosition="2" />
        </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        
        # Load settings
        self.settings = load_settings()
        
        # Initialize extractor with settings
        self.extractor = ShortsExtractor(
            quality=self.settings.get('quality', '1080'),
            max_results=int(self.settings.get('max_results', '30'))
        )

        self["youtube_icon"] = Pixmap()
        self.onLayoutFinish.append(self.loadIcon)

        # Load user & live channels
        self.user_channels = self.loadUserChannels()
        self.live_channels = self.loadLiveChannels()
        # Menu options
        self.list = [
            ("🔍 Search YouTube", "search"),

            # User Channels i Live Channels (odmah ispod Search)
        ]

        # Add User Channels category
        if self.user_channels:
            self.list.append(("📺 User Channels", "user_channels"))
        if self.live_channels:
            self.list.append(("🔴 Live Channels", "live_channels"))
        self.list.append(("📂 Latest playlist (Quick open)", "saved_playlist"))

        self.list.append(("─" * 40, "separator"))
        self.list.append(("⚙️ Edit User Channels", "edit_channels"))
        self.list.append(("🗑️ Delete Playlists", "delete_playlists"))

        # Separator pa WebCam i Broken Log
        self.list.append(("─" * 40, "separator"))
        self.list.append(("🎥 WebCam Prenj (from bouquet)", "webcam_prenj"))
        self.list.append(("⚠️ Broken Links Log", "broken_log"))

        # Zatim separator i ostale kategorije
        self.list.append(("─" * 40, "separator"))
        self.list.append(("🎬 YouTube Shorts", "yt_shorts"))
        self.list.append(("🎵 YouTube Music", "yt_music"))
        self.list.append(("🎥 YouTube Trailers", "yt_trailers"))
        self.list.append(("📰 YouTube News", "yt_news"))
        self.list.append(("🎮 YouTube Gaming", "yt_gaming"))
        self.list.append(("🔥 YouTube Trending", "yt_trending"))
        self.list.append(("🔴 Live Now", "yt_live"))
        self.list.append(("🎙️ Podcasts", "yt_podcast"))
        self.list.append(("✨ New For You", "yt_new"))

        self.list.append(("─" * 40, "separator"))

        # Zabava i humor
        self.list.append(("🤣 Comedy & Fails", "yt_comedy"))
        self.list.append(("🎬 Movie Reviews", "yt_moviereviews"))

        self.list.append(("─" * 40, "separator"))

        # Edukacija i nauka
        self.list.append(("📚 Educational", "yt_educational"))
        self.list.append(("🔬 Science & Tech", "yt_science"))
        self.list.append(("📖 Documentaries", "yt_docs"))
        self.list.append(("💻 Programming & Tech", "yt_programming"))
        self.list.append(("📐 Mathematics & Physics", "yt_math"))

        self.list.append(("─" * 40, "separator"))

        # Sport
        self.list.append(("⚽ Sports Highlights", "yt_sports"))
        self.list.append(("🏀 NBA/Basketball", "yt_basketball"))
        self.list.append(("⚽ Football/Soccer", "yt_football"))

        self.list.append(("─" * 40, "separator"))

        # Životni stil
        self.list.append(("💪 Fitness & Gym", "yt_fitness"))
        self.list.append(("🎨 Art & Creativity", "yt_art"))
        self.list.append(("🏠 Home & DIY", "yt_diy"))
        self.list.append(("🍳 Cooking & Recipes", "yt_cooking"))

        self.list.append(("─" * 40, "separator"))

        # Recenzije i putovanja
        self.list.append(("📱 Tech Reviews", "yt_tech"))
        self.list.append(("🚗 Car Reviews", "yt_cars"))
        self.list.append(("✈️ Travel Vlogs", "yt_travel"))
        self.list.append(("🐶 Animals & Pets", "yt_animals"))

        self["menu"] = MenuList(self.list)
        self["status"] = Label("")
        self["status"].setText("Select category or search YouTube")
        
        self["actions"] = ActionMap(["WizardActions", "DirectionActions", "ColorActions"], {
            "ok": self.selectOption,
            "back": self.close,
            "up": self.keyUp,
            "down": self.keyDown,
            "red": self.close,
            "green": self.openSearch,
            "yellow": self.openSettings,
            "blue": self.showAbout,
        }, -1)

    def loadIcon(self):
        icon_path = "/usr/lib/enigma2/python/Plugins/Extensions/CiefpYouTube/icons/youtube.png"
        if os.path.exists(icon_path):
            self["youtube_icon"].instance.setPixmapFromFile(icon_path)

    def loadUserChannels(self):
        if os.path.exists(USER_CHANNELS_FILE):
            try:
                with open(USER_CHANNELS_FILE, 'r') as f:
                    data = json.load(f)
                    return data.get('channels', [])
            except:
                return []
        return []

    def loadLiveChannels(self):
        if os.path.exists(LIVE_CHANNELS_FILE):
            try:
                with open(LIVE_CHANNELS_FILE, 'r') as f:
                    data = json.load(f)
                    return data.get('live_channels', [])
            except Exception as e:
                print(f"[CiefpYouTube] Live channels error: {e}")
                return []

        return []


    def load_webcam_bouquet(self):
        """Parsira userbouquet i vadi YouTube linkove"""
        bouquet_path = "/etc/enigma2/userbouquet.web_cam____prenj___.tv"
        youtube_urls = []

        if not os.path.exists(bouquet_path):
            # Prikaži poruku sa instrukcijama
            msg = _("Userbouquet does not exist!") + "\n\n" + \
                  _("Use the WebCamE2PrenjSF plugin to download or refresh the userbouquet.") + "\n\n" + \
                  _("Path: /etc/enigma2/userbouquet.web_cam____prenj___.tv")
            self.session.open(MessageBox, msg, MessageBox.TYPE_INFO)
            return []

        try:
            with open(bouquet_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            for i, line in enumerate(lines):
                line = line.strip()

                # Tražimo #SERVICE linije koje sadrže YT-DLP
                if line.startswith('#SERVICE') and ('YT-DLP' in line or 'yt-dlp' in line.lower()):
                    # Ekstrakcija URL-a iz #SERVICE linije
                    # Format: #SERVICE 5002:0:1:0:0:0:0:0:0:0:YT-DLP%3a//https%3a//www.youtube.com/watch?v=xxxxx

                    # Pronađi deo posle poslednjeg ':'
                    parts = line.split(':')
                    if len(parts) >= 10:
                        url_part = parts[-1]

                        # Ukloni YT-DLP:// prefiks (može biti sa %3a ili normalan)
                        if 'YT-DLP%3a//' in url_part:
                            url = url_part.replace('YT-DLP%3a//', '')
                        elif 'YT-DLP://' in url_part:
                            url = url_part.replace('YT-DLP://', '')
                        elif 'yt-dlp%3a//' in url_part.lower():
                            url = url_part.lower().replace('yt-dlp%3a//', '')
                        else:
                            url = url_part

                        # Dekodiraj URL (konvertuj %3a u :, %2f u /, itd.)
                        url = urllib.parse.unquote(url)

                        # Provera da li je YouTube link
                        if 'youtube.com/watch' in url or 'youtu.be/' in url:
                            # Uzmi naslov iz sledeće #DESCRIPTION linije
                            title = "YouTube Stream"
                            if i + 1 < len(lines):
                                next_line = lines[i + 1].strip()
                                if next_line.startswith('#DESCRIPTION'):
                                    title = next_line.replace('#DESCRIPTION', '').strip()
                                    # Ukloni OFF oznake i slično
                                    title = title.split('\\c00')[0].strip()
                                    if title.endswith('@'):
                                        title = title[:-1].strip()

                            youtube_urls.append({
                                'title': f"🎥 {title}",
                                'url': url,
                                'author': 'WebCam'
                            })
                            print(f"[CiefpYouTube] Found: {title} -> {url}")

            # Ako nismo našli ništa na prvi način, probaj drugi metod
            if not youtube_urls:
                for line in lines:
                    line = line.strip()
                    if 'youtube.com' in line or 'youtu.be' in line:
                        import re
                        urls = re.findall(r'(https?://[^\s]+)', line)
                        for url in urls:
                            url = urllib.parse.unquote(url)
                            if 'youtube.com/watch' in url or 'youtu.be/' in url:
                                youtube_urls.append({
                                    'title': 'YouTube Stream',
                                    'url': url,
                                    'author': 'WebCam'
                                })

        except Exception as e:
            print(f"[CiefpYouTube] Error parsing bouquet: {e}")
            import traceback
            traceback.print_exc()
            self.session.open(MessageBox, f"Error parsing bouquet:\n{str(e)}", MessageBox.TYPE_ERROR)
            return []

        print(f"[CiefpYouTube] Total YouTube URLs found: {len(youtube_urls)}")
        return youtube_urls

    def load_webcam_playlist(self, source_type):
        """Učitava webcam buket i kreira playlistu"""
        self["status"].setText("Loading WebCam Prenj bouquet...")

        # Učitaj YouTube linkove iz buketa
        youtube_urls = self.load_webcam_bouquet()

        if not youtube_urls:
            self.session.open(MessageBox, "No YouTube streams found in WebCam Prenj bouquet!", MessageBox.TYPE_ERROR)
            return

        # Ako ima linkova, direktno otvori plejer
        self.session.open(CiefpShortsPlayer, youtube_urls)

        # Takođe sačuvaj kao JSON za kasnije korišćenje
        try:
            playlist_dir = "/usr/lib/enigma2/python/Plugins/Extensions/CiefpYouTube/playlists/"
            if not os.path.exists(playlist_dir):
                os.makedirs(playlist_dir)

            playlist_file = os.path.join(playlist_dir, "webcam_prenj.json")
            with open(playlist_file, 'w') as f:
                json.dump({
                    "playlist_name": "WebCam Prenj",
                    "videos": youtube_urls
                }, f, indent=2)
            print(f"[CiefpYouTube] Saved webcam playlist to {playlist_file}")
        except Exception as e:
            print(f"[CiefpYouTube] Error saving playlist: {e}")

    def show_broken_links_log(self):
        """Prikazuje log neaktivnih linkova"""
        log_file = "/tmp/ciefp_youtube_broken_links.log"

        if not os.path.exists(log_file):
            self.session.open(MessageBox, "No broken links log found!\n\nLog file will be created when a stream fails.",
                              MessageBox.TYPE_INFO)
            return

        try:
            with open(log_file, 'r') as f:
                content = f.read()

            if not content.strip():
                self.session.open(MessageBox, "Log file is empty - no broken links recorded yet.", MessageBox.TYPE_INFO)
                return

            # Prikaži poslednjih 50 linija (da ne bude preveliko)
            lines = content.split('\n')
            last_lines = lines[-50:] if len(lines) > 50 else lines
            preview = '\n'.join(last_lines)

            # Opcije za log
            choices = [
                ("📋 View log", "view"),
                ("🗑️ Clear log", "clear"),
                ("📂 Full log path", "path")
            ]
            self.session.openWithCallback(self.broken_log_callback, ChoiceBox, title="Broken Links Log", list=choices)

        except Exception as e:
            self.session.open(MessageBox, f"Error reading log: {str(e)}", MessageBox.TYPE_ERROR)

    def broken_log_callback(self, choice):
        if not choice:
            return

        action = choice[1]
        log_file = "/tmp/ciefp_youtube_broken_links.log"

        if action == "view":
            try:
                with open(log_file, 'r') as f:
                    content = f.read()
                # Prikaži u MessageBox-u (ograniči dužinu)
                if len(content) > 3000:
                    content = content[-3000:] + "\n\n... (truncated)"
                self.session.open(MessageBox, content, MessageBox.TYPE_INFO)
            except:
                pass

        elif action == "clear":
            try:
                with open(log_file, 'w') as f:
                    f.write("")
                self.session.open(MessageBox, "Log file cleared!", MessageBox.TYPE_INFO)
            except:
                pass

        elif action == "path":
            self.session.open(MessageBox, f"Log file location:\n{log_file}", MessageBox.TYPE_INFO)

    def delete_playlists_menu(self):
        """Otvara meni za brisanje plejlisti"""
        if not os.path.exists(PLAYLISTS_DIR):
            self.session.open(MessageBox, "No playlists directory found!", MessageBox.TYPE_INFO)
            return

        playlist_files = glob.glob(os.path.join(PLAYLISTS_DIR, "*.json"))

        if not playlist_files:
            self.session.open(MessageBox, "No playlist files to delete!", MessageBox.TYPE_INFO)
            return

        # Kreiraj listu za ChoiceBox
        choices = [("Delete ALL playlists", "all")]
        choices.append(("─" * 40, "separator"))

        for f in playlist_files:
            try:
                with open(f, 'r') as file:
                    data = json.load(file)
                    name = data.get("playlist_name", os.path.basename(f))
                    choices.append((f"🗑️ {name}", f))
            except:
                choices.append((f"🗑️ {os.path.basename(f)}", f))

        self.session.openWithCallback(self.delete_playlists_callback, ChoiceBox, title="Delete Playlists:",
                                      list=choices)

    def delete_playlists_callback(self, choice):
        if not choice:
            return

        if choice[1] == "all":
            # Obriši sve
            msg = f"Delete ALL playlists?"
            self.session.openWithCallback(self.confirm_delete_all_playlists, MessageBox, msg, MessageBox.TYPE_YESNO)
        elif choice[1] != "separator":
            # Obriši jedan fajl
            filepath = choice[1]
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    name = data.get("playlist_name", os.path.basename(filepath))
                msg = f"Delete playlist '{name}'?"
                self.session.openWithCallback(lambda x: self.delete_single_playlist(x, filepath, name), MessageBox, msg,
                                              MessageBox.TYPE_YESNO)
            except:
                pass

    def confirm_delete_all_playlists(self, answer):
        if answer:
            deleted = 0
            for f in glob.glob(os.path.join(PLAYLISTS_DIR, "*.json")):
                try:
                    os.remove(f)
                    deleted += 1
                except:
                    pass
            self.session.open(MessageBox, f"Deleted {deleted} playlist(s)!", MessageBox.TYPE_INFO)

    def delete_single_playlist(self, answer, filepath, name):
        if answer:
            try:
                os.remove(filepath)
                self.session.open(MessageBox, f"Playlist '{name}' deleted!", MessageBox.TYPE_INFO)
            except Exception as e:
                self.session.open(MessageBox, f"Error deleting: {str(e)}", MessageBox.TYPE_ERROR)

    def saveUserChannels(self, channels):
        try:
            with open(USER_CHANNELS_FILE, 'w') as f:
                json.dump({'channels': channels}, f, indent=2)
            return True
        except:
            return False

    def keyUp(self):
        self["menu"].up()
        
    def keyDown(self):
        self["menu"].down()

    def openSettings(self):
        """Open settings screen"""
        self.session.open(SettingsScreen, self.settingsClosed)
    
    def settingsClosed(self, changed):
        if changed:
            # Reload settings and recreate extractor
            self.settings = load_settings()
            self.extractor = ShortsExtractor(
                quality=self.settings.get('quality', '1080'),
                max_results=int(self.settings.get('max_results', '30'))
            )
            self["status"].setText(f"Settings updated! Quality: {self.settings.get('quality', '1080')}p, Max: {self.settings.get('max_results', '30')}")
            self["info"].setText(f"Settings: {self.settings.get('quality', '1080')}p | {self.settings.get('max_results', '30')} videos")
    
    def showAbout(self):
        about_text = f"""CiefpYouTube v{PLUGIN_VERSION}

YouTube Video Browser for Enigma2

Features:
• Search YouTube videos
• Shorts, Music, Trailers, News, Gaming
• Live streams, Podcasts
• User channels (save your favorites)
• Live channels (save your favorites)
• Creating a playlist
• Configurable max results

Created by Ciefp
© 2026"""
        self.session.open(MessageBox, about_text, MessageBox.TYPE_INFO)

    def selectOption(self):
        current = self["menu"].getCurrent()
        if current:
            source_type = current[1]

            # --- NOVO: Otvaranje ChoiceBox-a sa istorijom sačuvanih lista ---
            if source_type == "saved_playlist":
                if os.path.exists(PLAYLISTS_DIR):
                    files = [f for f in os.listdir(PLAYLISTS_DIR) if f.endswith('.json')]

                    if files:
                        saved_lists = []
                        for filename in files:
                            try:
                                with open(os.path.join(PLAYLISTS_DIR, filename), 'r') as f:
                                    data = json.load(f)
                                    # Sakupljamo (Lepo ime kanala, putanja do fajla)
                                    saved_lists.append(
                                        (data.get("playlist_name", filename), os.path.join(PLAYLISTS_DIR, filename)))
                            except:
                                pass

                        if saved_lists:
                            # Ako ima samo JEDNA sačuvana lista, pusti je odmah bez ChoiceBox-a
                            if len(saved_lists) == 1:
                                self.openSavedPlaylistCallback((saved_lists[0][0], saved_lists[0][1]))
                                return

                            # Ako ih ima više, ponudi ChoiceBox korisniku
                            self.session.openWithCallback(self.openSavedPlaylistCallback, ChoiceBox,
                                                          title="Select a saved playlist:", list=saved_lists)
                            return

                self.session.open(MessageBox,
                                  "No saved playlists!\nOpen a channel to automatically create a playlist.",
                                  MessageBox.TYPE_ERROR)
                return
            # -----------------------------------------------------------------

            if source_type == "separator":
                return
            elif source_type == "search":
                self.openSearch()
            elif source_type == "user_channels":
                self.showUserChannels()
            elif source_type == "edit_channels":
                self.editUserChannels()
            elif source_type == "delete_playlists":
                self.delete_playlists_menu()
            elif source_type == "live_channels":
                self.showLiveChannels()
            elif source_type == "webcam_prenj":
                self.load_webcam_playlist(source_type)
            elif source_type == "broken_log":
                self.show_broken_links_log()
            else:
                self["status"].setText(f"Loading {current[0]}...")
                threading.Thread(target=self.loadVideos, args=(source_type, current[0]), daemon=True).start()

    def openSearch(self):
        self.session.openWithCallback(self.searchPerformed, VirtualKeyBoard, title="Enter search term:", text="")
    
    def searchPerformed(self, search_term):
        if search_term and search_term.strip():
            self["status"].setText(f"Searching: {search_term}...")
            threading.Thread(target=self.loadVideos, args=("search", search_term), daemon=True).start()

    def showUserChannels(self):
        if not self.user_channels:
            self.session.open(MessageBox, "No user channels saved!\nUse 'Edit User Channels' to add channels.", MessageBox.TYPE_INFO)
            return
        
        choices = [(channel['name'], channel['url']) for channel in self.user_channels]
        self.session.openWithCallback(self.userChannelSelected, ChoiceBox, title="Select Channel:", list=choices)

    def showLiveChannels(self):
        if not self.live_channels:
            self.session.open(
                MessageBox,
                "No live channels saved!",
                MessageBox.TYPE_INFO
            )
            return

        choices = [
            (channel['name'], channel['url'])
            for channel in self.live_channels
        ]

        self.session.openWithCallback(
            self.liveChannelSelected,
            ChoiceBox,
            title="Select Live Channel:",
            list=choices
        )

    def liveChannelSelected(self, choice):
        if choice:
            channel_url = choice[1]
            channel_name = choice[0]

            self["status"].setText(
                f"Loading live stream from {channel_name}..."
            )

            threading.Thread(
                target=self.loadVideos,
                args=("live_channel", channel_url),
                daemon=True
            ).start()
    
    def userChannelSelected(self, choice):
        if choice:
            channel_url = choice[1]
            channel_name = choice[0]
            self["status"].setText(f"Loading {channel_name}...")
            threading.Thread(target=self.loadVideos, args=("channel", channel_url), daemon=True).start()

    def editUserChannels(self):
        menu_items = [
            ("Add New Channel", "add"),
            ("Remove All Channels", "remove_all"),
        ]
        
        if self.user_channels:
            menu_items.insert(1, ("View/Remove Channels", "remove"))
        
        self.session.openWithCallback(self.editMenuSelected, ChoiceBox, title="Edit User Channels:", list=menu_items)
    
    def editMenuSelected(self, choice):
        if not choice:
            return
        
        action = choice[1]
        
        if action == "add":
            self.addUserChannel()
        elif action == "remove":
            self.removeUserChannel()
        elif action == "remove_all":
            self.user_channels = []
            self.saveUserChannels(self.user_channels)
            self.refreshMenu()
            self.session.open(MessageBox, "All user channels removed!", MessageBox.TYPE_INFO)
    
    def addUserChannel(self):
        self.session.openWithCallback(self.addChannelName, VirtualKeyBoard, title="Enter channel name:", text="")
    
    def addChannelName(self, name):
        if name and name.strip():
            self.pending_channel_name = name.strip()
            self.session.openWithCallback(self.addChannelUrl, VirtualKeyBoard, title=f"Enter URL for {name}:", text="https://www.youtube.com/@")
    
    def addChannelUrl(self, url):
        if url and url.strip():
            self.user_channels.append({
                'name': self.pending_channel_name,
                'url': url.strip()
            })
            self.saveUserChannels(self.user_channels)
            self.refreshMenu()
            self.session.open(MessageBox, f"Channel '{self.pending_channel_name}' added!", MessageBox.TYPE_INFO)
    
    def removeUserChannel(self):
        choices = [(channel['name'], idx) for idx, channel in enumerate(self.user_channels)]
        self.session.openWithCallback(self.removeChannelSelected, ChoiceBox, title="Select channel to remove:", list=choices)
    
    def removeChannelSelected(self, choice):
        if choice:
            idx = choice[1]
            removed = self.user_channels.pop(idx)
            self.saveUserChannels(self.user_channels)
            self.refreshMenu()
            self.session.open(MessageBox, f"Channel '{removed['name']}' removed!", MessageBox.TYPE_INFO)

    def refreshMenu(self):
        self.user_channels = self.loadUserChannels()
        self.live_channels = self.loadLiveChannels()

        new_list = [
            ("🔍 Search YouTube", "search"),
            ("─" * 40, "separator"),
            ("📂 Latest playlist (Quick open)", "saved_playlist"),
            ("🎬 YouTube Shorts", "yt_shorts"),
            ("🎵 YouTube Music", "yt_music"),
            ("🎥 YouTube Trailers", "yt_trailers"),
            ("📰 YouTube News", "yt_news"),
            ("🎮 YouTube Gaming", "yt_gaming"),
            ("🔥 YouTube Trending", "yt_trending"),
            ("🔴 Live Now", "yt_live"),
            ("🎙️ Podcasts", "yt_podcast"),
            ("✨ New For You", "yt_new"),

            ("─" * 40, "separator"),

            ("🤣 Comedy & Fails", "yt_comedy"),
            ("🎬 Movie Reviews", "yt_moviereviews"),

            ("─" * 40, "separator"),

            ("📚 Educational", "yt_educational"),
            ("🔬 Science & Tech", "yt_science"),
            ("📖 Documentaries", "yt_docs"),
            ("💻 Programming & Tech", "yt_programming"),
            ("📐 Mathematics & Physics", "yt_math"),

            ("─" * 40, "separator"),

            ("⚽ Sports Highlights", "yt_sports"),
            ("🏀 NBA/Basketball", "yt_basketball"),
            ("⚽ Football/Soccer", "yt_football"),

            ("─" * 40, "separator"),

            ("💪 Fitness & Gym", "yt_fitness"),
            ("🎨 Art & Creativity", "yt_art"),
            ("🏠 Home & DIY", "yt_diy"),
            ("🍳 Cooking & Recipes", "yt_cooking"),

            ("─" * 40, "separator"),

            ("📱 Tech Reviews", "yt_tech"),
            ("🚗 Car Reviews", "yt_cars"),
            ("✈️ Travel Vlogs", "yt_travel"),
            ("🐶 Animals & Pets", "yt_animals"),

            ("─" * 40, "separator"),
        ]

        if self.user_channels:
            new_list.append(("📺 User Channels", "user_channels"))

        if self.live_channels:
            new_list.append(("🔴 Live Channels", "live_channels"))

        new_list.append(("⚙️ Edit User Channels", "edit_channels"))

        self["menu"].setList(new_list)
        self.list = new_list

    def openSavedPlaylistCallback(self, answer):
        if answer:
            filepath = answer[1]
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    playlist = data.get("videos", [])
                if playlist:
                    self.session.open(CiefpShortsPlayer, playlist)
            except Exception as e:
                print(f"[CiefpYouTube] Error opening selected list:{e}")

    def loadVideos(self, source_type, search_term):
        playlist = self.extractor.get_shorts_list(source_type, search_term)

        # --- Čuvanje više različitih plejlista na osnovu naziva ---
        if playlist and search_term:
            try:
                if not os.path.exists(PLAYLISTS_DIR):
                    os.makedirs(PLAYLISTS_DIR)

                # Čišćenje naziva od emojija, krtih znakova i URL linkova
                clean_term = "".join([c for c in search_term if c.isalnum() or c in (' ', '_', '-')]).strip()

                # Ako je u pitanju URL (korisnički kanal), skraćujemo ga na ime handle-a (@)
                if "youtube.com" in search_term or "http" in search_term:
                    clean_term = search_term.split('@')[-1].split('/')[0] if '@' in search_term else "User_Channel"

                if not clean_term:
                    clean_term = str(source_type)

                safe_filename = clean_term.replace(" ", "_") + ".json"
                filepath = os.path.join(PLAYLISTS_DIR, safe_filename)

                playlist_data = {
                    "playlist_name": search_term,  # Čuvamo originalno ime za ChoiceBox
                    "videos": playlist
                }

                with open(filepath, 'w') as f:
                    json.dump(playlist_data, f)
                print(f"[CiefpYouTube] Playlist for '{search_term}' successfully saved to {safe_filename}.")
            except Exception as e:
                print(f"[CiefpYouTube] Error while dynamically saving list: {e}")
        # ----------------------------------------------------------------

        # POZIV TVOJE ORIGINALNE FUNKCIJE PREKO REACTOR-A
        from twisted.internet import reactor
        reactor.callFromThread(self.videosLoaded, playlist)

    def videosLoaded(self, playlist):
        self["status"].setText("")
        if playlist:
            self.session.open(CiefpShortsPlayer, playlist)
        else:
            self.session.open(MessageBox, "No videos found!\nCheck your internet connection.", MessageBox.TYPE_ERROR)

def main(session, **kwargs):
    session.open(CiefpYouTubeMainMenu)

def Plugins(**kwargs):
    icon_path = "/usr/lib/enigma2/python/Plugins/Extensions/CiefpYouTube/icons/plugin.png"
    return PluginDescriptor(
        name=f"{PLUGIN_NAME} v{PLUGIN_VERSION}",
        description="YouTube Video Browser - Search, Shorts, Music,Categories,Playlist",
        where=PluginDescriptor.WHERE_PLUGINMENU,
        icon=icon_path if os.path.exists(icon_path) else None,
        fnc=main
    )
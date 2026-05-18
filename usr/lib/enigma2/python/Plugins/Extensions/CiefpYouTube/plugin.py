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
import threading
import os
import json

from .extractor import ShortsExtractor
from .shortsplayer import CiefpShortsPlayer

PLUGIN_NAME = "CiefpYouTube"
PLUGIN_VERSION = "1.0"
USER_CHANNELS_FILE = "/usr/lib/enigma2/python/Plugins/Extensions/CiefpYouTube/user_channels.json"
LIVE_CHANNELS_FILE = "/usr/lib/enigma2/python/Plugins/Extensions/CiefpYouTube/live_channels.json"
PLAYLISTS_DIR = "/usr/lib/enigma2/python/Plugins/Extensions/CiefpYouTube/playlists/"
SETTINGS_FILE = "/usr/lib/enigma2/python/Plugins/Extensions/CiefpYouTube/settings.json"

# Load settings
def load_settings():
    default_settings = {
        'quality': '1080',
        'max_results': '30',
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


class SettingsScreen(Screen, ConfigListScreen):
    skin = """
        <screen position="center,center" size="800,500" title="CiefpYouTube Settings" backgroundColor="#1a1a1a">
            <widget name="config" position="20,20" size="760,400" scrollbarMode="showOnDemand" />
            <widget name="key_red" position="20,440" size="180,40" backgroundColor="#ff0000" font="Regular;22" halign="center" valign="center" foregroundColor="#ffffff" transparent="1" />
            <widget name="key_green" position="210,440" size="180,40" backgroundColor="#00ff00" font="Regular;22" halign="center" valign="center" foregroundColor="#ffffff" transparent="1" />
        </screen>
    """

    def __init__(self, session, callback):
        Screen.__init__(self, session)
        self.session = session
        self.callback = callback

        self.settings = load_settings()

        # Create config entries
        self.quality_choices = [
            ("best", "Best Available (4K/8K)"),
            ("2160", "4K UHD (2160p)"),
            ("1080", "Full HD (1080p)"),
            ("720", "HD Ready (720p)")
        ]

        self.results_choices = [
            ("10", "10 videos"),
            ("20", "20 videos"),
            ("30", "30 videos"),
            ("40", "40 videos"),
            ("50", "50 videos"),
            ("100", "100 videos"),
            ("150", "150 videos"),
            ("200", "200 videos"),
            ("250", "250 videos"),
            ("300", "300 videos")
        ]

        self.quality_entry = ConfigSelection(choices=self.quality_choices, default=self.settings.get('quality', '1080'))
        self.results_entry = ConfigSelection(choices=self.results_choices,
                                             default=self.settings.get('max_results', '30'))

        self.list = []
        self.list.append(getConfigListEntry("Video Quality:", self.quality_entry))
        self.list.append(getConfigListEntry("Max Results per Search:", self.results_entry))

        ConfigListScreen.__init__(self, self.list, session=self.session)

        self["key_red"] = StaticText("Cancel")
        self["key_green"] = StaticText("Save")

        self["actions"] = ActionMap(["SetupActions", "ColorActions"], {
            "red": self.cancel,
            "green": self.save,
            "cancel": self.cancel,
            "ok": self.save,
        }, -2)

    def save(self):
        self.settings['quality'] = self.quality_entry.value
        self.settings['max_results'] = self.results_entry.value
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
        # Menu options
        self.list = [
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

            # Zabava i humor
            ("🤣 Comedy & Fails", "yt_comedy"),
            ("🎬 Movie Reviews", "yt_moviereviews"),

            ("─" * 40, "separator"),

            # Edukacija i nauka
            ("📚 Educational", "yt_educational"),
            ("🔬 Science & Tech", "yt_science"),
            ("📖 Documentaries", "yt_docs"),
            ("💻 Programming & Tech", "yt_programming"),
            ("📐 Mathematics & Physics", "yt_math"),

            ("─" * 40, "separator"),

            # Sport
            ("⚽ Sports Highlights", "yt_sports"),
            ("🏀 NBA/Basketball", "yt_basketball"),
            ("⚽ Football/Soccer", "yt_football"),

            ("─" * 40, "separator"),

            # Životni stil
            ("💪 Fitness & Gym", "yt_fitness"),
            ("🎨 Art & Creativity", "yt_art"),
            ("🏠 Home & DIY", "yt_diy"),
            ("🍳 Cooking & Recipes", "yt_cooking"),

            ("─" * 40, "separator"),

            # Recenzije i putovanja
            ("📱 Tech Reviews", "yt_tech"),
            ("🚗 Car Reviews", "yt_cars"),
            ("✈️ Travel Vlogs", "yt_travel"),
            ("🐶 Animals & Pets", "yt_animals"),

            ("─" * 40, "separator"),
        ]
        # Add User Channels category
        if self.user_channels:
            self.list.append(("📺 User Channels", "user_channels"))
        if self.live_channels:
            self.list.append(("🔴 Live Channels", "live_channels"))
        
        self.list.append(("⚙️ Edit User Channels", "edit_channels"))

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
            elif source_type == "live_channels":
                self.showLiveChannels()
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
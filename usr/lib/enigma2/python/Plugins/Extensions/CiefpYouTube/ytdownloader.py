# -*- coding: utf-8 -*-
# ytdownloader.py - YouTube Download Manager for CiefpYouTube

import os
import json
import threading
import subprocess
import datetime
import re
from enigma import eTimer
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Components.Label import Label
from Components.Pixmap import Pixmap
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Components.config import ConfigSelection, ConfigText, getConfigListEntry
from Components.ConfigList import ConfigListScreen
from Components.Sources.StaticText import StaticText
from Components.ProgressBar import ProgressBar
from Screens.VirtualKeyBoard import VirtualKeyBoard
# ============= KONFIGURACIJA =============
PLAYLISTS_DIR = "/usr/lib/enigma2/python/Plugins/Extensions/CiefpYouTube/playlists/"
SETTINGS_FILE = "/usr/lib/enigma2/python/Plugins/Extensions/CiefpYouTube/settings.json"
DOWNLOAD_LOG = "/tmp/ciefp_youtube_downloads.log"

def get_download_path():
    """Uzima putanju za download iz settings"""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                data = json.load(f)
                path = data.get('download_path', '/hdd/movie/YouTube_Downloads/')
                if not os.path.exists(path):
                    try:
                        os.makedirs(path)
                    except:
                        pass
                return path
    except:
        pass
    
    default_path = '/hdd/movie/YouTube_Downloads/'
    if not os.path.exists(default_path):
        try:
            os.makedirs(default_path)
        except:
            pass
    return default_path

def save_download_path(path):
    """Čuva putanju za download u settings"""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                data = json.load(f)
        else:
            data = {}
        
        data['download_path'] = path
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except:
        return False

def log_download(url, title, filepath, success=True, error_msg=""):
    """Loguje download aktivnost"""
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "SUCCESS" if success else "FAILED"
        with open(DOWNLOAD_LOG, 'a') as f:
            f.write(f"\n{'─'*80}\n")
            f.write(f"[{timestamp}] {status}\n")
            f.write(f"TITLE: {title}\n")
            f.write(f"URL: {url}\n")
            if success:
                f.write(f"SAVED: {filepath}\n")
            else:
                f.write(f"ERROR: {error_msg}\n")
            f.write(f"{'─'*80}\n")
    except:
        pass

def get_safe_filename(title):
    """Konvertuje naslov u siguran naziv fajla"""
    safe = "".join([c for c in title if c.isalnum() or c in (' ', '-', '_')]).strip()
    safe = safe.replace(' ', '_')
    safe = re.sub(r'_+', '_', safe)
    safe = safe.strip('_')
    if len(safe) > 100:
        safe = safe[:100]
    return safe

class DownloadSettingsScreen(ConfigListScreen, Screen):
    # Dodat žuti kvadrat i natpis na dnu ekrana
    skin = """
    <screen position="center,center" size="1920,1080" title="YouTube Downloader Settings" backgroundColor="#660033" flags="wfNoBorder">
        <eLabel position="0,0" size="1920,80" backgroundColor="#0f0f0f" zPosition="1" />
        <eLabel text="..:: YouTube Downloader Settings ::.." position="40,20" size="800,45" font="Regular;32" foregroundColor="#ffcc00" backgroundColor="#00000000" transparent="1" zPosition="2" />

        <eLabel position="40,110" size="1840,50" backgroundColor="#2a2a2a" zPosition="1" />
        <eLabel text="CONFIGURATION OPTIONS" position="60,120" size="400,30" font="Regular;24" foregroundColor="#00ffcc" backgroundColor="#00000000" transparent="1" zPosition="2" />

        <widget name="config" position="40,160" size="1840,750" scrollbarMode="showOnDemand" itemHeight="50" font="Regular;26" secondfont="Regular;26" foregroundColor="#ffffff" backgroundColor="#0f0f0f" transparent="1" zPosition="2" />

        <widget name="HelpWindow" position="0,0" size="1,1" zPosition="-1" transparent="1" />

        <eLabel position="0,960" size="1920,120" backgroundColor="#0f0f0f" zPosition="1" />

        <eLabel position="40,1000" size="30,30" backgroundColor="#ff1111" zPosition="2" />
        <widget source="key_red" render="Label" position="85,1000" size="300,35" font="Regular;26" foregroundColor="#ffffff" backgroundColor="#00000000" transparent="1" zPosition="2" halign="left" />

        <eLabel position="420,1000" size="30,30" backgroundColor="#11ff11" zPosition="2" />
        <widget source="key_green" render="Label" position="465,1000" size="300,35" font="Regular;26" foregroundColor="#ffffff" backgroundColor="#00000000" transparent="1" zPosition="2" halign="left" />

        <eLabel position="800,1000" size="30,30" backgroundColor="#ffff11" zPosition="2" />
        <widget source="key_yellow" render="Label" position="845,1000" size="350,35" font="Regular;26" foregroundColor="#ffffff" backgroundColor="#00000000" transparent="1" zPosition="2" halign="left" />
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session

        # Učitavanje podešavanja
        self.current_settings = {}
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    self.current_settings = json.load(f)
            except:
                pass

        self.saved_path = self.current_settings.get('download_path', '/hdd/movie/YouTube_Downloads/')

        # Lista standardnih opcija. Izbacili smo "custom" odavde jer ide na dugme
        self.path_choices = [
            ("/hdd/movie/YouTube_Downloads/", "HDD - /hdd/movie/YouTube_Downloads/"),
            ("/hdd/YouTube_Downloads/", "HDD - /hdd/YouTube_Downloads/"),
            ("/usb/movie/YouTube_Downloads/", "USB - /usb/movie/YouTube_Downloads/"),
            ("/media/hdd/YouTube_Downloads/", "Media HDD - /media/hdd/YouTube_Downloads/")
        ]

        # Ako je u JSON-u već neka skroz divlja custom putanja, privremeno je dodajemo u listu da se vidi na ekranu
        is_predefined = False
        for choice in self.path_choices:
            if choice[0] == self.saved_path:
                is_predefined = True
                break

        if not is_predefined:
            self.path_choices.append((self.saved_path, _("Custom: ") + self.saved_path))

        self.path_selector = ConfigSelection(choices=self.path_choices, default=self.saved_path)

        self.list = []
        ConfigListScreen.__init__(self, self.list, session=self.session)

        self["key_red"] = StaticText(_("Cancel"))
        self["key_green"] = StaticText(_("Save"))
        self["key_yellow"] = StaticText(_("Custom Path"))  # Natpis za žuto dugme

        # Mapiranje akcija - ŽUTO dugme otvara tastaturu
        self["setupActions"] = ActionMap(["SetupActions", "ColorActions"], {
            "red": self.keyCancel,
            "cancel": self.keyCancel,
            "green": self.keySave,
            "ok": self.keySave,
            "yellow": self.openCustomKeyboard  # <--- ŽUTO dugme mapirano ovde
        }, -1)

        self.createSetup()

    def createSetup(self):
        self.list = []
        self.list.append(getConfigListEntry(_("Download Path:"), self.path_selector))
        self["config"].list = self.list
        self["config"].l.setList(self.list)

    def openCustomKeyboard(self):
        # Odmah otvara virtuelnu tastaturu sa trenutno aktivnom putanjom
        current_val = self.path_selector.value
        self.session.openWithCallback(self.virtualKeyBoardCallback, VirtualKeyBoard,
                                      title=_("Enter Your Custom Download Path:"), text=current_val)

    def virtualKeyBoardCallback(self, callback):
        # Kada korisnik lupi OK na tastaturi, dodajemo tu putanju u selektor i automatski je biramo
        if callback:
            new_path = callback
            if not new_path.endswith('/'):
                new_path += '/'

            # Dinamički dodajemo novu custom putanju u izbor i selektujemo je
            self.path_choices = [
                ("/hdd/movie/YouTube_Downloads/", "HDD - /hdd/movie/YouTube_Downloads/"),
                ("/hdd/YouTube_Downloads/", "HDD - /hdd/YouTube_Downloads/"),
                ("/usb/movie/YouTube_Downloads/", "USB - /usb/movie/YouTube_Downloads/"),
                ("/media/hdd/YouTube_Downloads/", "Media HDD - /media/hdd/YouTube_Downloads/"),
                (new_path, _("Custom: ") + new_path)
            ]
            self.path_selector.setChoices(self.path_choices)
            self.path_selector.value = new_path
            self.createSetup()

    def keySave(self):
        final_path = self.path_selector.value
        if final_path and not final_path.endswith('/'):
            final_path += '/'

        settings_data = {}
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    settings_data = json.load(f)
            except:
                pass

        settings_data['download_path'] = final_path

        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(settings_data, f, indent=4)
            print(f"[CiefpYouTube] Settings saved via Button. Path: {final_path}")
        except Exception as e:
            print(f"[CiefpYouTube] Error saving settings: {e}")

        self.close(True)

    def keyCancel(self):
        self.close(False)

class DownloadManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DownloadManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.queue = []
        self.current_download = None
        self.is_downloading = False
        self.callback = None
        self.total_count = 0
        self.completed_count = 0
        
    def add_to_queue(self, videos, format_type, callback=None):
        self.queue = []
        for video in videos:
            self.queue.append({
                'url': video.get('url'),
                'title': video.get('title', 'Unknown'),
                'format': format_type
            })
        self.total_count = len(self.queue)
        self.completed_count = 0
        self.callback = callback
        self.start_next_download()
    
    def start_next_download(self):
        if self.is_downloading:
            return
        
        if not self.queue:
            self.is_downloading = False
            if self.callback:
                self.callback('complete', None, None, self.total_count, self.completed_count)
            return
        
        self.is_downloading = True
        self.current_download = self.queue.pop(0)
        
        if self.callback:
            self.callback('start', self.current_download['title'], 
                         self.completed_count + 1, self.total_count, None)
        
        thread = threading.Thread(target=self._download_thread, daemon=True)
        thread.start()
    
    def _download_thread(self):
        video = self.current_download
        url = video['url']
        title = video['title']
        format_type = video['format']
        
        download_path = get_download_path()
        safe_title = get_safe_filename(title)
        
        if format_type == 'mp3':
            output_template = os.path.join(download_path, f"{safe_title}.%(ext)s")
            cmd = [
                'yt-dlp',
                '-f', 'bestaudio',
                '--extract-audio',
                '--audio-format', 'mp3',
                '--audio-quality', '0',
                '-o', output_template,
                '--no-warnings',
                '--no-progress',
                '--restrict-filenames',
                url
            ]
            extension = 'mp3'
        else:
            output_template = os.path.join(download_path, f"{safe_title}.%(ext)s")
            cmd = [
                'yt-dlp',
                '-f', 'best[ext=mp4]/best',
                '-o', output_template,
                '--no-warnings',
                '--no-progress',
                '--restrict-filenames',
                url
            ]
            extension = 'mp4'
        
        try:
            print(f"[DownloadManager] Starting: {title}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                downloaded_file = None
                for f in os.listdir(download_path):
                    if safe_title in f and f.endswith(extension):
                        downloaded_file = os.path.join(download_path, f)
                        break
                
                log_download(url, title, downloaded_file, success=True)
                self.completed_count += 1
                
                if self.callback:
                    self.callback('progress', title, self.completed_count, self.total_count, downloaded_file)
            else:
                error_msg = result.stderr[:200] if result.stderr else "Unknown error"
                log_download(url, title, "", success=False, error_msg=error_msg)
                self.completed_count += 1
                if self.callback:
                    self.callback('error', title, self.completed_count, self.total_count, error_msg)
                    
        except subprocess.TimeoutExpired:
            log_download(url, title, "", success=False, error_msg="Download timeout")
            self.completed_count += 1
            if self.callback:
                self.callback('error', title, self.completed_count, self.total_count, "Timeout")
        except Exception as e:
            log_download(url, title, "", success=False, error_msg=str(e)[:100])
            self.completed_count += 1
            if self.callback:
                self.callback('error', title, self.completed_count, self.total_count, str(e)[:100])
        
        self.is_downloading = False
        self.start_next_download()
    
    def cancel_all(self):
        self.queue = []
        self.is_downloading = False
        self.current_download = None


class YouTubeDownloaderScreen(Screen):
    """Glavni ekran za download menadžer"""
    
    # Pojednostavljen skin bez emoji koji izazivaju probleme
    skin = """
        <screen position="center,center" size="1920,1080" title="YouTube Download Manager" backgroundColor="#660033" flags="wfNoBorder">
            <eLabel position="0,0" size="1920,80" backgroundColor="#0f0f0f" zPosition="1" />
            <widget name="title" position="40,20" size="800,45" font="Regular;32" foregroundColor="#ffcc00" backgroundColor="#00000000" transparent="1" zPosition="2" />

            <eLabel position="40,110" size="900,50" backgroundColor="#2a2a2a" zPosition="1" />
            <eLabel text="PLAYLISTS / CONTENT" position="60,120" size="400,30" font="Regular;24" foregroundColor="#00ffcc" backgroundColor="#00000000" transparent="1" zPosition="2" />
            <widget name="left_list" position="40,160" size="900,600" scrollbarMode="showOnDemand" itemHeight="50" font="Regular;24" foregroundColor="#ffffff" backgroundColor="#0f0f0f" zPosition="2" />

            <eLabel position="980,110" size="900,50" backgroundColor="#2a2a2a" zPosition="1" />
            <eLabel text="SELECTED FILES" position="1000,120" size="400,30" font="Regular;24" foregroundColor="#00ffcc" backgroundColor="#00000000" transparent="1" zPosition="2" />
            <widget name="right_list" position="980,160" size="900,600" scrollbarMode="showOnDemand" itemHeight="50" font="Regular;24" foregroundColor="#ffffff" backgroundColor="#0f0f0f" zPosition="2" />

            <eLabel position="40,790" size="1840,140" backgroundColor="#2a2a2a" zPosition="1" />

            <eLabel position="60,810" size="1800,20" backgroundColor="#000000" zPosition="2" />
            <widget name="progress_bar" position="60,810" size="1800,20" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/CiefpYouTube/icons/progress.png" backgroundColor="#0d0c0c" zPosition="3" />

            <widget name="status_line1" position="60,845" size="1300,35" font="Regular;24" foregroundColor="#dbfc00" backgroundColor="#00000000" transparent="1" halign="left" zPosition="4" />
            <widget name="status_line2" position="60,885" size="1300,30" font="Regular;24" foregroundColor="#00ff0d" backgroundColor="#00000000" transparent="1" halign="left" zPosition="4" />

            <widget name="info" position="1380,845" size="480,45" font="Regular;24" halign="right" foregroundColor="#ffcc00" backgroundColor="#00000000" transparent="1" zPosition="4" />

            <eLabel position="0,960" size="1920,120" backgroundColor="#0f0f0f" zPosition="1" />

            <eLabel position="40,1000" size="30,30" backgroundColor="#ff1111" zPosition="2" />
            <widget source="key_red" render="Label" position="85,1000" size="300,35" font="Regular;26" foregroundColor="#ffffff" backgroundColor="#00000000" transparent="1" zPosition="2" halign="left" />

            <eLabel position="420,1000" size="30,30" backgroundColor="#11ff11" zPosition="2" />
            <widget source="key_green" render="Label" position="465,1000" size="300,35" font="Regular;26" foregroundColor="#ffffff" backgroundColor="#00000000" transparent="1" zPosition="2" halign="left" />

            <eLabel position="820,1000" size="30,30" backgroundColor="#ffff11" zPosition="2" />
            <widget source="key_yellow" render="Label" position="865,1000" size="300,35" font="Regular;26" foregroundColor="#ffffff" backgroundColor="#00000000" transparent="1" zPosition="2" halign="left" />

            <eLabel position="1220,1000" size="30,30" backgroundColor="#1111ff" zPosition="2" />
            <widget source="key_blue" render="Label" position="1265,1000" size="400,35" font="Regular;26" foregroundColor="#ffffff" backgroundColor="#00000000" transparent="1" zPosition="2" halign="left" />
        </screen>
    """

    def __init__(self, session, selected_videos=None):
        Screen.__init__(self, session)
        self.session = session
        self.selected_videos = selected_videos or []
        self.focus = "left"
        self.is_downloading = False
        self.download_queue = []
        self.current_process = None
        self.download_index = 0
        self.download_manager = DownloadManager()
        # Liste datoteka
        self.left_menu_list = []
        self.right_menu_list = []

        # Definisanje Enigma2 komponenti za Skin
        self["left_list"] = MenuList(self.left_menu_list)
        self["right_list"] = MenuList(self.right_menu_list)
        self["title"] = Label(_("..:: YouTube Download Manager ::.."))
        self["info"] = Label("")

        # NOVE STATUSNE LINIJE I PROGRESS BAR USKLAĐENI SA SKINOM
        self["progress_bar"] = ProgressBar()
        self["status_line1"] = Label(_("Idle... Waiting for download task."))
        self["status_line2"] = Label("")

        # IZVORI ZA DUGMIĆE U BOJI (StaticText)
        self["key_red"] = StaticText(_("Exit"))
        self["key_green"] = StaticText(_("Settings"))
        self["key_yellow"] = StaticText(_("Download"))
        self["key_blue"] = StaticText(_("Play & Download"))

        # Akcije tastera - potpuno ispravljene prema tvojim funkcijama u kodu
        self["actions"] = ActionMap(["SetupActions", "ColorActions", "DirectionActions"], {
            "cancel": self.exit,
            "ok": self.select_item,
            "red": self.exit,
            "green": self.open_settings,
            "yellow": self.download_selected,
            "blue": self.play_and_download,
            "left": self.focus_left,
            "right": self.focus_right,
            "up": self.left_up,
            "down": self.left_down
        }, -1)

        self.onLayoutFinish.append(self.layoutFinished)

        # Tajmer za osvežavanje loga/progresa tokom preuzimanja

        self.onLayoutFinish.append(self.layoutFinished)

    def open_settings(self):
        if self.is_downloading:
            self.session.open(MessageBox, _("Cannot change settings while downloading!"), MessageBox.TYPE_ERROR)
            return
        # Promenjeno sa self.settings_closed na self.settingsCallback
        self.session.openWithCallback(self.settingsCallback, DownloadSettingsScreen)

    def settingsCallback(self, changed=False):  # <--- Dodaj =False kao osiguranje
        # Tvoj postojeći kod unutar funkcije (npr. self.update_info() ili refresh)
        self.update_info()

    def left_up(self):
        if self.focus == "left":
            self["left_list"].up()
        else:
            self["right_list"].up()
    
    def left_down(self):
        if self.focus == "left":
            self["left_list"].down()
        else:
            self["right_list"].down()
    
    def focus_left(self):
        self.focus = "left"
        self.update_info()
    
    def focus_right(self):
        self.focus = "right"
        self.update_info()
    
    def load_playlists(self):
        """Učitava sve JSON plejliste"""
        self.playlists = []
        
        if not os.path.exists(PLAYLISTS_DIR):
            os.makedirs(PLAYLISTS_DIR)
            self["left_list"].setList([("No playlists found", None)])
            return
        
        try:
            files = [f for f in os.listdir(PLAYLISTS_DIR) if f.endswith('.json')]
            files.sort(key=lambda x: os.path.getmtime(os.path.join(PLAYLISTS_DIR, x)), reverse=True)
            
            for f in files:
                filepath = os.path.join(PLAYLISTS_DIR, f)
                try:
                    with open(filepath, 'r') as file:
                        data = json.load(file)
                        playlist_name = data.get('playlist_name', f.replace('.json', ''))
                        self.playlists.append({
                            'name': playlist_name,
                            'file': f,
                            'filepath': filepath,
                            'data': data
                        })
                except:
                    self.playlists.append({
                        'name': f.replace('.json', ''),
                        'file': f,
                        'filepath': filepath,
                        'data': None
                    })
            
            menu_list = [(f">> {p['name']}", p) for p in self.playlists]
            menu_list.insert(0, ("-" * 40, "separator"))
            menu_list.insert(0, ("ALL PLAYLISTS (click to open)", "header"))
            self["left_list"].setList(menu_list)
            
        except Exception as e:
            print(f"[DownloadManager] Error: {e}")
            self["left_list"].setList([("Error loading playlists", None)])
    
    def load_playlist_content(self, playlist):
        """Učitava sadržaj selektovane plejliste"""
        self.current_playlist = playlist
        self.current_playlist_name = playlist['name']
        self.current_playlist_videos = []
        
        data = playlist.get('data')
        if not data and playlist.get('filepath'):
            try:
                with open(playlist['filepath'], 'r') as f:
                    data = json.load(f)
            except:
                pass
        
        if data and 'videos' in data:
            self.current_playlist_videos = data['videos']
        
        if self.current_playlist_videos:
            menu_list = []
            menu_list.append(("<< BACK to playlists", "back"))
            menu_list.append(("-" * 40, "separator"))
            for idx, video in enumerate(self.current_playlist_videos):
                title = video.get('title', 'Unknown')[:60]
                menu_list.append((f"[{idx+1}] {title}", idx))
            self["left_list"].setList(menu_list)
        else:
            self["left_list"].setList([("No videos in this playlist", None), ("<< BACK", "back")])
    
    def select_item(self):
        """Selektuje stavku - OK dugme"""
        if self.is_downloading:
            return
        
        if self.focus == "left":
            current = self["left_list"].getCurrent()
            if not current:
                return
            
            value = current[1]
            
            if value == "back":
                self.load_playlists()
                return
            
            if value == "separator" or value == "header":
                return
            
            if isinstance(value, dict) and 'name' in value:
                self.load_playlist_content(value)
                return
            
            if isinstance(value, int) and value < len(self.current_playlist_videos):
                video = self.current_playlist_videos[value]
                
                exists = False
                for v in self.selected_videos:
                    if v.get('url') == video.get('url'):
                        exists = True
                        break
                
                if not exists:
                    self.selected_videos.append(video)
                    self.refresh_right_panel()
                    self.update_info()
        
        elif self.focus == "right":
            current = self["right_list"].getCurrent()
            if current and current[1] is not None:
                if current[1] == "clear":
                    self.selected_videos = []
                    self.refresh_right_panel()
                    self.update_info()
                elif isinstance(current[1], int):
                    idx = current[1]
                    if idx < len(self.selected_videos):
                        self.selected_videos.pop(idx)
                        self.refresh_right_panel()
                        self.update_info()
    
    def refresh_right_panel(self):
        """Osvježava desni panel"""
        if not self.selected_videos:
            self["right_list"].setList([("No files selected", None)])
            return
        
        menu_list = []
        for idx, video in enumerate(self.selected_videos):
            title = video.get('title', 'Unknown')[:50]
            menu_list.append((f"[{idx+1}] {title}", idx))
        
        menu_list.append(("-" * 40, "separator"))
        menu_list.append(("Clear all selected", "clear"))
        
        self["right_list"].setList(menu_list)
    
    def download_selected(self):
        """Pokreće download selektovanih fajlova"""
        if not self.selected_videos:
            self.session.open(MessageBox, "No files selected! Use OK to add files.", MessageBox.TYPE_INFO)
            return
        
        if self.is_downloading:
            self.session.open(MessageBox, "Download already in progress! Please wait.", MessageBox.TYPE_INFO)
            return
        
        choices = [
            ("Download as MP4 (Video)", "mp4"),
            ("Download as MP3 (Audio)", "mp3")
        ]
        self.session.openWithCallback(self.download_format_callback, ChoiceBox, title="Select download format:", list=choices)
    
    def download_format_callback(self, answer):
        if not answer:
            return
        format_type = answer[1]
        self.start_download(format_type)
    
    def start_download(self, format_type):
        """Pokreće download"""
        self.is_downloading = True
        self.download_manager.add_to_queue(
            self.selected_videos.copy(),
            format_type,
            self.download_callback
        )
    
    def download_callback(self, event, title, current, total, extra):
        """Callback za praćenje downloada"""
        from twisted.internet import reactor
        
        if event == 'start':
            reactor.callFromThread(self.update_status_start, title, current, total)
        elif event == 'progress':
            reactor.callFromThread(self.update_status_progress, title, current, total, extra)
        elif event == 'error':
            reactor.callFromThread(self.update_status_error, title, current, total, extra)
        elif event == 'complete':
            reactor.callFromThread(self.download_complete, current, total)

    def update_status_start(self, title, current, total):
        percent = int((current - 1) / total * 100) if total > 0 else 0
        self["status_line1"].setText("DOWNLOADING: " + title[:60] + "...")
        self["status_line2"].setText(
            "Progress: " + str(current) + " of " + str(total) + " files (" + str(percent) + "%)")

        # Postavljanje procenta na progress bar (od 0 do 100)
        self["progress_bar"].setValue(percent)

    def update_status_progress(self, title, current, total, filepath):
        percent = int(current / total * 100) if total > 0 else 0
        short_path = filepath.split('/')[-1] if filepath else "unknown"
        self["status_line1"].setText("COMPLETED: " + title[:60])
        self["status_line2"].setText(
            "Progress: " + str(current) + " of " + str(total) + " files (" + str(percent) + "%) | Saved: " + short_path)

        # Postavljanje punog napretka za završen fajl
        self["progress_bar"].setValue(percent)

    def update_status_error(self, title, current, total, error):
        percent = int(current / total * 100) if total > 0 else 0
        self["status_line1"].setText("FAILED: " + title[:60])
        self["status_line2"].setText(
            "Error: " + error + " | " + str(current) + " of " + str(total) + " files (" + str(percent) + "%)")

        # Čak i ako pukne, pomeri progres do te tačke
        self["progress_bar"].setValue(percent)

    def download_complete(self, current, total):
        self.is_downloading = False
        self["status_line1"].setText("ALL DOWNLOADS COMPLETED!")
        self["status_line2"].setText("Successfully downloaded " + str(total) + " file(s) to " + get_download_path())
        self.update_info()
    
    def play_and_download(self):
        """Play & Download"""
        if not self.selected_videos:
            self.session.open(MessageBox, "No files selected! Use OK to add files.", MessageBox.TYPE_INFO)
            return
        
        choices = [
            ("Play & Download as MP4", "mp4"),
            ("Play & Download as MP3", "mp3")
        ]
        self.session.openWithCallback(self.play_download_callback, ChoiceBox, title="Play and Download:", list=choices)
    
    def play_download_callback(self, answer):
        if not answer:
            return
        
        format_type = answer[1]
        first_video = self.selected_videos[0]
        
        self.start_download(format_type)
        
        from .shortsplayer import CiefpShortsPlayer
        self.session.open(CiefpShortsPlayer, [first_video])
        self.close()
    
    def update_info(self):
        count = len(self.selected_videos)
        focus_text = "LEFT" if self.focus == "left" else "RIGHT"
        download_path = get_download_path()
        short_path = download_path.split('/')[-2] if download_path.endswith('/') else download_path.split('/')[-1]
        self["info"].setText(focus_text + " | " + short_path + " | " + str(count) + " file(s)")

    def layoutFinished(self):
        self.load_playlists()
        self.refresh_right_panel()
        self.update_info()
    
    def exit(self):
        if self.is_downloading:
            self.session.openWithCallback(self.confirm_exit, MessageBox, 
                                         "Download in progress! Are you sure you want to exit?", 
                                         MessageBox.TYPE_YESNO)
        else:
            self.close()
    
    def confirm_exit(self, answer):
        if answer:
            self.download_manager.cancel_all()
            self.close()
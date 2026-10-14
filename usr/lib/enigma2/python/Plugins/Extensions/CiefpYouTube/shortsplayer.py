# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.ProgressBar import ProgressBar
from Screens.ChoiceBox import ChoiceBox
from enigma import eServiceReference, eTimer
import subprocess
import datetime
import os
import time
import threading
import json
from Components.config import ConfigSelection, getConfigListEntry

SETTINGS_FILE = "/usr/lib/enigma2/python/Plugins/Extensions/CiefpYouTube/settings.json"
BROKEN_LINKS_LOG = "/tmp/ciefp_youtube_broken_links.log"
YT_CACHE_FILE = "/tmp/ciefp_yt_cache.json"
CACHE_TTL = 5 * 3600


def _load_cache():
    try:
        if os.path.exists(YT_CACHE_FILE):
            with open(YT_CACHE_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {}


def _save_cache(cache):
    try:
        with open(YT_CACHE_FILE, 'w') as f:
            json.dump(cache, f)
    except:
        pass


def _extract_video_id(url):
    """Izvlači YouTube video ID iz URL-a."""
    import re
    m = re.search(r'(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})', url)
    return m.group(1) if m else url


def get_cached_url(url):
    """Vraća keširani direktni URL ako postoji i nije istekao."""
    cache = _load_cache()
    vid = _extract_video_id(url)
    entry = cache.get(vid)
    if entry:
        ts, direct = entry
        if time.time() - ts < CACHE_TTL:
            return direct
    return None


def set_cached_url(url, direct):
    cache = _load_cache()
    vid = _extract_video_id(url)
    cache[vid] = (time.time(), direct)
    now = time.time()
    cache = {k: v for k, v in cache.items() if now - v[0] < CACHE_TTL}
    _save_cache(cache)


def get_mini_skin_opacity():
    settings_file = "/usr/lib/enigma2/python/Plugins/Extensions/CiefpYouTube/settings.json"
    opacity_map = {
        '100': 'FF', '90': 'E6', '80': 'CC', '70': 'B3',
        '60': '99', '50': '80', '40': '66', '30': '4D',
        '20': '33', '10': '1A', '0': '00',
    }
    try:
        if os.path.exists(settings_file):
            with open(settings_file, 'r') as f:
                data = json.load(f)
                opacity = data.get('mini_skin_opacity', '50')
                return opacity_map.get(str(opacity), '80')
    except:
        pass
    return '80'


def load_quality_setting():
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                data = json.load(f)
                return data.get('quality', '720')
    except:
        pass
    return '720'


def get_video_format(quality):
    """Vraća format za yt-dlp koji daje JEDAN link (video+audio zajedno)."""
    if quality == "2160":
        return 'best[height<=2160][ext=mp4]/best[ext=mp4]/best'
    elif quality == "1080":
        return 'best[height<=1080][ext=mp4]/best[ext=mp4]/best'
    elif quality == "720":
        return 'best[height<=720][ext=mp4]/best[ext=mp4]/best'
    else:
        return 'best[ext=mp4]/best'


def get_player_type():
    settings_file = "/usr/lib/enigma2/python/Plugins/Extensions/CiefpYouTube/settings.json"
    try:
        if os.path.exists(settings_file):
            with open(settings_file, 'r') as f:
                data = json.load(f)
                return data.get('player_type', '4097')
    except:
        pass
    return '4097'


def get_webcam_timeout():
    settings_file = "/usr/lib/enigma2/python/Plugins/Extensions/CiefpYouTube/settings.json"
    try:
        if os.path.exists(settings_file):
            with open(settings_file, 'r') as f:
                data = json.load(f)
                return int(data.get('webcam_timeout', '20'))
    except:
        pass
    return 20


def log_broken_link(url, title, error_msg=""):
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(BROKEN_LINKS_LOG, 'a') as f:
            f.write(f"\n{'─'*80}\n")
            f.write(f"📅 [{timestamp}]\n")
            f.write(f"📺 TITLE: {title}\n")
            f.write(f"🔗 URL: {url}\n")
            if error_msg:
                f.write(f"⚠️ ERROR: {error_msg}\n")
            f.write(f"{'─'*80}\n")
    except:
        pass


def extract_with_ytdlp(url):
    """
    Ekstrahuje direktni stream URL koristeći yt-dlp subprocess.
    Forsira node kao JS runtime.
    Vraća (direct_url, error_msg).
    """
    quality = load_quality_setting()
    video_format = get_video_format(quality)

    try:
        cmd = [
            'yt-dlp',
            '-g',
            '-f', video_format,
            '--no-warnings',
            '--no-check-formats',
            '--js-runtimes', 'node',
            url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)

        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split('\n')[0], None

        # Fallback 1: best bez restrikcija
        cmd2 = [
            'yt-dlp', '-g', '-f', 'best',
            '--no-warnings', '--no-check-formats',
            '--js-runtimes', 'node', url
        ]
        r2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=90)
        if r2.returncode == 0 and r2.stdout.strip():
            return r2.stdout.strip().split('\n')[0], None

        err = (r2.stderr or result.stderr or "unknown")[:200]
        return None, err

    except subprocess.TimeoutExpired:
        return None, "timeout (>90s)"
    except Exception as e:
        return None, str(e)[:200]


# ============================================================
# CACHE MANAGER (singleton) - za auto-delete skinutih fajlova
# ============================================================
class CacheManager:
    """Prati reprodukciju skinutih fajlova i briše ih po završetku (ako je auto-delete).
    Singleton - jedna instanca za celu aplikaciju."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CacheManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.monitored_files = {}  # filepath -> {session, timer, last_position, stuck_count}

    def start_monitoring(self, filepath, session):
        """Počni da pratiš fajl - obriši ga kad reprodukcija završi."""
        if not filepath or not os.path.exists(filepath):
            print(f"[CacheManager] File not found: {filepath}")
            return

        print(f"[CacheManager] Monitoring: {filepath}")

        timer = eTimer()
        timer.callback.append(lambda: self._check_playback(filepath))

        self.monitored_files[filepath] = {
            'session': session,
            'timer': timer,
            'last_position': -1,
            'stuck_count': 0,
            'check_count': 0
        }

        timer.start(5000)  # svakih 5 sekundi

    def _check_playback(self, filepath):
        """Proveri da li je reprodukcija završena."""
        info = self.monitored_files.get(filepath)
        if not info:
            return

        session = info['session']
        info['check_count'] += 1

        try:
            service = session.nav.getCurrentService()

            if not service:
                info['stuck_count'] += 1
                # 2 provere bez servisa = reprodukcija završena
                if info['stuck_count'] >= 2:
                    self._handle_end(filepath)
                return

            seek = service.seek()
            if seek:
                position = seek.getPlayPosition()
                length = seek.getLength()

                if position and length:
                    try:
                        pos_secs = int(position[1] / 90000)
                        len_secs = int(length[1] / 90000)

                        # Ako je na kraju (u zadnjih 5s) - završeno
                        if len_secs > 0 and pos_secs >= len_secs - 5:
                            self._handle_end(filepath)
                            return

                        # Detekcija "stuck"
                        if pos_secs == info['last_position']:
                            info['stuck_count'] += 1
                            if info['stuck_count'] >= 6:  # 30s bez napretka
                                self._handle_end(filepath)
                                return
                        else:
                            info['stuck_count'] = 0

                        info['last_position'] = pos_secs
                    except:
                        pass

        except Exception as e:
            print(f"[CacheManager] Monitor error: {e}")

    def _handle_end(self, filepath):
        """Reprodukcija završena - odluči šta sa fajlom."""
        info = self.monitored_files.pop(filepath, None)
        if info and info['timer']:
            try:
                info['timer'].stop()
            except:
                pass

        # Proveri auto-delete opciju
        try:
            with open(SETTINGS_FILE, 'r') as f:
                data = json.load(f)
                auto_delete = data.get('auto_delete_cache', 'yes')
        except:
            auto_delete = 'yes'

        if auto_delete == 'yes':
            self._delete_file(filepath)
        elif auto_delete == 'ask':
            session = info['session'] if info else None
            if session:
                from Screens.MessageBox import MessageBox
                session.openWithCallback(
                    lambda ans: self._do_delete(ans, filepath),
                    MessageBox,
                    f"Delete downloaded file?\n\n{os.path.basename(filepath)}",
                    MessageBox.TYPE_YESNO
                )
        # 'no' - ostavi fajl

    def _delete_file(self, filepath):
        """Obriši fajl."""
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                print(f"[CacheManager] Deleted: {filepath}")
        except Exception as e:
            print(f"[CacheManager] Error deleting: {e}")

    def _do_delete(self, answer, filepath):
        if answer:
            self._delete_file(filepath)


# ============================================================
# CIEFP SHORTS PLAYER - izbor videa iz playliste
# ============================================================
class CiefpShortsPlayer(Screen):
    skin = """
        <screen position="center,center" size="1920,1080" title="CiefpYouTube Player" backgroundColor="#660033" flags="wfNoBorder">
            <eLabel position="0,0" size="1920,100" backgroundColor="#1a1a1a" zPosition="-1" />
            <eLabel text="..:: CiefpYouTube Browser ::.." position="60,25" size="600,50" font="Regular;40" foregroundColor="#ffffff" backgroundColor="#1a1a1a" transparent="1" />
            <widget name="menu" position="60,150" size="1800,800" scrollbarMode="showOnDemand" itemHeight="50" font="Regular;28" foregroundColor="#ffffff" backgroundColor="#2a2a2a" transparent="0" />
            <widget name="status" position="60,970" size="1800,40" font="Regular;24" foregroundColor="#ffcc00" backgroundColor="#660033" transparent="1" />
            <widget name="controls" position="60,1020" size="1800,40" font="Regular;20" foregroundColor="#03fc1c" backgroundColor="#660033" transparent="1" />
        </screen>
    """

    def __init__(self, session, playlist, webcam_mode=False, bouquet_version=""):
        Screen.__init__(self, session)
        self.session = session
        self.playlist = playlist
        self.index = 0
        self.webcam_mode = webcam_mode
        self.bouquet_version = bouquet_version

        if not self.webcam_mode and not self.bouquet_version:
            for video in playlist:
                if 'bouquet_version' in video:
                    self.bouquet_version = video.get('bouquet_version', '')
                    if self.bouquet_version:
                        self.webcam_mode = True
                        break

        self["status"] = Label("")
        self["controls"] = Label("▲/▼ Select | OK Options | EXIT Back")
        self.menu_list = []
        self["menu"] = MenuList(self.menu_list)

        self["actions"] = ActionMap(["SetupActions", "DirectionActions"], {
            "cancel": self.close,
            "ok": self.okClicked,
            "down": self["menu"].down,
            "up": self["menu"].up
        }, -1)

        self.populateMenu()

    def populateMenu(self):
        for video in self.playlist:
            self.menu_list.append(video.get('title', 'Unknown Video'))
        self["menu"].setList(self.menu_list)

    def okClicked(self):
        self.index = self["menu"].getSelectedIndex()
        current_video = self.playlist[self.index]

        if self.webcam_mode:
            # Webcam uvek ide preko ChoiceBox (single/playlist)
            choices = [
                ("Play this video only", "single"),
                ("Play entire playlist in sequence (Mini Skin)", "playlist")
            ]
            self.session.openWithCallback(self.webcam_choice_callback, ChoiceBox,
                                          title="Select playback mode:", list=choices)
            return

        # Učitaj default mode iz settings
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                mode = settings.get('playback_mode', 'ask')
        except:
            mode = 'ask'

        # Ako je "ask" - prikaži ChoiceBox
        if mode == 'ask':
            choices = [
                ("▶ Play 360p (stream, first time ~30s, then instant)", "stream_360"),
                ("▶ Play FHD 1080p (download first, ~20s)", "play_1080"),
                ("▶ Play HD 720p (download first, ~10s)", "play_720"),
                ("⬇ Download MP4", "download_mp4"),
                ("⬇ Download MP3", "download_mp3"),
                ("▶ Play entire playlist (360p stream)", "playlist"),
            ]
            self.session.openWithCallback(self.choiceCallback, ChoiceBox,
                                          title="Select playback mode:", list=choices)
            return

        # Inače - direktno primeni izabrani mode
        self._execute_playback_mode(mode, current_video)

    def _execute_playback_mode(self, mode, video):
        """Izvršava playback mode bez ChoiceBox-a."""
        if mode == "stream_360":
            self.closeAndPlay(video.get('url'), video.get('title', 'Video'))

        elif mode == "play_1080":
            self.session.open(PreDownloadPlayer, video, quality="1080")

        elif mode == "play_720":
            self.session.open(PreDownloadPlayer, video, quality="720")

        elif mode == "download_mp4":
            from .ytdownloader import YouTubeDownloaderScreen
            self.session.open(YouTubeDownloaderScreen, selected_videos=[video])

        elif mode == "download_mp3":
            from .ytdownloader import YouTubeDownloaderScreen
            self.session.open(YouTubeDownloaderScreen, selected_videos=[video])

        else:
            # Fallback - stream 360p
            self.closeAndPlay(video.get('url'), video.get('title', 'Video'))

    def webcam_choice_callback(self, answer):
        if answer:
            mode = answer[1]
            if mode == "single":
                current_video = self.playlist[self.index]
                url = current_video.get('url')
                title = current_video.get('title', 'Video')
                self.closeAndPlay(url, title)
            elif mode == "playlist":
                self.session.open(CiefpWebcamPlaylistPlayer, self.playlist, self.index, self.bouquet_version)

    def choiceCallback(self, answer):
        if not answer:
            return

        mode = answer[1]
        current_video = self.playlist[self.index]

        if mode == "stream_360":
            self.closeAndPlay(current_video.get('url'), current_video.get('title', 'Video'))

        elif mode == "play_1080":
            self.session.open(PreDownloadPlayer, current_video, quality="1080")

        elif mode == "play_720":
            self.session.open(PreDownloadPlayer, current_video, quality="720")

        elif mode == "download_mp4":
            from .ytdownloader import YouTubeDownloaderScreen
            self.session.open(YouTubeDownloaderScreen, selected_videos=[current_video])

        elif mode == "download_mp3":
            from .ytdownloader import YouTubeDownloaderScreen
            self.session.open(YouTubeDownloaderScreen, selected_videos=[current_video])

        elif mode == "playlist":
            self.session.open(CiefpPlaylistPlayer, self.playlist, self.index)

    def closeAndPlay(self, orig_url, title):
        """Pusti stream preko našeg extract_with_ytdlp (u thread-u, sa node).
        Ne koristi YT-DLP:// protokol jer on blokira glavni thread i koristi quickjs."""
        # Proveri keš
        cached = get_cached_url(orig_url)
        if cached:
            print(f"[CiefpYouTube] Using cached URL for {title[:40]}")
            self._play_direct_url(cached, title)
            return

        # Nema keša - ekstrahuj u thread-u
        self["status"].setText("Extracting stream URL (please wait)...")

        def worker():
            direct, err = extract_with_ytdlp(orig_url)
            from twisted.internet import reactor
            if direct:
                set_cached_url(orig_url, direct)
                reactor.callFromThread(self._play_direct_url, direct, title)
            else:
                reactor.callFromThread(self._play_error_short, orig_url, title, err)

        threading.Thread(target=worker, daemon=True).start()

    def _play_direct_url(self, direct_url, title):
        """Pusti već ekstrahovani direktni URL."""
        try:
            player_type = get_player_type()
            print(f"[CiefpYouTube] Playing direct URL - player_type: '{player_type}'")

            if player_type == "movieplayer":
                from Screens.InfoBar import MoviePlayer
                ref = eServiceReference(4097, 0, direct_url)
                ref.setName(title)
                self.session.openWithCallback(self.close, MoviePlayer, ref)
            elif player_type == "5001":
                self.close()
                time.sleep(0.3)
                ref = eServiceReference(5001, 0, direct_url)
                ref.setName(title)
                self.session.nav.playService(ref)
            elif player_type == "5002":
                self.close()
                time.sleep(0.3)
                ref = eServiceReference(5002, 0, direct_url)
                ref.setName(title)
                self.session.nav.playService(ref)
            else:  # 4097
                self.close()
                time.sleep(0.3)
                ref = eServiceReference(4097, 0, direct_url)
                ref.setName(title)
                self.session.nav.playService(ref)
        except Exception as e:
            print(f"[CiefpYouTube] Error in _play_direct_url: {e}")

    def _play_error_short(self, orig_url, title, err):
        """Fallback ako ekstrakcija ne uspe."""
        print(f"[CiefpYouTube] Extraction failed: {err}")
        log_broken_link(orig_url, title, str(err)[:100])
        self["status"].setText(f"Error: {str(err)[:50]}")


# ============================================================
# CIEFP PLAYLIST PLAYER - sekvencijalna reprodukcija playliste
# ============================================================
class CiefpPlaylistPlayer(Screen):
    def __init__(self, session, playlist, start_index=0):
        alpha_hex = get_mini_skin_opacity()
        self.skin = f"""
        <screen position="center,0" size="1920,160" title="CiefpYouTube Playlist" backgroundColor="#ff000000" flags="wfNoBorder">
            <eLabel position="0,0" size="1920,160" backgroundColor="#{alpha_hex}00000e" zPosition="1" />
            <eLabel text="NOW PLAYING:" position="50,20" size="180,40" font="Regular;22" foregroundColor="#ffffff" backgroundColor="#00000000" transparent="1" zPosition="2" />
            <widget name="title" position="240,15" size="1630,50" font="Regular;30" foregroundColor="#ffffff" backgroundColor="#{alpha_hex}00000e" transparent="1" zPosition="2" />
            <eLabel text="NEXT:" position="50,75" size="180,40" font="Regular;20" foregroundColor="#ffffff" backgroundColor="#00000000" transparent="1" zPosition="2" />
            <widget name="next_title" position="240,72" size="1200,40" font="Regular;24" foregroundColor="#ffcc00" backgroundColor="#{alpha_hex}00000e" transparent="1" zPosition="2" />
            <widget name="playlist_info" position="50,120" size="300,30" font="Regular;22" foregroundColor="#00ffcc" backgroundColor="transparent" transparent="1" zPosition="2" />
            <widget name="status" position="900,120" size="500,30" font="Regular;22" halign="right" foregroundColor="#ffcc00" backgroundColor="transparent" transparent="1" zPosition="2" />    
            <widget name="controls" position="240,120" size="700,30" font="Regular;22" foregroundColor="#03fc1c" backgroundColor="#{alpha_hex}00000e" transparent="1" zPosition="2" />
            <widget name="duration" position="1400,115" size="180,40" font="Regular;30" halign="right" foregroundColor="#00ffcc" backgroundColor="transparent" transparent="1" zPosition="2"/>
            <widget name="time" position="1600,110" size="300,50" font="Regular;36" halign="right" foregroundColor="#ffffff" backgroundColor="transparent" transparent="1" zPosition="2"/>
        </screen>
        """
        Screen.__init__(self, session)
        self.playlist = playlist
        self.index = start_index
        self.play_count = 0

        self["title"] = Label("Loading...")
        self["next_title"] = Label("")
        self["status"] = Label("")
        self["playlist_info"] = Label("")
        self["controls"] = Label("OK: Pause | ▲/▼: Previous/Next | EXIT: Exit playlist")
        self["time"] = Label("")
        self["duration"] = Label("--:--")

        self["actions"] = ActionMap(["SetupActions", "DirectionActions"], {
            "cancel": self.handleExit,
            "ok": self.pauseToggle,
            "down": self.nextVideo,
            "up": self.prevVideo
        }, -1)

        self.time_timer = eTimer()
        self.time_timer.callback.append(self.updateTime)
        self.time_timer.start(1000)

        self.playlist_timer = eTimer()
        try:
            self.playlist_timer.callback.append(self.playlistTimerCallback)
        except:
            self.playlist_timer.timeout.connect(self.playlistTimerCallback)

        self.startExtraction()

    def updateTime(self):
        try:
            import time
            self["time"].setText(time.strftime("%H:%M:%S"))
        except:
            pass

    def startExtraction(self):
        self.playlist_timer.stop()
        self.play_count = 0
        if self.index >= len(self.playlist):
            self.handleExit()
            return

        current_video = self.playlist[self.index]
        url = current_video.get('url')
        title = current_video.get('title', 'Video')
        self["title"].setText(title)

        if self.index + 1 < len(self.playlist):
            self["next_title"].setText(self.playlist[self.index + 1].get('title', ''))
        else:
            self["next_title"].setText("End playlist")

        self["playlist_info"].setText(f"Song: {self.index + 1} of {len(self.playlist)}")

        # Preload SAMO sledeći video
        if self.index + 1 < len(self.playlist):
            self.preload_next(self.playlist, self.index + 1)

        # Provjeri keš za trenutni video
        cached = get_cached_url(url)
        if cached:
            self._play_direct(cached, title)
            return

        self["status"].setText("Extracting...")

        def worker():
            direct, err = extract_with_ytdlp(url)
            from twisted.internet import reactor
            if direct:
                set_cached_url(url, direct)
                reactor.callFromThread(self._play_direct, direct, title)
            else:
                reactor.callFromThread(self._play_error, url, title, err)

        threading.Thread(target=worker, daemon=True).start()

    def preload_next(self, playlist, next_index):
        """Preload samo sledećeg videa."""
        def worker():
            if next_index >= len(playlist):
                return
            video = playlist[next_index]
            url = video.get('url')
            if not url:
                return
            if get_cached_url(url):
                return
            direct, err = extract_with_ytdlp(url)
            if direct:
                set_cached_url(url, direct)
                print(f"[CiefpYouTube] Preloaded next: {video.get('title', '')[:40]}")
        threading.Thread(target=worker, daemon=True).start()

    def _play_direct(self, direct_url, title):
        try:
            ref = eServiceReference(4097, 0, direct_url)
            ref.setName(title)
            self.session.nav.playService(ref)
            self["status"].setText("")
            self.playlist_timer.start(1000, False)
        except Exception as e:
            print(f"[CiefpYouTube] Error: {e}")
            self.showError(str(e)[:30])

    def _play_error(self, orig_url, title, err):
        print(f"[CiefpYouTube] Extract failed: {err}; using YT-DLP:// fallback")
        log_broken_link(orig_url, title, str(err)[:100])
        try:
            yt_service_url = f"YT-DLP://{orig_url}"
            ref = eServiceReference(4097, 0, yt_service_url)
            ref.setName(title)
            self.session.nav.playService(ref)
            self["status"].setText("")
            self.playlist_timer.start(1000, False)
        except Exception as e:
            self.showError(str(e)[:30])

    def playlistTimerCallback(self):
        self.play_count += 1
        if self.play_count < 2:
            return

        try:
            service = self.session.nav.getCurrentService()
            if not service:
                self.nextVideo()
                return

            seek = service.seek()
            if seek:
                length = seek.getLength()
                position = seek.getPlayPosition()
                if length and position:
                    length_secs = int(length[1] / 90000)
                    position_secs = int(position[1] / 90000)
                    if length_secs > 0 and length_secs < 43200:
                        remaining = length_secs - position_secs
                        if 0 <= remaining < 43200:
                            mins = int(remaining // 60)
                            secs = int(remaining % 60)
                            self["duration"].setText("-%02d:%02d" % (mins, secs))
                            if remaining <= 3:
                                self.nextVideo()
                                return
        except Exception as e:
            print(f"[CiefpYouTube] Timer error: {e}")

    def nextVideo(self):
        self.playlist_timer.stop()
        self["status"].setText("Loading next song...")
        if self.index < len(self.playlist) - 1:
            self.index += 1
            self.startExtraction()
        else:
            self.handleExit()

    def prevVideo(self):
        self.playlist_timer.stop()
        if self.index > 0:
            self.index -= 1
            self.startExtraction()

    def pauseToggle(self):
        try:
            service = self.session.nav.getCurrentService()
            if service and hasattr(service, 'pause'):
                service.pause()
                self["controls"].setText("PAUSED | OK: Continue | ▲/▼: Change | EXIT: Exit")
        except:
            pass

    def showError(self, error_msg):
        if hasattr(self, 'playlist') and self.index < len(self.playlist):
            current_video = self.playlist[self.index]
            log_broken_link(
                current_video.get('url', 'unknown'),
                current_video.get('title', 'unknown'),
                error_msg
            )
        self["title"].setText(f"Error: {error_msg}. Skipping...")
        self.nextVideo()

    def handleExit(self):
        self.playlist_timer.stop()
        self.session.nav.stopService()
        self.close()


# ============================================================
# CIEFP WEBCAM PLAYLIST PLAYER
# ============================================================
class CiefpWebcamPlaylistPlayer(Screen):
    def __init__(self, session, playlist, start_index=0, bouquet_version=""):
        alpha_hex = get_mini_skin_opacity()
        self.skin = f"""
        <screen position="center,0" size="1920,160" title="CiefpYouTube WebCam" backgroundColor="#ff000000" flags="wfNoBorder">
            <eLabel position="0,0" size="1920,160" backgroundColor="#{alpha_hex}00000e" zPosition="1" />
            <eLabel text="NOW PLAYING:" position="50,20" size="180,40" font="Regular;22" foregroundColor="#ffffff" backgroundColor="#00000000" transparent="1" zPosition="2" />
            <widget name="title" position="240,15" size="1630,50" font="Regular;30" foregroundColor="#ffffff" backgroundColor="#{alpha_hex}00000e" transparent="1" zPosition="2" />
            <eLabel text="NEXT:" position="50,75" size="180,40" font="Regular;20" foregroundColor="#ffffff" backgroundColor="#00000000" transparent="1" zPosition="2" />
            <widget name="next_title" position="240,72" size="1200,40" font="Regular;24" foregroundColor="#ffcc00" backgroundColor="#{alpha_hex}00000e" transparent="1" zPosition="2" />
            <widget name="playlist_info" position="50,120" size="300,30" font="Regular;22" foregroundColor="#00ffcc" backgroundColor="transparent" transparent="1" zPosition="2" />
            <widget name="bouquet_version" position="800,20" size="1000,30" font="Regular;24" halign="right" foregroundColor="#ffffff" backgroundColor="transparent" transparent="1" zPosition="2" />
            <widget name="status" position="900,120" size="500,30" font="Regular;22" halign="right" foregroundColor="#ffcc00" backgroundColor="transparent" transparent="1" zPosition="2" />    
            <widget name="controls" position="240,120" size="700,30" font="Regular;22" foregroundColor="#03fc1c" backgroundColor="#{alpha_hex}00000e" transparent="1" zPosition="2" />
            <widget name="time" position="1600,110" size="300,50" font="Regular;36" halign="right" foregroundColor="#ffffff" backgroundColor="transparent" transparent="1" zPosition="2"/>
        </screen>
        """
        Screen.__init__(self, session)
        self.session = session
        self.playlist = playlist
        self.index = start_index
        self.bouquet_version = bouquet_version
        self.webcam_timeout = get_webcam_timeout()
        self.auto_switch_timer = None
        self.countdown_timer = None
        self.countdown = 0
        self.is_paused = False
        self.is_loading = False

        self["title"] = Label("Loading...")
        self["next_title"] = Label("")
        self["status"] = Label("")
        self["playlist_info"] = Label("")
        self["controls"] = Label(f"🔴 WEBCAM | Auto-switch: {self.webcam_timeout}s | OK: Pause | ▲/▼: Skip | EXIT: Exit")
        self["time"] = Label("")
        version_text = bouquet_version[:100] if len(bouquet_version) > 100 else bouquet_version
        self["bouquet_version"] = Label(version_text)

        self["actions"] = ActionMap(["SetupActions", "DirectionActions"], {
            "cancel": self.handleExit,
            "ok": self.pauseToggle,
            "down": self.nextVideo,
            "up": self.prevVideo
        }, -1)

        self.time_timer = eTimer()
        self.time_timer.callback.append(self.updateTime)
        self.time_timer.start(1000)

        self.startExtraction()

    def updateTime(self):
        try:
            import time
            self["time"].setText(time.strftime("%H:%M:%S"))
        except:
            pass

    def startExtraction(self):
        if self.auto_switch_timer:
            self.auto_switch_timer.stop()
        if self.countdown_timer:
            self.countdown_timer.stop()

        if self.index >= len(self.playlist):
            self["status"].setText("End of playlist reached")
            self.handleExit()
            return

        current_video = self.playlist[self.index]
        url = current_video.get('url')
        title = current_video.get('title', 'Camera')

        self["title"].setText(f"⏳ Loading: {title}...")
        self["status"].setText("Loading stream...")
        self.is_loading = True

        if self.index + 1 < len(self.playlist):
            self.pending_next_title = self.playlist[self.index + 1].get('title', '')
        else:
            self.pending_next_title = self.playlist[0].get('title', '') if self.playlist else ""

        self["playlist_info"].setText(f"Camera: {self.index + 1} of {len(self.playlist)}")

        # Preload sledeće kamere
        if self.index + 1 < len(self.playlist):
            self.preload_next(self.playlist, self.index + 1)

        cached = get_cached_url(url)
        if cached:
            self._play_direct(cached, title)
            return

        def worker():
            direct, err = extract_with_ytdlp(url)
            from twisted.internet import reactor
            if direct:
                set_cached_url(url, direct)
                reactor.callFromThread(self._play_direct, direct, title)
            else:
                reactor.callFromThread(self._play_error, url, title, err)

        threading.Thread(target=worker, daemon=True).start()

    def preload_next(self, playlist, next_index):
        """Preload samo sledeće kamere."""
        def worker():
            if next_index >= len(playlist):
                return
            video = playlist[next_index]
            url = video.get('url')
            if not url:
                return
            if get_cached_url(url):
                return
            direct, err = extract_with_ytdlp(url)
            if direct:
                set_cached_url(url, direct)
                print(f"[CiefpYouTube] Preloaded next cam: {video.get('title', '')[:40]}")
        threading.Thread(target=worker, daemon=True).start()

    def _play_direct(self, direct_url, title):
        try:
            ref = eServiceReference(4097, 0, direct_url)
            ref.setName(title)
            self.session.nav.playService(ref)

            self["title"].setText(title)
            self["next_title"].setText(self.pending_next_title)
            self["status"].setText("")
            self.is_loading = False

            self.start_auto_switch_timer()
        except Exception as e:
            print(f"[CiefpYouTube] Error: {e}")
            self.is_loading = False
            self.showError(str(e)[:30])

    def _play_error(self, orig_url, title, err):
        print(f"[CiefpYouTube] WebCam extract failed: {err}; YT-DLP:// fallback")
        log_broken_link(orig_url, title, str(err)[:100])
        try:
            yt_service_url = f"YT-DLP://{orig_url}"
            ref = eServiceReference(4097, 0, yt_service_url)
            ref.setName(title)
            self.session.nav.playService(ref)
            self["title"].setText(title)
            self["next_title"].setText(self.pending_next_title)
            self["status"].setText("")
            self.is_loading = False
            self.start_auto_switch_timer()
        except Exception as e:
            self.is_loading = False
            self.showError(str(e)[:30])

    def start_auto_switch_timer(self):
        if self.auto_switch_timer:
            self.auto_switch_timer.stop()
        if self.countdown_timer:
            self.countdown_timer.stop()

        self.countdown = self.webcam_timeout
        self.countdown_timer = eTimer()
        try:
            self.countdown_timer.callback.append(self.update_countdown)
        except:
            self.countdown_timer.timeout.connect(self.update_countdown)
        self.countdown_timer.start(1000)

        self.auto_switch_timer = eTimer()
        try:
            self.auto_switch_timer.callback.append(self.auto_switch_callback)
        except:
            self.auto_switch_timer.timeout.connect(self.auto_switch_callback)
        self.auto_switch_timer.start(self.webcam_timeout * 1000, True)

    def update_countdown(self):
        if self.is_paused or self.is_loading:
            return
        if self.countdown > 0:
            self.countdown -= 1
            self["status"].setText(f"Next camera in: {self.countdown}s")
        else:
            if self.countdown_timer:
                self.countdown_timer.stop()

    def auto_switch_callback(self):
        if self.is_paused or self.is_loading:
            return
        self.nextVideo()

    def nextVideo(self):
        if self.is_loading:
            return

        if self.auto_switch_timer:
            self.auto_switch_timer.stop()
        if self.countdown_timer:
            self.countdown_timer.stop()
        self.is_paused = False

        if self.index >= len(self.playlist) - 1:
            self["status"].setText("End of playlist reached")
            self.handleExit()
            return

        self.is_loading = True
        self.index += 1
        self.startExtraction()

    def prevVideo(self):
        if self.is_loading:
            return

        if self.auto_switch_timer:
            self.auto_switch_timer.stop()
        if self.countdown_timer:
            self.countdown_timer.stop()
        self.is_paused = False

        self.is_loading = True

        if self.index > 0:
            self.index -= 1
        else:
            self.index = len(self.playlist) - 1

        self.startExtraction()

    def pauseToggle(self):
        try:
            service = self.session.nav.getCurrentService()
            if service and hasattr(service, 'pause'):
                service.pause()
                self.is_paused = not self.is_paused
                if self.is_paused:
                    if self.auto_switch_timer:
                        self.auto_switch_timer.stop()
                    if self.countdown_timer:
                        self.countdown_timer.stop()
                    self["controls"].setText("🔴 WEBCAM PAUSED | OK: Resume | ▲/▼: Skip | EXIT: Exit")
                    self["status"].setText("PAUSED")
                else:
                    self.start_auto_switch_timer()
                    self["controls"].setText(
                        f"🔴 WEBCAM | Auto-switch: {self.webcam_timeout}s | OK: Pause | ▲/▼: Skip | EXIT: Exit")
        except:
            pass

    def showError(self, error_msg):
        if hasattr(self, 'playlist') and self.index < len(self.playlist):
            current_video = self.playlist[self.index]
            log_broken_link(
                current_video.get('url', 'unknown'),
                current_video.get('title', 'unknown'),
                error_msg
            )
        self["title"].setText(f"Error: {error_msg}. Skipping...")
        self.is_loading = False
        self.nextVideo()

    def handleExit(self):
        if self.auto_switch_timer:
            self.auto_switch_timer.stop()
        if self.countdown_timer:
            self.countdown_timer.stop()
        self.session.nav.stopService()
        self.close()


# ============================================================
# PRE-DOWNLOAD PLAYER - skida FHD pa pušta
# ============================================================
class PreDownloadPlayer(Screen):
    """Screen koji skida FHD fajl preko yt-dlp pa ga pušta.
    Prikazuje progress bar dok skida, pa automatski startuje reprodukciju."""

    skin = """
        <screen position="center,center" size="1280,720" title="CiefpYouTube FHD Preload" backgroundColor="#660033" flags="wfNoBorder">
            <eLabel position="0,0" size="1280,100" backgroundColor="#1a1a1a" zPosition="-1" />
            <eLabel text="..:: CiefpYouTube FHD Preload ::.." position="40,25" size="800,50" font="Regular;32" foregroundColor="#ffcc00" backgroundColor="#1a1a1a" transparent="1" />

            <widget name="title_label" position="40,140" size="1200,60" font="Regular;28" foregroundColor="#ffffff" backgroundColor="#1a1a1a" transparent="1" />

            <eLabel position="40,220" size="1200,30" backgroundColor="#000000" zPosition="1" />
            <widget name="progress_bar" position="40,220" size="1200,30" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/CiefpYouTube/icons/progress.png" backgroundColor="#000000" zPosition="2" />

            <widget name="status" position="40,270" size="1200,40" font="Regular;24" foregroundColor="#00ffcc" backgroundColor="#1a1a1a" transparent="1" />
            <widget name="info" position="40,320" size="1200,40" font="Regular;22" foregroundColor="#ffcc00" backgroundColor="#1a1a1a" transparent="1" />

            <eLabel position="0,620" size="1280,100" backgroundColor="#1a1a1a" zPosition="-1" />
            <eLabel position="40,650" size="30,30" backgroundColor="#ff0000" zPosition="2" />
            <eLabel text="EXIT: Cancel download" position="85,650" size="600,40" font="Regular;24" foregroundColor="#ffffff" backgroundColor="#1a1a1a" transparent="1" />
        </screen>
    """

    def __init__(self, session, video, quality="1080"):
        Screen.__init__(self, session)
        self.session = session
        self.video = video
        self.quality = quality
        self.url = video.get('url')
        self.title = video.get('title', 'Unknown')
        self.download_path = self._get_cache_path()
        self.output_file = None
        self.download_process = None
        self.is_cancelled = False
        self.play_file_path = None

        self["title_label"] = Label(self.title[:80])
        self["progress_bar"] = ProgressBar()
        self["status"] = Label("Preparing download...")
        self["info"] = Label("")

        self["actions"] = ActionMap(["SetupActions"], {
            "cancel": self.cancel_download,
        }, -1)

        self.onLayoutFinish.append(self.start_download)

    # ==================== CACHE PATH ====================
    def _get_cache_path(self):
        """Uzima cache path iz settings, kreira folder ako ne postoji."""
        try:
            with open(SETTINGS_FILE, 'r') as f:
                data = json.load(f)
                path = data.get('cache_path', '/hdd/movie/YouTube_Cache/')
        except:
            path = '/hdd/movie/YouTube_Cache/'

        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except Exception as e:
                print(f"[PreDownloadPlayer] Cannot create {path}: {e}, using /tmp fallback")
                path = '/tmp/ciefp_yt_cache/'
                if not os.path.exists(path):
                    try:
                        os.makedirs(path)
                    except:
                        pass
        return path

    # ==================== DOWNLOAD ====================
    def start_download(self):
        """Pokreće download u pozadinskom thread-u (ne blokira UI)."""
        threading.Thread(target=self._download_worker, daemon=True).start()

    def _download_worker(self):
        """Thread koji skida fajl preko yt-dlp."""
        safe_title = self._safe_filename(self.title)
        self.output_file = os.path.join(self.download_path, f"{safe_title}.mp4")
        output_template = os.path.join(self.download_path, f"{safe_title}.%(ext)s")

        # Format prema kvalitetu - forsira H.264 (avc1) za Enigma2 kompatibilnost
        if self.quality == "1080":
            fmt = ('bestvideo[height<=1080][vcodec^=avc1]+bestaudio[ext=m4a]/'
                   'bestvideo[height<=1080][vcodec^=avc1]+bestaudio/'
                   'best[height<=1080][vcodec^=avc1]/best')
        elif self.quality == "720":
            fmt = ('bestvideo[height<=720][vcodec^=avc1]+bestaudio[ext=m4a]/'
                   'bestvideo[height<=720][vcodec^=avc1]+bestaudio/'
                   'best[height<=720][vcodec^=avc1]/best')
        else:
            fmt = 'best[height<=480]/best'

        cmd = [
            'yt-dlp',
            '-f', fmt,
            '--merge-output-format', 'mp4',
            '-o', output_template,
            '--no-warnings',
            '--newline',
            '--retries', '3',
            '--no-overwrites',
            '--no-playlist',
            '--js-runtimes', 'node',
            self.url
        ]

        try:
            from twisted.internet import reactor

            self.download_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )

            for line in self.download_process.stdout:
                if self.is_cancelled:
                    try:
                        self.download_process.kill()
                    except:
                        pass
                    return

                line = line.strip()

                if '[download]' in line and '%' in line:
                    try:
                        percent_str = line.split('%')[0].split()[-1]
                        percent = float(percent_str)
                        reactor.callFromThread(self.update_progress, percent, line)
                    except:
                        pass
                elif '[Merger]' in line:
                    reactor.callFromThread(self.update_status, "Merging video+audio (ffmpeg)...")
                elif '[download]' in line and 'Destination' in line:
                    reactor.callFromThread(self.update_status, "Starting download...")

            self.download_process.wait()

            if self.is_cancelled:
                return

            if os.path.exists(self.output_file):
                reactor.callFromThread(self.download_complete)
            else:
                found = False
                try:
                    for f in os.listdir(self.download_path):
                        if safe_title in f and (f.endswith('.mp4') or f.endswith('.mkv') or f.endswith('.webm')):
                            self.output_file = os.path.join(self.download_path, f)
                            found = True
                            break
                except:
                    pass

                if found:
                    reactor.callFromThread(self.download_complete)
                else:
                    reactor.callFromThread(self.download_failed, "Output file not found after download")

        except Exception as e:
            from twisted.internet import reactor
            reactor.callFromThread(self.download_failed, str(e)[:100])

    # ==================== UI CALLBACKS ====================
    def update_progress(self, percent, raw_line):
        self["progress_bar"].setValue(int(percent))
        try:
            if ' at ' in raw_line:
                speed_part = raw_line.split(' at ')[1].split(' ETA')[0].strip()
                self["info"].setText(f"Speed: {speed_part}")
        except:
            pass

    def update_status(self, text):
        self["status"].setText(text)

    def download_complete(self):
        """Download gotov - pusti fajl."""
        print("[PreDownloadPlayer-DEBUG] download_complete() CALLED")
        print(f"[PreDownloadPlayer-DEBUG] output_file = {self.output_file}")
        print(f"[PreDownloadPlayer-DEBUG] file exists = {os.path.exists(self.output_file) if self.output_file else 'N/A'}")

        self["status"].setText("Download complete! Starting playback...")
        self["progress_bar"].setValue(100)
        self["info"].setText("")

        # POZOVI DIREKTNO bez callLater
        print("[PreDownloadPlayer-DEBUG] Calling _play_file() directly...")
        self._play_file()

    def download_failed(self, error_msg):
        """Greška - prikaži i zatvori."""
        self["status"].setText(f"Download failed: {error_msg}")
        try:
            log_broken_link(self.url, self.title, f"PreDownload failed: {error_msg}")
        except:
            pass
        from twisted.internet import reactor
        reactor.callLater(3, self.close)

    # ==================== PLAYBACK ====================
    def _play_file(self):
        """Pusti skinuti fajl i pokreni CacheManager monitoring."""
        print("[PreDownloadPlayer-DEBUG] _play_file() CALLED")

        try:
            if not hasattr(self, 'output_file') or not self.output_file:
                print("[PreDownloadPlayer-DEBUG] ERROR: output_file not set!")
                self["status"].setText("Error: output file not found")
                return

            print(f"[PreDownloadPlayer-DEBUG] output_file = {self.output_file}")

            if not os.path.exists(self.output_file):
                print(f"[PreDownloadPlayer-DEBUG] ERROR: file does not exist: {self.output_file}")
                self["status"].setText("Error: file not found on disk")
                return

            try:
                size = os.path.getsize(self.output_file)
                print(f"[PreDownloadPlayer-DEBUG] file size = {size} bytes ({size / 1024 / 1024:.2f} MB)")
            except Exception as e:
                print(f"[PreDownloadPlayer-DEBUG] Cannot get file size: {e}")

            self.play_file_path = self.output_file

            player_type = get_player_type()
            print(f"[PreDownloadPlayer-DEBUG] player_type = '{player_type}'")

            # Zatvori screen PRE puštanja
            print("[PreDownloadPlayer-DEBUG] Closing screen BEFORE playService...")
            self.close()
            print("[PreDownloadPlayer-DEBUG] Screen closed")

            # Kratka pauza da se screen zatvori
            import time
            time.sleep(0.3)

            # Pusti fajl
            print(f"[PreDownloadPlayer-DEBUG] Creating eServiceReference(4097, 0, '{self.output_file}')")
            ref = eServiceReference(4097, 0, self.output_file)
            ref.setName(self.title)

            print("[PreDownloadPlayer-DEBUG] Calling session.nav.playService()...")
            self.session.nav.playService(ref)
            print("[PreDownloadPlayer-DEBUG] playService() returned OK")

            # CacheManager
            try:
                print("[PreDownloadPlayer-DEBUG] Starting CacheManager...")
                cache_mgr = CacheManager()
                cache_mgr.start_monitoring(self.play_file_path, self.session)
                print("[PreDownloadPlayer-DEBUG] CacheManager started")
            except Exception as e:
                print(f"[PreDownloadPlayer-DEBUG] CacheManager error: {e}")

        except Exception as e:
            print(f"[PreDownloadPlayer-DEBUG] EXCEPTION in _play_file: {e}")
            import traceback
            traceback.print_exc()
            
    # ==================== UTILS ====================
    def _safe_close(self):
        """Bezbedno zatvaranje screena - sprečava 'execing' grešku."""
        print("[PreDownloadPlayer-DEBUG] _safe_close() CALLED")
        try:
            self.close()
            print("[PreDownloadPlayer-DEBUG] self.close() OK")
        except Exception as e:
            print(f"[PreDownloadPlayer-DEBUG] close() error: {e}")
    # ==================== UTILS ====================
    def _safe_filename(self, title):
        """Konvertuje naslov u siguran naziv fajla."""
        safe = "".join([c for c in title if c.isalnum() or c in (' ', '-', '_', '.', "'")]).strip()
        if len(safe) > 100:
            safe = safe[:100]
        return safe

    # ==================== CANCEL ====================
    def cancel_download(self):
        """Prekida download i briše delimičan fajl."""
        print("[PreDownloadPlayer] Cancelling download...")
        self.is_cancelled = True

        if self.download_process:
            try:
                self.download_process.kill()
            except:
                pass

        try:
            if self.output_file and os.path.exists(self.output_file):
                os.remove(self.output_file)
            for f in os.listdir(self.download_path):
                if '.part' in f or '.ytdl' in f:
                    try:
                        os.remove(os.path.join(self.download_path, f))
                    except:
                        pass
        except Exception as e:
            print(f"[PreDownloadPlayer] Cleanup error: {e}")

        self.close()
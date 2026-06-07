# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Screens.ChoiceBox import ChoiceBox
from enigma import eServiceReference, eTimer
import subprocess
import datetime
import os
import time
import threading
import json

SETTINGS_FILE = "/usr/lib/enigma2/python/Plugins/Extensions/CiefpYouTube/settings.json"
BROKEN_LINKS_LOG = "/tmp/ciefp_youtube_broken_links.log"

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
    if quality == "2160":
        return 'best[height<=2160][ext=mp4]/best'
    elif quality == "1080":
        return 'best[height<=1080][ext=mp4]/best'
    elif quality == "720":
        return 'best[height<=720][ext=mp4]/best'
    else:
        return 'best[ext=mp4]/best'

def get_player_type():
    """Vraća tip playera iz settings (4097, 5001, 5002 ili movieplayer)"""
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
            f.write(f"[{timestamp}] TITLE: {title}\n")
            f.write(f"  URL: {url}\n")
            f.write(f"  ERROR: {error_msg}\n")
            f.write("-" * 80 + "\n")
    except:
        pass


class CiefpShortsPlayer(Screen):
    skin = """
        <screen position="0,0" size="1920,1080" title="CiefpYouTube Player" backgroundColor="#660033" flags="wfNoBorder">
            <eLabel position="0,0" size="1920,100" backgroundColor="#1a1a1a" zPosition="-1" />
            <eLabel text="..:: CiefpYouTube Browser ::.." position="60,25" size="600,50" font="Regular;40" foregroundColor="#ffffff" backgroundColor="#1a1a1a" transparent="1" />
            <widget name="menu" position="60,150" size="1800,800" scrollbarMode="showOnDemand" itemHeight="50" font="Regular;28" foregroundColor="#ffffff" backgroundColor="#2a2a2a" transparent="0" />
            <widget name="status" position="60,970" size="1800,40" font="Regular;24" foregroundColor="#ffcc00" backgroundColor="#660033" transparent="1" />
            <widget name="controls" position="60,1020" size="1800,40" font="Regular;20" foregroundColor="#03fc1c" backgroundColor="#660033" transparent="1" />
        </screen>
    """

    # U CiefpShortsPlayer klasi, izmijeni __init__ metod:
    def __init__(self, session, playlist, webcam_mode=False, bouquet_version=""):
        Screen.__init__(self, session)
        self.session = session
        self.playlist = playlist
        self.index = 0
        self.webcam_mode = webcam_mode
        self.bouquet_version = bouquet_version

        # Provjeri da li neki video u playlisti ima bouquet_version
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

        # ZA WEBCAM: Prikaži ChoiceBox sa opcijama single/playlist
        if self.webcam_mode:
            choices = [
                ("Play this video only", "single"),
                ("Play entire playlist in sequence (Mini Skin)", "playlist")
            ]
            self.session.openWithCallback(self.webcam_choice_callback, ChoiceBox,
                                          title="Select playback mode:", list=choices)
            return

        # ZA OBIČNE PLAYLISTE: Originalni kod
        choices = [
            ("Play this video only", "single"),
            ("Play entire playlist in sequence (Mini Skin)", "playlist")
        ]
        self.session.openWithCallback(self.choiceCallback, ChoiceBox,
                                      title="Select playback mode:", list=choices)

    def webcam_choice_callback(self, answer):
        """Callback za webcam izbor (isti kao choiceCallback ali sa webcam_mode)"""
        if answer:
            mode = answer[1]
            if mode == "single":
                current_video = self.playlist[self.index]
                url = current_video.get('url')
                title = current_video.get('title', 'Video')
                self["status"].setText("Loading stream...")
                threading.Thread(target=self.extractAndPlaySingle, args=(url, title), daemon=True).start()
            elif mode == "playlist":
                # Za webcam playlistu, pošalji webcam_mode=True
                self.session.open(CiefpWebcamPlaylistPlayer, self.playlist, self.index, self.bouquet_version)

    def choiceCallback(self, answer):
        if answer:
            mode = answer[1]
            if mode == "single":
                current_video = self.playlist[self.index]
                url = current_video.get('url')
                title = current_video.get('title', 'Video')
                self["status"].setText("Loading stream...")
                threading.Thread(target=self.extractAndPlaySingle, args=(url, title), daemon=True).start()
            elif mode == "playlist":
                self.session.open(CiefpPlaylistPlayer, self.playlist, self.index)

    def extractAndPlaySingle(self, url, title):
        quality = load_quality_setting()
        video_format = get_video_format(quality)
        try:
            cmd = ['yt-dlp', '-g', '-f', video_format, '--no-warnings', url]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and result.stdout.strip():
                video_url = result.stdout.strip().split('\n')[0]
                from twisted.internet import reactor
                reactor.callFromThread(self.closeAndPlay, video_url, title)
            else:
                cmd_fallback = ['yt-dlp', '-g', '-f', 'best', '--no-warnings', url]
                result_fallback = subprocess.run(cmd_fallback, capture_output=True, text=True, timeout=30)
                if result_fallback.returncode == 0 and result_fallback.stdout.strip():
                    video_url = result_fallback.stdout.strip().split('\n')[0]
                    from twisted.internet import reactor
                    reactor.callFromThread(self.closeAndPlay, video_url, title)
                else:
                    from twisted.internet import reactor
                    reactor.callFromThread(self.showErrorMsg, "Cannot extract stream URL")
        except Exception as e:
            # Loguj neispravan link za single play
            log_broken_link(url, title, str(e)[:30])
            from twisted.internet import reactor
            reactor.callFromThread(self.showErrorMsg, str(e)[:30])

    def closeAndPlay(self, video_url, title):
        """Zatvori trenutni prozor i pusti stream - single play"""
        try:
            player_type = get_player_type()
            print(f"[CiefpYouTube] Single play - player_type: '{player_type}'")

            if player_type == "movieplayer":
                # Ne zatvaraj odmah, prvo otvori MoviePlayer pa onda zatvori
                from Screens.InfoBar import MoviePlayer
                ref = eServiceReference(4097, 0, video_url)
                ref.setName(title)
                # Otvori MoviePlayer sa callback-om da zatvori CiefpShortsPlayer
                self.session.openWithCallback(self.close, MoviePlayer, ref)
            elif player_type == "5001":  # Exteplayer3
                self.close()
                time.sleep(0.3)
                ref = eServiceReference(5001, 0, video_url)
                ref.setName(title)
                self.session.nav.playService(ref)
            else:  # 4097 ili 5002
                self.close()
                time.sleep(0.3)
                ref = eServiceReference(5002, 0, video_url)
                ref.setName(title)
                self.session.nav.playService(ref)
        except Exception as e:
            print(f"[CiefpYouTube] Error in closeAndPlay: {e}")

    def showErrorMsg(self, error_msg):
        self["status"].setText(f"Error: {error_msg}")
        timer = eTimer()
        timer.callback.append(self.close)
        timer.start(2000, True)


class CiefpPlaylistPlayer(Screen):
    def __init__(self, session, playlist, start_index=0):
        alpha_hex = get_mini_skin_opacity()
        self.skin = f"""
        <screen position="0,0" size="1920,160" title="CiefpYouTube Playlist" backgroundColor="#ff000000" flags="wfNoBorder">
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
        threading.Thread(target=self.extractThread, args=(url, title), daemon=True).start()

    def extractThread(self, url, title):
        quality = load_quality_setting()
        video_format = get_video_format(quality)
        try:
            cmd = ['yt-dlp', '-g', '-f', video_format, '--no-warnings', url]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and result.stdout.strip():
                video_url = result.stdout.strip().split('\n')[0]
                from twisted.internet import reactor
                reactor.callFromThread(self.playVideoDirect, video_url, title)
            else:
                cmd_fallback = ['yt-dlp', '-g', '-f', 'best', '--no-warnings', url]
                result_fallback = subprocess.run(cmd_fallback, capture_output=True, text=True, timeout=30)
                if result_fallback.returncode == 0 and result_fallback.stdout.strip():
                    video_url = result_fallback.stdout.strip().split('\n')[0]
                    from twisted.internet import reactor
                    reactor.callFromThread(self.playVideoDirect, video_url, title)
                else:
                    from twisted.internet import reactor
                    reactor.callFromThread(self.showError, "Link error")
        except Exception as e:
            from twisted.internet import reactor
            reactor.callFromThread(self.showError, str(e)[:30])

    def playVideoDirect(self, video_url, title):
        try:
            ref = eServiceReference(5002, 0, video_url)
            ref.setName(title)
            self.session.nav.playService(ref)
            self["status"].setText("")
            self.playlist_timer.start(1000, False)
        except Exception as e:
            print(f"[CiefpYouTube] Error: {e}")

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
        # Loguj neispravan link
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


class CiefpWebcamPlaylistPlayer(Screen):
    def __init__(self, session, playlist, start_index=0, bouquet_version=""):
        alpha_hex = get_mini_skin_opacity()
        self.skin = f"""
        <screen position="0,0" size="1920,160" title="CiefpYouTube WebCam" backgroundColor="#ff000000" flags="wfNoBorder">
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
        self.is_paused = False
        self.is_loading = False  # DODATO: flag za učitavanje

        self["title"] = Label("Loading...")
        self["next_title"] = Label("")
        self["status"] = Label("")
        self["playlist_info"] = Label("")
        self["controls"] = Label(f"🔴 WEBCAM | Auto-switch: {self.webcam_timeout}s | OK: Pause | ▲/▼: Skip | EXIT: Exit")
        self["time"] = Label("")
        version_text = bouquet_version[:100] if len(bouquet_version) > 100 else bouquet_version
        self["bouquet_version"] = Label(version_text)
        self["bouquet_version"] = Label(bouquet_version[:100] if len(bouquet_version) > 100 else bouquet_version)

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

        # Provjeri da li smo preko kraja liste
        if self.index >= len(self.playlist):
            # Kraj liste - završavamo
            self["status"].setText("End of playlist reached")
            self.handleExit()
            return

        # ... ostatak koda (isti)
        current_video = self.playlist[self.index]
        url = current_video.get('url')
        title = current_video.get('title', 'Camera')

        # DODATO: Prikaži "Loading..." dok se stream učitava
        self["title"].setText(f"⏳ Loading: {title}...")
        self["status"].setText("Loading stream...")
        self.is_loading = True

        # Pripremi NEXT naziv (bit će prikazan kada nova kamera počne)
        if self.index + 1 < len(self.playlist):
            next_title = self.playlist[self.index + 1].get('title', '')
            self.pending_next_title = next_title
        else:
            self.pending_next_title = self.playlist[0].get('title', '') if self.playlist else ""

        self["playlist_info"].setText(f"Camera: {self.index + 1} of {len(self.playlist)}")

        threading.Thread(target=self.extractThread, args=(url, title), daemon=True).start()

    def extractThread(self, url, title):
        quality = load_quality_setting()
        video_format = get_video_format(quality)
        try:
            cmd = ['yt-dlp', '-g', '-f', video_format, '--no-warnings', url]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and result.stdout.strip():
                video_url = result.stdout.strip().split('\n')[0]
                from twisted.internet import reactor
                reactor.callFromThread(self.playVideoDirect, video_url, title)
            else:
                cmd_fallback = ['yt-dlp', '-g', '-f', 'best', '--no-warnings', url]
                result_fallback = subprocess.run(cmd_fallback, capture_output=True, text=True, timeout=30)
                if result_fallback.returncode == 0 and result_fallback.stdout.strip():
                    video_url = result_fallback.stdout.strip().split('\n')[0]
                    from twisted.internet import reactor
                    reactor.callFromThread(self.playVideoDirect, video_url, title)
                else:
                    from twisted.internet import reactor
                    reactor.callFromThread(self.showError, "Cannot extract stream")
        except Exception as e:
            from twisted.internet import reactor
            reactor.callFromThread(self.showError, str(e)[:30])

    def playVideoDirect(self, video_url, title):
        try:
            ref = eServiceReference(5002, 0, video_url)
            ref.setName(title)
            self.session.nav.playService(ref)

            # DODATO: Tek sada promijeni nazive (stream je učitan)
            self["title"].setText(title)
            self["next_title"].setText(self.pending_next_title)
            self["status"].setText("")
            self.is_loading = False

            self.start_auto_switch_timer()
        except Exception as e:
            print(f"[CiefpYouTube] Error: {e}")
            self.is_loading = False

    def start_auto_switch_timer(self):
        if self.auto_switch_timer:
            self.auto_switch_timer.stop()

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

        # Provjeri da li smo na zadnjoj kameri
        if self.index >= len(self.playlist) - 1:
            # Ovo je zadnja kamera, završavamo reprodukciju
            self["status"].setText("End of playlist reached")
            self.handleExit()
            return

        # DODATO: Prije prebacivanja, pripremi se za novu kameru
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

        # DODATO: Prije prebacivanja, pripremi se za novu kameru
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
        # Loguj neispravan link
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


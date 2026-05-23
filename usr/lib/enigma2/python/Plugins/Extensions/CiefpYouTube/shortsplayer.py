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
import time


SETTINGS_FILE = "/usr/lib/enigma2/python/Plugins/Extensions/CiefpYouTube/settings.json"
BROKEN_LINKS_LOG = "/tmp/ciefp_youtube_broken_links.log"

# Dodaj na vrh shortsplayer.py, posle importa
def get_mini_skin_opacity():
    """Vrati alpha hex za mini skin transparentnost"""
    settings_file = "/usr/lib/enigma2/python/Plugins/Extensions/CiefpYouTube/settings.json"

    # Mapa opacity -> hex alpha
    opacity_map = {
        '100': 'FF',
        '90': 'E6',
        '80': 'CC',
        '70': 'B3',
        '60': '99',
        '50': '80',
        '40': '66',
        '30': '4D',
        '20': '33',
        '10': '1A',
        '0': '00',
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
    elif quality == "1440":
        return 'best[height<=1440][ext=mp4]/best'
    elif quality == "1080":
        return 'best[height<=1080][ext=mp4]/best'
    elif quality == "720":
        return 'best[height<=720][ext=mp4]/best'
    elif quality == "480":
        return 'best[height<=480][ext=mp4]/best'
    else:
        return 'best[ext=mp4]/best'

def log_broken_link(url, title, error_msg=""):
    """Loguje neaktivne linkove u fajl"""
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(BROKEN_LINKS_LOG, 'a') as f:
            f.write(f"[{timestamp}] TITLE: {title}\n")
            f.write(f"  URL: {url}\n")
            f.write(f"  ERROR: {error_msg}\n")
            f.write("-" * 80 + "\n")
        print(f"[CiefpYouTube] Logged broken link: {title}")
    except Exception as e:
        print(f"[CiefpYouTube] Failed to log broken link: {e}")

# =========================================================================
# 1. EKRAN: KLASIČAN PREGLED LISTE (Glavni ekran)
# =========================================================================

class CiefpShortsPlayer(Screen):
    skin = """
        <screen position="0,0" size="1920,1080" title="CiefpYouTube Player" backgroundColor="#660033" flags="wfNoBorder">
            <eLabel position="0,0" size="1920,100" backgroundColor="#1a1a1a" zPosition="-1" />
            <eLabel text="..:: CiefpYouTube Browser ::.." position="60,25" size="600,50" font="Regular;40" foregroundColor="#ffffff" backgroundColor="#1a1a1a" transparent="1" />
            <widget name="menu" position="60,150" size="1800,800" scrollbarMode="showOnDemand" itemHeight="50" font="Regular;28" foregroundColor="#ffffff" backgroundColor="#2a2a2a" transparent="0" />
            <widget name="status" position="60,970" size="1800,40" font="Regular;24" foregroundColor="#ffcc00" backgroundColor="#660033" transparent="1" />
            <widget name="controls" position="60,1020" size="1800,40" font="Regular;20" foregroundColor="#aaaaaa" backgroundColor="#660033" transparent="1" />
        </screen>
    """

    def __init__(self, session, playlist):
        Screen.__init__(self, session)
        self.session = session  # DODAJ OVO
        self.playlist = playlist
        self.index = 0

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
        self.menu_list = []
        for video in self.playlist:
            self.menu_list.append(video.get('title', 'Unknown Video'))
        self["menu"].setList(self.menu_list)

    def okClicked(self):
        self.index = self["menu"].getSelectedIndex()
        
        choices = [
            ("Play this video only", "single"),
            ("Play entire playlist in sequence (Mini Skin)", "playlist")
        ]
        self.session.openWithCallback(self.choiceCallback, ChoiceBox, title="Select playback mode:", list=choices)

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

        print(f"[CiefpYouTube] Extracting stream for: {title}")
        print(f"[CiefpYouTube] URL: {url}")

        try:
            cmd = ['yt-dlp', '-g', '-f', video_format, '--no-warnings', url]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0 and result.stdout.strip():
                video_url = result.stdout.strip().split('\n')[0]
                print(f"[CiefpYouTube] Extracted video URL: {video_url[:100]}...")
                from twisted.internet import reactor
                reactor.callFromThread(self.closeAndPlay, video_url, title)
            else:
                # Loguj neaktivni link
                error_msg = result.stderr[:200] if result.stderr else "No stream available"
                log_broken_link(url, title, error_msg)

                print(f"[CiefpYouTube] Primary extraction failed, trying fallback...")
                cmd_fallback = ['yt-dlp', '-g', '-f', 'best[vcodec!=none][acodec!=none]', '--no-warnings', url]
                result_fallback = subprocess.run(cmd_fallback, capture_output=True, text=True, timeout=30)
                if result_fallback.returncode == 0 and result_fallback.stdout.strip():
                    video_url = result_fallback.stdout.strip().split('\n')[0]
                    from twisted.internet import reactor
                    reactor.callFromThread(self.closeAndPlay, video_url, title)
                else:
                    # Loguj i fallback neuspeh
                    log_broken_link(url, title, f"Fallback also failed: {result_fallback.stderr[:200]}")
                    from twisted.internet import reactor
                    reactor.callFromThread(self.showErrorMsg, "Cannot extract stream URL")
        except Exception as e:
            log_broken_link(url, title, str(e))
            print(f"[CiefpYouTube] Exception: {e}")
            from twisted.internet import reactor
            reactor.callFromThread(self.showErrorMsg, str(e)[:30])

    def closeAndPlay(self, video_url, title):
        """Zatvori trenutni prozor i pusti stream"""
        try:
            # Zatvori CiefpShortsPlayer
            self.close()
            # Mala pauza da se prozor sigurno zatvori
            time.sleep(0.3)
            # Pusti stream
            ref = eServiceReference(5002, 0, video_url)
            ref.setName(title)
            self.session.nav.playService(ref)
        except Exception as e:
            print(f"[CiefpYouTube] Error in closeAndPlay: {e}")

    def showErrorMsg(self, error_msg):
        self["status"].setText(f"Error: {error_msg}")
        # Sačekaj 2 sekunde pa zatvori
        timer = eTimer()
        timer.callback.append(self.close)
        timer.start(2000, True)


# =========================================================================
# 2. EKRAN: MINI SKIN ZA PLEJLISTU (Prilagođeno prema stabilnoj logici iz CiefpVibes)
# =========================================================================
class CiefpPlaylistPlayer(Screen):
    def __init__(self, session, playlist, start_index=0):
        # Učitaj opacity pre nego što se skin inicijalizuje
        alpha_hex = get_mini_skin_opacity()

        # Kreiraj dinamički skin
        self.skin = f"""
        <screen position="0,0" size="1920,160" title="CiefpYouTube Playlist" backgroundColor="#ff000000" flags="wfNoBorder">

            <eLabel position="0,0" size="1920,160"
                backgroundColor="#{alpha_hex}00000e"
                zPosition="1" />

            <eLabel text="NOW PLAYING:"
                position="50,20"
                size="180,40"
                font="Regular;22"
                foregroundColor="#ffffff"
                backgroundColor="#00000000"
                transparent="1"
                zPosition="2" />

            <widget name="title"
                position="240,15"
                size="1630,50"
                font="Regular;30"
                foregroundColor="#ffffff"
                backgroundColor="#{alpha_hex}00000e"
                transparent="1"
                zPosition="2" />

            <eLabel text="NEXT:"
                position="50,75"
                size="180,40"
                font="Regular;20"
                foregroundColor="#ffffff"
                backgroundColor="#00000000"
                transparent="1"
                zPosition="2" />

            <widget name="next_title"
                position="240,72"
                size="1200,40"
                font="Regular;24"
                foregroundColor="#aaaaaa"
                backgroundColor="#{alpha_hex}00000e"
                transparent="1"
                zPosition="2" />
                
            <!-- PLAYLIST INFO -->
                <widget name="playlist_info"
                position="50,120"
                size="300,30"
                font="Regular;22"
                foregroundColor="#00ffcc"
                backgroundColor="transparent"
                transparent="1"
                zPosition="2" />

            <!-- STATUS -->
            <widget name="status"
                position="900,120"
                size="500,30"
                font="Regular;22"
                halign="right"
                foregroundColor="#ffcc00"
                backgroundColor="transparent"
                transparent="1"
                zPosition="2" />    

            <!-- CONTROLS -->
            <widget name="controls"
                position="240,120"
                size="700,30"
                font="Regular;22"
                foregroundColor="#03fc1c"
                backgroundColor="#{alpha_hex}00000e"
                transparent="1"
                zPosition="2" />

            <!-- COUNTDOWN -->
            <widget name="duration"
                position="1400,115"
                size="180,40"
                font="Regular;30"
                halign="right"
                foregroundColor="#00ffcc"
                backgroundColor="transparent"
                transparent="1"
                zPosition="2"/>

            <!-- CLOCK -->
            <widget name="time"
                position="1600,110"
                size="300,50"
                font="Regular;36"
                halign="right"
                foregroundColor="#ffffff"
                backgroundColor="transparent"
                transparent="1"
                zPosition="2"/>

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

        # Time update
        self.time_timer = eTimer()
        self.time_timer.callback.append(self.updateTime)
        self.time_timer.start(1000)

        # Playlist timer
        self.playlist_timer = eTimer()

        try:
            self.playlist_timer.callback.append(self.playlistTimerCallback)
        except:
            self.playlist_timer.timeout.connect(self.playlistTimerCallback)

        self.startExtraction()


    def updateTime(self):
        try:
            import time
            t = time.strftime("%H:%M:%S")
            self["time"].setText(t)
        except:
            pass


    def startExtraction(self):
        # Zaustavljamo tajmer dok se izvlači novi link
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
            next_title = self.playlist[self.index + 1].get('title', '')
            self["next_title"].setText(next_title)
        else:
            self["next_title"].setText("End playlist")

        self["playlist_info"].setText(
            f"Song: {self.index + 1} out of  {len(self.playlist)}"
        )

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
                # Loguj neaktivni link
                log_broken_link(url, title, result.stderr[:200] if result.stderr else "No stream")

                cmd_fallback = ['yt-dlp', '-g', '-f', 'best[vcodec!=none][acodec!=none]', '--no-warnings', url]
                result_fallback = subprocess.run(cmd_fallback, capture_output=True, text=True, timeout=30)
                if result_fallback.returncode == 0 and result_fallback.stdout.strip():
                    video_url = result_fallback.stdout.strip().split('\n')[0]
                    from twisted.internet import reactor
                    reactor.callFromThread(self.playVideoDirect, video_url, title)
                else:
                    log_broken_link(url, title, f"Fallback failed: {result_fallback.stderr[:200]}")
                    from twisted.internet import reactor
                    reactor.callFromThread(self.showError, "Link error")
        except Exception as e:
            log_broken_link(url, title, str(e))
            from twisted.internet import reactor
            reactor.callFromThread(self.showError, str(e)[:30])

    def playVideoDirect(self, video_url, title):
        try:
            ref = eServiceReference(5002, 0, video_url)
            ref.setName(title)

            self.session.nav.playService(ref)

            # Stream krenuo -> skloni loading poruku
            self["status"].setText("")

            # Pokreni playlist timer
            self.playlist_timer.start(1000, False)

        except Exception as e:
            print(f"[CiefpYouTube] Startup error: {e}")

    def playlistTimerCallback(self):
        self.play_count += 1
        # Pustimo prvih 8 krugova (oko 12 sekundi) da se strim i bafer potpuno smire
        if self.play_count < 2:
            return

        try:
            service = self.session.nav.getCurrentService()
            if not service:
                print("[CiefpYouTube] No active service, I'm transferring...")
                self.nextVideo()
                return

            # Izvlacenje informacija o trajanju
            seek = service.seek()
            if seek:
                length = seek.getLength()
                position = seek.getPlayPosition()
                if not length or not position:
                    return

                if length[0] or position[0]:
                    return

                if length and position:
                    # Izračunavanje preostalog vremena (OpenATV / CiefpVibes sistem)
                    length_secs = int(length[1] / 90000)
                    position_secs = int(position[1] / 90000)

                    # Zaštita od pogrešnih stream vrednosti
                    if length_secs <= 0 or length_secs > 43200:
                        self["duration"].setText("--:--")
                        return

                    if position_secs < 0:
                        return
                    remaining = length_secs - position_secs
                    if remaining < 0 or remaining > 43200:
                        self["duration"].setText("--:--")
                        return
                    mins = int(remaining // 60)
                    secs = int(remaining % 60)

                    self["duration"].setText("-%02d:%02d" % (mins, secs))

                    # Ako je ostalo manje od 3 sekunde do kraja pesme
                    if remaining <= 3:
                        print("[CiefpYouTube] End of song detected via length. Next...")
                        self.nextVideo()
                        return
                else:
                    # Ako strim svira a ne vraća dužinu, ali getCurrentService javi da je stao/završio
                    # Ovo rešava problem ako length/position vrate None na mrežnim strimovima
                    if self.play_count > 15:  # samo ako je pesma vec realno svirala neko vreme
                        self.nextVideo()
                        return
        except Exception as e:
            print(f"[CiefpYouTube] Timer error:{e}")
            self.nextVideo()

    def nextVideo(self):
        self.playlist_timer.stop()

        # Poruka korisniku
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
        self["title"].setText(f"Error: {error_msg}. Skipping...")
        self.nextVideo()

    def handleExit(self):
        self.playlist_timer.stop()
        self.session.nav.stopService()
        self.close()
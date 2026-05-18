# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Screens.ChoiceBox import ChoiceBox
from enigma import eServiceReference, eTimer
import subprocess
import os
import threading
import json

SETTINGS_FILE = "/usr/lib/enigma2/python/Plugins/Extensions/CiefpYouTube/settings.json"

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
        return 'best[height<=2160][vcodec!=none][acodec!=none]/best'
    elif quality == "1080":
        return 'best[height<=1080][vcodec!=none][acodec!=none]/best'
    elif quality == "720":
        return 'best[height<=720][vcodec!=none][acodec!=none]/best'
    else:
        return 'best[vcodec!=none][acodec!=none]/best'


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
                # Puštamo samo jedan video preko posebnog thread-a i zatvaramo listu
                current_video = self.playlist[self.index]
                url = current_video.get('url')
                title = current_video.get('title', 'Video')
                self["status"].setText("Loading stream...")
                threading.Thread(target=self.extractAndPlaySingle, args=(url, title), daemon=True).start()
            elif mode == "playlist":
                # Otvaramo POTPUNO NOVI EKRAN (Mini Skin) i prosleđujemo mu listu i trenutni indeks
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
                reactor.callFromThread(self.playSingleDirect, video_url, title)
            else:
                cmd_fallback = ['yt-dlp', '-g', '-f', 'best[vcodec!=none][acodec!=none]', '--no-warnings', url]
                result_fallback = subprocess.run(cmd_fallback, capture_output=True, text=True, timeout=30)
                if result_fallback.returncode == 0 and result_fallback.stdout.strip():
                    video_url = result_fallback.stdout.strip().split('\n')[0]
                    from twisted.internet import reactor
                    reactor.callFromThread(self.playSingleDirect, video_url, title)
        except:
            pass

    def playSingleDirect(self, video_url, title):
        try:
            ref = eServiceReference(5002, 0, video_url)
            ref.setName(title)
            self.session.nav.playService(ref)
            self.close()
        except:
            pass


# =========================================================================
# 2. EKRAN: MINI SKIN ZA PLEJLISTU (Prilagođeno prema stabilnoj logici iz CiefpVibes)
# =========================================================================
class CiefpPlaylistPlayer(Screen):
    skin = """
        <screen position="0,0" size="1920,160" title="CiefpYouTube Playlist" backgroundColor="#ff000000" flags="wfNoBorder">
            <eLabel position="0,0" size="1920,160" backgroundColor="#dd111111" zPosition="1" />
            <eLabel text="NOW PLAYING:" position="50,20" size="180,40" font="Regular;22" foregroundColor="#ffffff" backgroundColor="#00000000" transparent="1" zPosition="2" />
            <widget name="title" position="240,15" size="1630,50" font="Regular;30" foregroundColor="#ffffff" backgroundColor="#00000000" transparent="1" zPosition="2" />
            <eLabel text="NEXT:" position="50,75" size="180,40" font="Regular;20" foregroundColor="#ffffff" backgroundColor="#00000000" transparent="1" zPosition="2" />
            <widget name="next_title" position="240,72" size="1630,40" font="Regular;24" foregroundColor="#aaaaaa" backgroundColor="#00000000" transparent="1" zPosition="2" />
            <widget name="status" position="240,120" size="500,30" font="Regular;20" foregroundColor="#ffcc00" backgroundColor="#00000000" transparent="1" zPosition="2" />
            <widget name="controls" position="750,120" size="1120,30" font="Regular;20" foregroundColor="#03fc1c" backgroundColor="#00000000" transparent="1" zPosition="2" />
        </screen>
    """

    def __init__(self, session, playlist, start_index=0):
        Screen.__init__(self, session)
        self.playlist = playlist
        self.index = start_index
        self.play_count = 0  # Brojač krugova tajmera za zaštitu početka strima

        self["title"] = Label("Loading...")
        self["next_title"] = Label("")
        self["status"] = Label("")
        self["controls"] = Label("OK: Pause | ▲/▼: Previous/Next | EXIT: Exit playlist")

        self["actions"] = ActionMap(["SetupActions", "DirectionActions"], {
            "cancel": self.handleExit,
            "ok": self.pauseToggle,
            "down": self.nextVideo,
            "up": self.prevVideo
        }, -1)

        # Inicijalizacija tajmera identično kao u CiefpVibes
        self.playlist_timer = eTimer()
        try:
            self.playlist_timer.callback.append(self.playlistTimerCallback)
        except:
            self.playlist_timer.timeout.connect(self.playlistTimerCallback)

        self.startExtraction()

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

        self["status"].setText(f"Song: {self.index + 1} od {len(self.playlist)}")

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
                cmd_fallback = ['yt-dlp', '-g', '-f', 'best[vcodec!=none][acodec!=none]', '--no-warnings', url]
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

            # Pokrećemo tajmer da proverava na svakih 1.5 sekundi (1500ms) kao u CiefpVibes
            self.playlist_timer.start(1500, False)
        except Exception as e:
            print(f"[CiefpYouTube] Startup error: {e}")

    def playlistTimerCallback(self):
        self.play_count += 1
        # Pustimo prvih 8 krugova (oko 12 sekundi) da se strim i bafer potpuno smire
        if self.play_count < 8:
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

                if length and position:
                    # Izračunavanje preostalog vremena (OpenATV / CiefpVibes sistem)
                    length_secs = length[1] / 90000
                    position_secs = position[1] / 90000
                    remaining = length_secs - position_secs

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
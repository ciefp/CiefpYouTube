#!/bin/bash
##setup command=wget -q "--no-check-certificate" https://raw.githubusercontent.com/ciefp/CiefpYouTube/main/installer.sh -O - | /bin/sh

######### Only This 2 lines to edit with new version ######
version='1.2'
changelog='\nAdded ffmpeg and yt-dlp installation for FHD/4K support on all images'
##############################################################

# Check if we should skip restart (for batch installations)
SKIP_REBOOT="${SKIP_REBOOT:-0}"

TMPPATH=/tmp/CiefpYouTube

if [ ! -d /usr/lib64 ]; then
	PLUGINPATH=/usr/lib/enigma2/python/Plugins/Extensions/CiefpYouTube
else
	PLUGINPATH=/usr/lib64/enigma2/python/Plugins/Extensions/CiefpYouTube
fi

# Check package manager status
if [ -f /var/lib/dpkg/status ]; then
	STATUS=/var/lib/dpkg/status
	OSTYPE=DreamOs
else
	STATUS=/var/lib/opkg/status
	OSTYPE=Dream
fi

echo ""
echo "============================================================="
echo "     CiefpYouTube v$version Installer"
echo "============================================================="
echo ""

# ============ DETEKCIJA OPENATV VERZIJE ============
get_openatv_version() {
	if [ -f /etc/image-version ]; then
		grep -i "version=" /etc/image-version 2>/dev/null | cut -d'=' -f2 | cut -d'.' -f1,2
	else
		echo ""
	fi
}

is_openatv8() {
	local ver=$(get_openatv_version)
	[[ "$ver" =~ ^8\. ]]
}

is_openatv7() {
	local ver=$(get_openatv_version)
	[[ "$ver" =~ ^7\. ]]
}

# ============ INSTALACIJA ffmpeg (obavezno za 4K) ============
install_ffmpeg() {
	echo "[CiefpYouTube] Installing ffmpeg (required for 4K/FHD)..."
	
	if [ $OSTYPE = "DreamOs" ]; then
		apt-get update && apt-get install ffmpeg -y
	else
		opkg update && opkg install ffmpeg
	fi
	
	# Provjeri da li je ffmpeg uspješno instaliran
	if command -v ffmpeg >/dev/null 2>&1; then
		echo "[CiefpYouTube] ffmpeg installed successfully: $(ffmpeg -version | head -1)"
	else
		echo "[CiefpYouTube] WARNING: ffmpeg installation failed - 4K may not work!"
	fi
}

# ============ INSTALACIJA yt-dlp ============
install_ytdlp() {
	echo "[CiefpYouTube] Installing yt-dlp..."
	
	# Prvo pokušaj instalirati python3-yt-dlp (OpenATV 7.6+)
	if [ $OSTYPE = "DreamOs" ]; then
		apt-get update
		apt-get install python3-yt-dlp -y || {
			echo "[CiefpYouTube] python3-yt-dlp not in repo, installing via pip3..."
			apt-get install python3-pip python3-codecs python3-core -y
			pip3 install yt-dlp --upgrade
		}
	else
		# OpenATV 7.6+ ima python3-yt-dlp u feedu
		opkg update
		opkg install python3-yt-dlp || {
			echo "[CiefpYouTube] python3-yt-dlp not in feed, trying pip3..."
			opkg install python3-pip python3-codecs python3-core
			pip3 install yt-dlp --upgrade
		}
	fi
	
	# Provjeri da li je yt-dlp uspješno instaliran
	if command -v yt-dlp >/dev/null 2>&1; then
		echo "[CiefpYouTube] yt-dlp installed successfully: $(yt-dlp --version)"
	else
		echo "[CiefpYouTube] WARNING: yt-dlp installation failed!"
	fi
}

# ============ INSTALACIJA Node.js (JavaScript runtime za yt-dlp) ============
install_nodejs() {
	echo "[CiefpYouTube] Checking for Node.js (required for YouTube JS challenges)..."
	
	if command -v node >/dev/null 2>&1; then
		echo "[CiefpYouTube] Node.js already installed: $(node --version)"
		return 0
	fi
	
	echo "[CiefpYouTube] Installing Node.js..."
	if [ $OSTYPE = "DreamOs" ]; then
		apt-get update && apt-get install nodejs -y
	else
		opkg update && opkg install nodejs
	fi
	
	if command -v node >/dev/null 2>&1; then
		echo "[CiefpYouTube] Node.js installed: $(node --version)"
		
		# Konfiguriši yt-dlp da koristi Node.js
		mkdir -p /home/root/.config/yt-dlp
		echo "--js-runtimes node" > /home/root/.config/yt-dlp/config
		echo "[CiefpYouTube] yt-dlp configured to use Node.js"
	else
		echo "[CiefpYouTube] WARNING: Node.js installation failed - 4K may not work!"
	fi
}

# ============ INSTALACIJA python3-requests ============
if grep -qs "Package: python3-requests" $STATUS ; then
	echo "[CiefpYouTube] python3-requests is already installed."
else
	echo "[CiefpYouTube] python3-requests is missing! Installing..."
	if [ $OSTYPE = "DreamOs" ]; then
		apt-get update && apt-get install python3-requests -y
	else
		opkg update && opkg install python3-requests
	fi
fi

# ============ INSTALACIJA python3-json ============
if [ $OSTYPE != "DreamOs" ]; then
	if ! opkg list-installed | grep -q "python3-json"; then
		echo "[CiefpYouTube] Installing python3-json..."
		opkg update && opkg install python3-json > /dev/null 2>&1
	fi
fi

echo ""

# ============ INSTALACIJA KOMANDI ZA FHD/4K ============
echo "============================================================="
echo "     Installing FHD/4K required components..."
echo "============================================================="

# 1. Instaliraj ffmpeg
install_ffmpeg

# 2. Instaliraj yt-dlp
install_ytdlp

# 3. Instaliraj Node.js za JavaScript support
install_nodejs

echo ""

# ============ INSTALACIJA PLUGINA ============
## Remove old tmp directory if exists
[ -d $TMPPATH ] && rm -rf $TMPPATH > /dev/null 2>&1

## Remove old plugin directory before upgrade
[ -d $PLUGINPATH ] && rm -rf $PLUGINPATH

# Download and install plugin
mkdir -p $TMPPATH
cd $TMPPATH
set -e

echo "[CiefpYouTube] Downloading latest package from GitHub..."
wget --no-check-certificate https://github.com/ciefp/CiefpYouTube/archive/refs/heads/main.tar.gz
tar -xzf main.tar.gz
cp -r 'CiefpYouTube-main/usr' '/'

set +e
cd
sleep 2

### Check if plugin installed correctly
if [ ! -d $PLUGINPATH ]; then
	echo "!!! SOMETHING WENT WRONG - CiefpYouTube not installed !!!"
	exit 1
fi

# Clean up installation trash
rm -rf $TMPPATH > /dev/null 2>&1
sync

echo ""
echo "#########################################################"
echo "#           CiefpYouTube v$version INSTALLED            #"
echo "#                                                       #"
echo "#  Features:                                           #"
echo "#  - FHD/4K Video Playback (requires yt-dlp + ffmpeg)  #"
echo "#  - Playlists with Mini Skin                          #"
echo "#  - User/Live Channels                                #"
echo "#  - Broken Links Log                                  #"
echo "#                                                       #"
echo "#                  developed by ciefp                   #"
echo "#                  .::CiefpSettings::.                  #"
echo "#               https://github.com/ciefp                #"
echo "#########################################################"

# Only restart if SKIP_REBOOT is not set to 1
if [ "$SKIP_REBOOT" = "0" ]; then
	echo "#            your Device will RESTART Now               #"
	echo "#########################################################"
	sleep 3
	killall -9 enigma2
else
	echo "#        Restart skipped (batch installation)           #"
	echo "#########################################################"
fi

exit 0
#!/bin/bash
##setup command=wget -q "--no-check-certificate" https://raw.githubusercontent.com/ciefp/CiefpYouTube/main/installer.sh -O - | /bin/sh

######### Only This 2 lines to edit with new version ######
version='1.0'
changelog='\nInitial public release\nAdded YouTube Jukebox with Smart Cache and OpenPLi Fix'
##############################################################

# Check if we should skip restart (for batch installations)
SKIP_REBOOT="${SKIP_REBOOT:-0}"

TMPPATH=/tmp/CiefpYouTube

if [ ! -d /usr/lib64 ]; then
	PLUGINPATH=/usr/lib/enigma2/python/Plugins/Extensions/CiefpYouTube
else
	PLUGINPATH=/usr/lib64/enigma2/python/Plugins/Extensions/CiefpYouTube
fi

# Check package manager status (FIXED duplicate line)
if [ -f /var/lib/dpkg/status ]; then
	STATUS=/var/lib/dpkg/status
	OSTYPE=DreamOs
else
	STATUS=/var/lib/opkg/status
	OSTYPE=Dream
fi

echo ""
echo "Checking dependencies for CiefpYouTube..."
echo ""

# 1. Provera i instalacija za yt-dlp (Sa naprednim fallback-om za OpenPLi preko pip3)
if python3 -c "import yt_dlp" > /dev/null 2>&1; then
	echo "[CiefpYouTube] Python module 'yt-dlp' is already working."
else
	echo "[CiefpYouTube] yt-dlp module is missing! Trying opkg/apt first..."
	if [ $OSTYPE = "DreamOs" ]; then
		apt-get update && apt-get install yt-dlp -y
	else
		opkg update && opkg install yt-dlp
	fi
	
	# OpenPLi FIX: Ako opkg nije uspeo da postavi ispravan modul, instaliramo ga preko pip3
	if ! python3 -c "import yt_dlp" > /dev/null 2>&1; then
		echo "[CiefpYouTube] opkg install failed to provision the module. Applying OpenPLi pip3 fix..."
		if [ $OSTYPE != "DreamOs" ]; then
			opkg update && opkg install python3-pip python3-codecs python3-core
			pip3 install yt-dlp
		fi
	fi
fi

# 2. Provera i instalacija za python3-requests
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

# 3. Provera i instalacija za python3-json (potrebno za čuvanje plejlista)
if grep -qs "Package: python3-json" $STATUS ; then
	echo "[CiefpYouTube] python3-json is already installed."
else
	if [ $OSTYPE != "DreamOs" ]; then
		if opkg list-installed | grep -q "python3-json"; then
			echo "[CiefpYouTube] python3-json is present."
		else
			opkg update && opkg install python3-json > /dev/null 2>&1
		fi
	fi
fi

echo ""

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
echo "#           CiefpYouTube INSTALLED SUCCESSFULLY         #"
echo "#                  Version: $version                    #"
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
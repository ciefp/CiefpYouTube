#!/bin/bash
##setup command=wget -q "--no-check-certificate" https://raw.githubusercontent.com/ciefp/CiefpYouTube/main/installer.sh -O - | /bin/sh

######### Only This 2 lines to edit with new version ######
version='1.1'
changelog='\nFixed universal yt-dlp installation for OpenATV 7.6/8.0+, OpenPLi and others'
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
echo "Checking dependencies for CiefpYouTube..."
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

# ============ INSTALACIJA yt-dlp ============
install_ytdlp() {
	echo "[CiefpYouTube] Installing yt-dlp..."
	
	# OpenPLi specijalni slučaj
	if grep -qi "openpli" /etc/issue 2>/dev/null; then
		echo "[CiefpYouTube] OpenPLi detected - installing via pip3"
		if [ $OSTYPE = "DreamOs" ]; then
			apt-get update
			apt-get install python3-pip python3-codecs python3-core -y
		else
			opkg update
			opkg install python3-pip python3-codecs python3-core
		fi
		pip3 install yt-dlp
		return $?
	fi
	
	# OpenATV 8.0+ koristi wrapper
	if is_openatv8; then
		echo "[CiefpYouTube] OpenATV 8.0+ detected - installing ytdlpwrapper"
		if [ $OSTYPE = "DreamOs" ]; then
			apt-get update && apt-get install enigma2-plugin-extensions-ytdlpwrapper -y
		else
			opkg update && opkg install enigma2-plugin-extensions-ytdlpwrapper
		fi
		return $?
	fi
	
	# OpenATV 7.6 i stariji - standardna instalacija
	if is_openatv7; then
		echo "[CiefpYouTube] OpenATV 7.x detected - standard yt-dlp install"
		if [ $OSTYPE = "DreamOs" ]; then
			apt-get update && apt-get install yt-dlp -y
		else
			opkg update && opkg install yt-dlp
		fi
		return $?
	fi
	
	# Fallback za sve ostale (Pure2, OpenSPA, itd.)
	echo "[CiefpYouTube] Generic system - trying opkg install"
	if [ $OSTYPE = "DreamOs" ]; then
		apt-get update && apt-get install yt-dlp -y || {
			echo "[CiefpYouTube] apt-get failed, trying pip3"
			apt-get install python3-pip python3-codecs python3-core -y
			pip3 install yt-dlp
		}
	else
		opkg update && opkg install yt-dlp || {
			echo "[CiefpYouTube] opkg failed, trying pip3"
			opkg install python3-pip python3-codecs python3-core
			pip3 install yt-dlp
		}
	fi
}

# Provera da li je yt-dlp već instaliran i radi
if python3 -c "import yt_dlp" > /dev/null 2>&1; then
	echo "[CiefpYouTube] yt-dlp is already working."
else
	install_ytdlp
	
	# Finalna provera
	if ! python3 -c "import yt_dlp" > /dev/null 2>&1; then
		echo "[CiefpYouTube] WARNING: yt-dlp module still not available!"
		echo "[CiefpYouTube] Continuing anyway, plugin may have limited functionality."
	fi
fi

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
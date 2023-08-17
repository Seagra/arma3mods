import getopt
import os
import sys
import os.path
import re
import shutil
from bs4 import BeautifulSoup
import platform
from shutil import which


from datetime import datetime
from urllib import request

# Requirements to check if mods need an update
A3_CHANGELOG_URL = 'https://steamcommunity.com/sharedfiles/filedetails/changelog'
A3_UPDATE_PATTERN = re.compile(r"workshopAnnouncement.*?<p id=\"(\d+)\">", re.DOTALL)

# If we are on Windows, we need our backslashes
if platform.system() == "Windows":
    A3_WORKSHOP_DIR = "{}\steamapps\workshop\content\{}"
else:
    A3_WORKSHOP_DIR = "{}/steamapps/workshop/content/{}"


# Now we set the requirements to use the correct workshop and the correct app_id
ARMA3_WORKSHOP_ID = '107410'
ARMA3_SERVER_ID = '233780'

# Global Dictonary for Mods
MODS = {}



# We define our Functions here to use them later
# Running SteamCMD with parameters
def runSteamCMD(STEAMCMD, parameters):
    print("")
    print("")
    os.system("{} {}".format(STEAMCMD, parameters))
    print("")
    print("")


# Start lowercase-mods
def lowerCaseMods(WORKSHOP_DIR):
    # Check if we are running on Windows, when we running on windows we don´t need this step
    if platform.system() == "Windows":
        print("[LOWERCASE] Welcome on Windows - This step is not required and will be skipped")
    else:
        if which("rename") is not None:
            print("[LOWERCASE] Starting Rename to lowercase all mods")
            os.system(
                "(cd {} && find . -depth -exec rename -v 's/(.*)\/([^\/]*)/$1\/\L$2/' {{}} \;)".format(WORKSHOP_DIR))
        else:
            print('[LOWERCASE] MISSING PROGRAM - RENAME!')
            exit(0)


# Create Sym-Links
# set links for arma3-server
def createSymLinks(ARMA_MOD_PATH, ARMAWORKSHOP):
    print("Starting Symlink-Creator")
    for modName, modID in MODS.items():
        if platform.system() == "Windows":
            linkPath = "{}\{}".format(ARMA_MOD_PATH, modName)
            realPath = "{}\{}".format(ARMAWORKSHOP, modID)
        else:
            linkPath = "{}/{}".format(ARMA_MOD_PATH, modName)
            realPath = "{}/{}".format(ARMAWORKSHOP, modID)

        if os.path.isdir(realPath):
            if not os.path.exists(linkPath):
                os.symlink(realPath, linkPath)
                print("Creating SymLink for Mod '{} '".format(linkPath))
            else:
                print("Symlink for Mod {} already exists!".format(modName))
                continue
        else:
            print("Mod '{}' not found!".format(modName))
            continue


# Check for Modification Update
def modUpdate(modID, modPath, armaModPath):
    if os.path.exists(armaModPath):
        response = request.urlopen("{}/{}".format(A3_CHANGELOG_URL, modID)).read()
        response = response.decode('utf-8')

        matchPattern = A3_UPDATE_PATTERN.search(response)

        if matchPattern:
            updatedAt = datetime.fromtimestamp(int(matchPattern.group(1)))
            createdAt = datetime.fromtimestamp(os.path.getctime(modPath))

            return (updatedAt >= createdAt)
        return False


# Update Mods|Install Mods
def updateMods(STEAMUSER, STEAMPASS, ARMAWORKSHOP, STEAMCMDPATH):
    steamCMDParam = " +force_install_dir {}".format(ARMAWORKSHOP)
    steamCMDParam += " +login {} {}".format(STEAMUSER, STEAMPASS)
    for modName, modID in MODS.items():
        path = "{}/{}".format(A3_WORKSHOP_DIR, modID)

        if os.path.exists(path):
            if modUpdate(modID, path):
                shutil.rmtree(path)
                print('Update for Mod {} found, start update...'.format(modName))
                steamCMDParam += " +workshop_download_item {} {} validate".format(ARMA3_WORKSHOP_ID, modID)
                continue
            else:
                print("No Update needed for Mod {}".format(modName))
                continue
        elif not(os.path.exists(path)):
            print("Mod not existing, install mod ""{}".format(modName))
            steamCMDParam += " +workshop_download_item {} {} validate".format(ARMA3_WORKSHOP_ID, modID)
            continue
        else:
            print("No Update for Mod '{}' required!".format(modName))
            continue

    if "+workshop_download_item" in steamCMDParam:
        print('Start Mod-Download')
        steamCMDParam += ' +quit'
        runSteamCMD(STEAMCMDPATH, steamCMDParam)
    else:
        print("No Download-Queue, skip Mod-Download")


def buildSystemDService(servername, headless_count, headless_password,commandLineParameters):
    if platform.system() != "Windows":
        print("[SYSTEMD-BUILDER] Build Server-File")



## MainProgramm
#
#
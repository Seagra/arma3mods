import getopt
import os
import sys
import os.path
import re
import shutil

from bs4 import BeautifulSoup
import configparser


from datetime import datetime
from urllib import request


###
#   CONFIGURATION
###
ARMA_SERVER_PATH = ''
ARMA_MOD_PATH = ARMA_SERVER_PATH + '/mods'
STEAM_USER = ''
STEAM_PASSWORD = ''
STEAMCMD = ''
MODSET_FILE = ''
CONFIG_FILE = ''
CMD_PARAMS = ''
SYSTEM_USER = ''
SYSTEMD_GROUP = ''
FORCE = False

ARMA3_WORKSHOP_ID = '107410'
ARMA3_SERVER_ID = '233780'

A3_UPDATE_PATTERN = re.compile(r"workshopAnnouncement.*?<p id=\"(\d+)\">", re.DOTALL)
A3_WORKSHOP_DIR = "{}/steamapps/workshop/content/{}".format(ARMA_SERVER_PATH, ARMA3_WORKSHOP_ID)
A3_CHANGELOG_URL = 'https://steamcommunity.com/sharedfiles/filedetails/changelog'

###
# FUNCTIONS
####

# Running Steam-CMD
def steamcmd(parameters):
    print("")
    print("")
    os.system("{} {}".format(STEAMCMD, parameters))
    print("")
    print("")


# Set mods to lowercase to prevent unix-problems, only used on unix-machines
def lowercase_mods():
    print("Start Lowercase-Mods")
    os.system("(cd {} && find . -depth -exec rename -v 's/(.*)\/([^\/]*)/$1\/\L$2/' {{}} \;)".format(A3_WORKSHOP_DIR))


# set links for arma3-server
def createSymLinks():
    print("Starting Symlink-Creator")
    for modName, modID in MODS.items():
        linkPath = "{}/{}".format(ARMA_MOD_PATH, modName)
        realPath = "{}/{}".format(A3_WORKSHOP_DIR, modID)

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
def modUpdate(modID, modPath):
    if os.path.exists(ARMA_MOD_PATH):
        response = request.urlopen("{}/{}".format(A3_CHANGELOG_URL, modID)).read()
        response = response.decode('utf-8')

        matchPattern = A3_UPDATE_PATTERN.search(response)

        if matchPattern:
            updatedAt = datetime.fromtimestamp(int(matchPattern.group(1)))
            createdAt = datetime.fromtimestamp(os.path.getctime(modPath))

            return (updatedAt >= createdAt)
        else:
            return False


# Update Mods
def updateMods():
    steamCMDParam = " +force_install_dir {}".format(ARMA_SERVER_PATH)
    steamCMDParam += " +login {} {}".format(STEAM_USER, STEAM_PASSWORD)
    for modName, modID in MODS.items():
        path = "{}/{}".format(A3_WORKSHOP_DIR, modID)

        if os.path.exists(path):
            if modUpdate(modID, path):
                shutil.rmtree(path)
                print('Update for Mod {} found, start update...'.format(modName))
                steamCMDParam += " +workshop_download_item {} {} validate".format(ARMA3_WORKSHOP_ID, modID)
            else:
                print("No Update needed for Mod {}".format(modName))
        elif not(os.path.exists(path)):
            print("Mod not existing, install mod ""{}".format(modName))
            steamCMDParam += " +workshop_download_item {} {} validate ".format(ARMA3_WORKSHOP_ID, modID)
        else:
            if FORCE:
                print("FORCE Update for Mod '{}' required!".format(modName))
                steamCMDParam += " +workshop_download_item {} {} validate ".format(ARMA3_WORKSHOP_ID, modID)
            else:
                print("No Update for Mod '{}' required!".format(modName))

    if "+workshop_download_item" in steamCMDParam:
        print('Start Mod-Download')
        steamCMDParam += ' +quit'
        steamcmd(steamCMDParam)
    else:
        print("No Download-Queue, skip Mod-Download")


# Build Service-File
def buildSystemd():
    print("Build Server-File")
    serverFileContent = '[Unit] \n Description= Arma3Server Service File \n \n'
    serverFileContent += '[Service] \n Type=simple \n Restart=on-failure \n User=' + SYSTEMD_USER + ' \n Group=' + SYSTEMD_GROUP + ' \n WorkingDirectory=' + ARMA_SERVER_PATH + '/  \n ExecStart=' + ARMA_SERVER_PATH + '/./arma3server_x64 '

    # Checkout our start_parameters
    if paramList[0] != "empty":
        for element in paramList:
            serverFileContent += str(element) + ' '

    modRelativePath = ARMA_MOD_PATH.split("/")
    for modName, modID in MODS.items():
        serverFileContent += ' "-mod=' + modRelativePath[-1] + '/' + modName + '"'

    serverFileContent += '\n'
    serverFileContent += '[Install] \n WantedBy=multi-user.target'

    with open('/etc/systemd/system/armaserver.service', 'w+') as file:
        file.write(serverFileContent)
    # Reload SystemCTL-Daemon
    os.system('systemctl daemon-reload')

        # Set correct permissions
    os.system('chown ' + SYSTEMD_USER + ':' + SYSTEMD_GROUP + ' ' + ARMA_SERVER_PATH + ' -R')
    os.system('chown ' + SYSTEMD_USER + ':' + SYSTEMD_GROUP + ' ' + ARMA_MOD_PATH + ' -R')


####
#
#
####


# We load our Config-File for Arma-Server from path and load the modset.html-file
CONFIG_FILE = sys.argv[1]
MODSET_FILE = sys.argv[2]

if len(sys.argv) == 4:
    FORCE = True

# load Config-Elements
if os.path.exists(CONFIG_FILE):
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)

    ARMA_SERVER_PATH = config['ARMA']['SERVER_PATH']
    ARMA_MOD_PATH = ARMA_SERVER_PATH + '/mods'
    STEAMCMD = config['STEAM']['STEAM_PATH']
    STEAM_USER = config['STEAM']['STEAM_USER']
    STEAM_PASSWORD = config['STEAM']['STEAM_PASSWORD']
    SYSTEMD_USER = config['ARMA']['SERVER_USER']
    SYSTEMD_GROUP = config['ARMA']['SERVER_GROUP']
    A3_WORKSHOP_DIR = "{}/steamapps/workshop/content/{}".format(ARMA_SERVER_PATH, ARMA3_WORKSHOP_ID)

    paramList = []
    if(len(config['ARMA']['START_PARAMETERS']) > 0):
        paramList = config['ARMA']['START_PARAMETERS'].split(",")
    else:
        paramList = ["empty"]
else:
    print("Config-File can not be loaded!")
    exit(1)

with open(MODSET_FILE, 'r') as htmlFile:
    fileContent = htmlFile.read()

# Check if file is empty, when not do our magic stuff ;D We extract the content from the table and extract the mod-id for download
if len(fileContent) > 0:
    soup = BeautifulSoup(fileContent, 'html.parser')
    MODS = {}
    for row in soup.table.find_all('tr'):
        row_cell = row.td.get_text()
        row_link = row.a.get_text()
        row_id = row_link.split("=")
        modID = row_id[1]
        MODS[row_cell] = modID

    # Check if result is empty
    if len(MODS) > 0:
        # If not exists, create Folder for Mods
        if not os.path.isdir(ARMA_MOD_PATH):
            os.mkdir(ARMA_MOD_PATH)

        updateMods()
        lowercase_mods()
        createSymLinks()
        buildSystemd()
        print("Installed!")
        exit(0)
    else:
        print("Nothing to do")
        exit(0)

else:
    print("Config not found!")
    exit(1)

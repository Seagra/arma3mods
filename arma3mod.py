import os
import platform
import sys
import os.path
import re
import shutil
from bs4 import BeautifulSoup


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

ARMA3_WORKSHOP_ID = '107410'
ARMA3_SERVER_ID = '233780'

A3_UPDATE_PATTERN = re.compile(r"workshopAnnouncement.*?<p id=\"(\d+)\">", re.DOTALL)
A3_WORKSHOP_DIR = "{}/steamapps/workshop/content/{}".format(ARMA_SERVER_PATH, ARMA3_WORKSHOP_ID)
A3_CHANGELOG_URL = 'https://steamcommunity.com/sharedfiles/filedetails/changelog'

SYSTEMD_BUILD = True
SYSTEMD_SERVER_SERVICE = 'armaserver'
SYSTEMD_HEADLESS_COUNT = 3
SYSTEMD_HEADLESS_SERVICE = 'armaclient'
SYSTEMD_USER = 'arma'
SYSTEMD_GROUP = 'arma'

HEADLESS_CONNECT_ADDRESS = '127.0.0.1'
HEADLESS_CONNECT_PORT = 2302
HEADLESS_SERVER_PASSWORD = 'x23y'


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
        steamcmd(steamCMDParam)
    else:
        print("No Download-Queue, skip Mod-Download")


# Build Service-File
def buildSystemd():
    if SYSTEMD_BUILD:
        print("Build Server-File")
        serverFileContent = '[Unit] \n Description= Arma3Server Service File \n Wants=network-online.target \n Before=arma.target \n PartOf=arma.target \n \n'
        serverFileContent += '[Service] \n Type=simple \n Restart=on-failure \n ExecStartPre=/bin/sleep 10 \n User=' + SYSTEMD_USER + ' \n Group=' + SYSTEMD_GROUP + ' \n WorkingDirectory=' + ARMA_SERVER_PATH + '/  \n ExecStart=' + ARMA_SERVER_PATH + '/./arma3server_x64 -exThreads=7 -config=server.cfg '
        modRelativePath = ARMA_MOD_PATH.split("/")
        for modName, modID in MODS.items():
            serverFileContent += ' "-mod=' + modRelativePath[-1] + '/' + modName + '"'

        serverFileContent += '\n'
        serverFileContent += '[Install] \n WantedBy=arma.target'

        with open('/etc/systemd/system/' + SYSTEMD_SERVER_SERVICE + '.service', 'w+') as file:
            file.write(serverFileContent)
        # Reload SystemCTL-Daemon
        os.system('systemctl daemon-reload')

        if SYSTEMD_HEADLESS_COUNT > 0:
            count = 0
            while count < SYSTEMD_HEADLESS_COUNT:
                print("Build Headless-File for Headless-Client Number " + str(count))
                serverFileContent = '[Unit] \n Description= Arma3Server Headless File \n Wants=network-online.target \n Before=arma.target PartOf=arma.target \n After=armaserver.service \n \n'
                serverFileContent += '[Service] \n Type=simple \n Restart=on-failure \n ExecStartPre=/bin/sleep/10 \n User=' + SYSTEMD_USER + ' \n Group=' + SYSTEMD_GROUP + ' \n WorkingDirectory=' + ARMA_SERVER_PATH + '/  \n ExecStart=' + ARMA_SERVER_PATH + '/./arma3server_x64 -client -connect=' + HEADLESS_CONNECT_ADDRESS + ' -port=' + str(HEADLESS_CONNECT_PORT) + ' -password=' + HEADLESS_SERVER_PASSWORD
                modRelativePath = ARMA_MOD_PATH.split("/")
                for modName, modID in MODS.items():
                    serverFileContent += ' "-mod=' + modRelativePath[-1] + '/' + modName + '"'

                serverFileContent += '\n'
                serverFileContent += '[Install] \n WantedBy=arma.target'

                with open('/etc/systemd/system/' + SYSTEMD_HEADLESS_SERVICE + str(count) + '.service', 'w+') as file:
                    file.write(serverFileContent)
                count = count + 1

        # Build Target-File
        armatarget = '[Unit] \n Decription=Arma3-Server \n \n [Install] \n WantedBy=multi-user.target \n'

        with open('/etc/systemd/system/arma.target', 'w+') as target:
            target.write(armatarget)

        # Reload SystemCTL-Daemon
        os.system('systemctl daemon-reload')
        # Set correct permissions
        os.system('chown ' + SYSTEMD_USER + ':' + SYSTEMD_GROUP + ' ' + ARMA_MOD_PATH + ' -R')

# First we need our HTML-File from Arma3Launcher

if len(sys.argv) == 2:
    # Check if file exists, when file exists now we want to read the content ;D
    if os.path.exists(sys.argv[1]):

        with open(sys.argv[1], 'r') as htmlFile:
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
                updateMods()
                lowercase_mods()
                createSymLinks()
                buildSystemd()
    else:
        print("File not found: " + str(sys.argv[1]))

# Integrated Ansible-Call for our ansible-playbook
elif len(sys.argv) == 6:
    if os.path.exists(sys.argv[1]):

        with open(sys.argv[1], 'r') as htmlFile:
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
                ARMA_SERVER_PATH = sys.argv[2]
                ARMA_MOD_PATH = ARMA_SERVER_PATH + '/mods'
                STEAM_USER = sys.argv[4]
                STEAM_PASSWORD = sys.argv[5]
                A3_WORKSHOP_DIR = "{}/steamapps/workshop/content/{}".format(ARMA_SERVER_PATH, ARMA3_WORKSHOP_ID)

                # Log in with anonymous-user
                if STEAM_USER == "anonymous":
                    STEAM_PASSWORD = ''

                STEAMCMD = sys.argv[3] + 'steamcmd.sh'

                updateMods()
                lowercase_mods()
                createSymLinks()
                buildSystemd()

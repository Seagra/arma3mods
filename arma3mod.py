import getopt
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
MODSET_FILE = '/home/modset.html'

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
                serverFileContent += '[Service] \n Type=simple \n Restart=on-failure \n ExecStartPre=/bin/sleep 20 \n User=' + SYSTEMD_USER + ' \n Group=' + SYSTEMD_GROUP + ' \n WorkingDirectory=' + ARMA_SERVER_PATH + '/  \n ExecStart=' + ARMA_SERVER_PATH + '/./arma3server_x64 -client -connect=' + HEADLESS_CONNECT_ADDRESS + ' -port=' + str(HEADLESS_CONNECT_PORT) + ' -password=' + HEADLESS_SERVER_PASSWORD
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


# Cleanup for Mods when they are not in html
def  cleanUp():
    if os.path.exists(A3_WORKSHOP_DIR) and os.path.exists(ARMA_MOD_PATH):
        workshop_dir = os.listdir(A3_WORKSHOP_DIR)
        mod_dir = os.listdir(ARMA_MOD_PATH)

        for modName, modID in MODS.items():
            if modName not in mod_dir:
                print("Mod not found in Mod-HTML, delete Mod " + str(modName))
                os.unlink(workshop_dir + modID)
                os.unlink(mod_dir + modName)
            elif modID not in workshop_dir:
                print("Mod not found in Workshop-Dir, delete Mod " + str(modName))
                os.unlink(workshop_dir + modID)
                os.unlink(mod_dir + modName)
            else:
                continue


##
#   MAIN-PRGOGRAMM
#
##
buildCMDFlag = False
cleanFlag = False

# Check if comamnd-line parameters given
if len(sys.argv) > 2:
    arguments = sys.argv[1:]

    try:
        opts, args = getopt.getopt(arguments, "a:s:m:h:b:x:u:p:c:d",
                                   ['armapath',
                                    'steampath',
                                    'modsetfile',
                                    'help',
                                    'buildsystemd',
                                    'headlessclients',
                                    'steamcmduser',
                                    'steamcmdpassword',
                                    'headlessclientpw',
                                    'deleteoldmods'])
    except:
        print("Error to execute Script!")
        exit()

    for opt, arg in opts:

        if opt in ['-a', '--armapath']:
            ARMA_SERVER_PATH = arg
            ARMA_MOD_PATH = arg + '/mods'
            A3_WORKSHOP_DIR = "{}/steamapps/workshop/content/{}".format(ARMA_SERVER_PATH, ARMA3_WORKSHOP_ID)

        elif opt in ['-s', '--steampath']:
            STEAMCMD = arg

        elif opt in ['-m', '--modsetfile']:
            MODSET_FILE = arg

        elif opt in ['-h', '--help']:
            print("Usage: python3 armamods.py -a <arma_server_path> -s <steamcmd_path> -m <modset_file> -b <y> (Build SYSTEMD_FILES) -x <int|Amount of headless clients> -u <steamcmd_user> -p <steamcmd_password> -d <y> (Auto-Cleanup when mods not in modlist.html")

        elif opt in ['-b', '--buildsystemd']:
            buildCMDFlag = True

        elif opt in ['-x', '--headlessclients']:
            SYSTEMD_HEADLESS_COUNT = str(arg)

        elif opt in ['-u', '--steamcmduser']:
            STEAM_USER = arg

        elif opt in ['-p', '--steamcmdpassword']:
            STEAM_PASSWORD = arg

        elif opt in ['-c', '--headlessclientpw']:
            SYSTEMD_HEADLESS_PASSWORD = arg

        elif opt in ['-d', '--deleteoldmods']:
            cleanFlag = True


        else:
            print("Option " + str(opt) + " not found!")
            continue


    # Pasing HTML-File and do our modStuff
    if os.path.exists(MODSET_FILE):

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

            if len(MODS) > 0:
                updateMods()
                lowercase_mods()
                createSymLinks()

                if buildCMDFlag:
                    buildSystemd()

                if cleanFlag:
                    cleanUp()
                exit(0)

            else:
                print("No Mods imported!")
                exit(1)

        else:
            print("ModSet-File " + str(MODSET_FILE) + ' is empty!')
            exit(1)

    else:
        print('ModSet-File ' + str(MODSET_FILE) + ' not exists!')
        exit(1)

else:
    print("Usage: python3 armamods.py -a <arma_server_path> -s <steamcmd_path> -m <modset_file> -b (build systemD-Files) -x <int|Amount of headless clients> -u <steamcmd_user> -p <steamcmd_password>")
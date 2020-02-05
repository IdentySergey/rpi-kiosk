import os
import threading
import platform
import subprocess
import time
import logging


class PlaylistFolderScanner(object):

    def __init__(self, base_path):
        self.playlist = []
        self.rsync_start = False
        self.local_path = "{0}/{1}".format(base_path, 'src')
        self.remote_path = "{0}/{1}".format(base_path, 'dst')
        self.mount = None
        self.sync = False

    def enable_rsync(self, smb_path, smb_username, smb_password):
        self.mount = MountFolder(self.remote_path, smb_path, smb_username, smb_password)
        threading.Thread(target=self.rsync, daemon=True).start()
        self.sync = True

    def make_playlist(self):
        local_path_folder = os.listdir(self.local_path)
        remote_path_folder = os.listdir(self.remote_path)
        self.playlist = []
        if self.sync:
            for local_item in local_path_folder:
                if local_item in remote_path_folder:
                    self.playlist.append("{0}/{1}".format(self.local_path, local_item))
        else:
            for local_item in local_path_folder:
                self.playlist.append("{0}/{1}".format(self.local_path, local_item))
        return self.playlist

    def rsync(self):
        while True:
            self.sync = self.mount.has_sync()
            if self.sync:
                subprocess.call(
                    ['rsync', '-az', '--delete', "{0}/".format(self.remote_path), "{0}/".format(self.local_path)])
                print("SYNC")
                time.sleep(3)


class MountFolder(object):

    def __init__(self, remote_path, smb_path, smb_username, smb_password):
        self.smb_path = smb_path
        self.smb_username = smb_username
        self.smb_password = smb_password
        self.host = smb_path.split('\\')[2]
        self.remote_path = remote_path
        self.has_trouble = True
        self.monitor = threading.Thread(target=self.monitor_thread, daemon=True)
        self.__loop_monitor = True
        self.monitor.start()

    def monitor_thread(self):
        while self.__loop_monitor:
            if not self.ping() or not self.mount_remote():
                logging.error("network error")
                self.has_trouble = True
            else:
                self.has_trouble = False
            time.sleep(1)

    def has_sync(self):
        return self.has_trouble

    def is_mounted(self):
        rp = subprocess.Popen("sudo mount | grep {0}".format(self.remote_path), stdout=subprocess.PIPE, shell=True)
        rs = rp.communicate()
        rp.wait()
        if rs[0].decode('utf-8') is '':
            return False
        return True

    def mount_remote(self):
        if self.ping() and not self.is_mounted():
            smb_path = self.smb_path.replace('\\', '/')
            smb_mount = "sudo mount -t cifs -o vers=2.1,username={0},password={1} {2} {3}" \
                .format(self.smb_username, self.smb_password, smb_path, self.remote_path).split(" ")
            if subprocess.call(smb_mount) is 0:
                return True
        return False

    def ping(self):
        param = '-n' if platform.system().lower() == 'windows' else '-c'
        command = ['ping', param, '1', self.host]
        return subprocess.call(command, stdout=open(os.devnull, 'wb')) == 0


class MediaKiosk(object):

    def __init__(self, base_path="/home/pi/kiosk", smb_path="", smb_username="", smb_password=""):
        logging.basicConfig(filename='kiosk.log', level=logging.INFO)
        self.is_alive = True
        self.local_path = "{0}/{1}".format(base_path, 'src')
        self.remote_path = "{0}/{1}".format(base_path, 'dst')
        if not os.path.isdir(base_path):
            os.mkdir(base_path)
        if not os.path.isdir(self.local_path):
            os.mkdir(self.local_path)
        if not os.path.isdir(self.remote_path):
            os.mkdir(self.remote_path)
        self.scanner = PlaylistFolderScanner(base_path)
        if smb_path is not "":
            self.scanner.enable_rsync(smb_path, smb_username, smb_password)

    def start(self):
        self.is_alive = True
        while self.is_alive:
            playlist = self.scanner.make_playlist()
            for item in playlist:
                spc = subprocess.Popen("omxplayer -p -o hdmi {0}".format(item), stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, close_fds=True, shell=True)
                spc.wait()
                spc.stdin.write(b'q')





# Inspired by https://pypi.python.org/pypi/jukebox-mpg123

from signal import SIGTSTP, SIGTERM, SIGABRT
import pty
import sys, os, subprocess
import threading
import time

# Subdirectory to look for music in.
musicDir = 'music'

# The higher it is, the faster volume changes for each 'volume +/-' command.
volumeChangeMultiplier = 5

def mod_inc(val, mod):
    return (val + 1) % mod

def mod_dec(val, mod):
    return (val + mod - 1) % mod

class MusicPlayer(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        # Extremely coarse-grained lock.
        self.lock = threading.Lock()
        self.song_idx = 0;
        self.songs = filter(lambda s: s.endswith('.mp3'), os.listdir(musicDir))
        self.songs.sort()
        self.proc = None
        self.mpg123 = None
        self.running = True
        self.stopped = False
        self.masterPty = None
        self.slavePty = None

    def getNextSong(self):
        nextSong = self.songs[self.song_idx];
        self.song_idx = mod_inc(self.song_idx, len(self.songs))
        return nextSong
    
    def stopPlayingSong(self):
        if self.proc is not None:
            self.proc.terminate()
            self.proc = None

    def run(self):
        # Check if mpg123 is available
        fin, fout = os.popen4(["which", "mpg123"])
        self.mpg123 = fout.read().replace("\n", "")
        if not len(self.mpg123):
            print "error mpg123 not installed"
            return

        self.main_loop()

    def quit(self):
        self.lock.acquire()
        self.running = False
        self.stopPlayingSong()
        self.lock.release()

    def main_loop(self):
        self.lock.acquire()
        while self.running:
            if not self.stopped:
                if self.proc is None:
                    song = os.path.join(musicDir, self.getNextSong())
                    DEVNULL = open(os.devnull, 'w')
                    self.masterPty, self.slavePty = pty.openpty()
                    self.proc = subprocess.Popen(
                        [self.mpg123, '-C', '-r', '48000', song],
                        shell = False,
                        stdout = DEVNULL,
                        stderr = DEVNULL,
                        stdin = self.slavePty
                    )
                else:
                    if self.proc.poll() is not None:
                        self.proc = None
            self.lock.release()
            time.sleep(0.5)
            self.lock.acquire()

    def nextSong(self):
        self.lock.acquire()
        self.stopPlayingSong()
        if self.stopped:
            self.song_idx = mod_inc(self.song_idx, len(self.songs))
        self.lock.release()

    def prevSong(self):
        self.lock.acquire()
        self.stopPlayingSong()
        self.song_idx = mod_dec(self.song_idx, len(self.songs))
        if not self.stopped:
            self.song_idx = mod_dec(self.song_idx, len(self.songs))
        self.lock.release()

    def gotoSong(self, song_idx):
        self.lock.acquire()
        ret = False
        if 0 <= song_idx and song_idx < len(self.songs):
            self.song_idx = song_idx
            self.stopPlayingSong()
            ret = True
        self.lock.release()
        return ret
    
    def stop(self):
        self.lock.acquire()
        self.stopPlayingSong()
        self.stopped = True
        self.song_idx = mod_dec(self.song_idx, len(self.songs))
        self.lock.release()

    def play(self):
        self.lock.acquire()
        self.stopped = False
        self.lock.release()

    def volume(self, change):
        assert change == '+' or change == '-'
        self.lock.acquire()
        if self.proc is not None:
            for _ in xrange(volumeChangeMultiplier):
                os.write(self.masterPty, change)
        self.lock.release()

musicPlayer = MusicPlayer()
musicPlayer.start()

while True:
    command = raw_input()
    if command == 'quit':
        musicPlayer.quit()
        break
    elif command == 'next':
        musicPlayer.nextSong()
    elif command == 'prev':
        musicPlayer.prevSong()
    elif command == 'stop':
        musicPlayer.stop()
    elif command == 'play':
        musicPlayer.play()
    elif command.startswith('goto '):
        try:
            song_idx = int(command[len('goto '):])
        except:
            print 'error The command goto should be followed by a number.'
            continue
        if not musicPlayer.gotoSong(song_idx):
            print 'error Song number is out of range.'
    elif command.startswith('volume '):
        change = command[len('volume '):]
        if change == '+' or change == '-':
            musicPlayer.volume(change)
        else:
            print 'error Command should be "volume +" or "volume -"'
    else:
        print 'error Invalid command.'

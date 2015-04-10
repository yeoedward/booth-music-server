# Inspired by https://pypi.python.org/pypi/jukebox-mpg123

from signal import SIGTSTP, SIGTERM, SIGABRT
import sys, os, subprocess
import threading
import time

# Subdirectory to look for music in.
musicDir = 'music'

class MusicPlayer(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        # Extremely coarse-grained lock.
        self.lock = threading.Lock()
        self.songs_idx = 0;
        self.songs = filter(lambda s: s.endswith('.mp3'), os.listdir(musicDir))
        self.proc = None
        self.mpg123 = None
        self.running = True

    def getNextSong(self):
        nextSong = self.songs[self.songs_idx];
        self.songs_idx = (self.songs_idx + 1) % len(self.songs)
        return nextSong

    def run(self):
        # Check if mpg123 is available
        fin, fout = os.popen4(["which", "mpg123"])
        self.mpg123 = fout.read().replace("\n", "")
        if not len(self.mpg123):
            print "error mpg123 not installed"
            return

        self.play()

    def stop(self):
        self.lock.acquire()
        self.running = False
        if self.proc is not None:
            os.kill(self.proc.pid, SIGTSTP)
        self.lock.release()

    def play(self):
        self.lock.acquire()
        self.running = True
        while self.running:
            if self.proc is None:
                song = os.path.join(musicDir, self.getNextSong())
                self.proc = subprocess.Popen(
                    [self.mpg123, song],
                    shell = False,
                    stdout = subprocess.PIPE,
                    stderr = subprocess.PIPE
                )
            else:
                if self.proc.poll() is not None:
                    self.proc = None
            self.lock.release()
            time.sleep(0.5)
            self.lock.acquire()

    def nextSong(self):
        self.lock.acquire()
        if self.proc is not None:
            os.kill(self.proc.pid, SIGTERM)
        self.lock.release()

    def prevSong(self):
        self.lock.acquire()
        self.songs_idx = \
            (self.songs_idx + len(self.songs) - 1) % len(self.songs)
        if self.proc is not None:
            self.songs_idx -= 1
            os.kill(self.proc.pid, SIGTERM)
        self.lock.release()

musicPlayer = MusicPlayer()
musicPlayer.start()

while True:
    command = raw_input()
    if command == 'quit':
        musicPlayer.stop()
        break
    elif command == 'stop':
        musicPlayer.stop()
        # Threads can only be run once, so we create a new object.
        musicPlayer = MusicPlayer()
    elif command == 'play':
        musicPlayer.start()
    elif command == 'next':
        musicPlayer.nextSong()
    elif command == 'prev':
        musicPlayer.prevSong()


# Inspired by https://pypi.python.org/pypi/jukebox-mpg123

from signal import SIGTSTP, SIGTERM, SIGABRT
import sys, os, subprocess
import threading
import time

class MusicPlayer(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        # Extremely coarse-grained lock.
        self.lock = threading.Lock()
        self.songs_idx = 0;
        self.songs = [
            'Lionhearted (Arty Radio Edit).mp3'
        ];
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
            print "mpg123 is not installed"
            return

        print "Starting mpg123 daemon..."
        self.play()

    def stop(self):
        print "Stopping daemon..."
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
                song = self.getNextSong()

                if not os.path.exists(song):
                    print "File not found: %s" %  song
                    continue

                print "Playing " + song
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

    def skipSong(self):
        self.lock.acquire()
        if self.proc is not None:
            os.kill(self.proc.pid, SIGTERM)
        self.lock.release()

musicPlayer = MusicPlayer()
musicPlayer.start()

while True:
    command = raw_input('Command: ')
    if command == 'quit':
        musicPlayer.stop()
        break
    elif command == 'stop':
        musicPlayer.stop()
        # Threads can only be run once, so we create a new object.
        musicPlayer = MusicPlayer()
    elif command == 'play':
        musicPlayer.start()
    elif command == 'skip':
        musicPlayer.skipSong()

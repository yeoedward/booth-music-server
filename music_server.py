# Adapted from https://pypi.python.org/pypi/jukebox-mpg123

from signal import SIGTSTP, SIGTERM, SIGABRT
import daemon
import daemon.pidfile
import sys, os, subprocess
import time

class MusicPlayer:
    songs_idx = 0;
    songs = [
        'Lionhearted (Arty Radio Edit).mp3'
    ];
    proc = None
    mpg123 = None
    daemon_instance = None
    pidFile = None

    def getNextSong(self):
        nextSong = self.songs[self.songs_idx];
        self.songs_idx = (self.songs_idx + 1) % len(self.songs)
        return nextSong

    def start(self):
        # Check if mpg123 is available
        fin, fout = os.popen4(["which", "mpg123"])
        self.mpg123 = fout.read().replace("\n", "")
        if not len(self.mpg123):
            print "mpg123 is not installed"
            return

        self.pidFile = os.path.dirname(os.path.abspath(__file__)) + \
                "/daemon.pid"

        print self.pidFile
        if os.path.exists(self.pidFile):
            print "Daemon already running, pid file exists"
            return

        pid = daemon.pidfile.TimeoutPIDLockFile(
            self.pidFile,
            10
        )

        print "Starting mpg123 daemon..."
        self.daemon_instance = daemon.DaemonContext(
            uid=os.getuid(),
            gid=os.getgid(),
            pidfile=pid,
            working_directory=os.getcwd(),
            detach_process=True,
            signal_map={
                SIGTSTP: self.shutdown,
                SIGABRT: self.skipSong
            }
        )

        with self.daemon_instance:
            self.play()

    def stop(self):
        if not os.path.exists(self.pidFile):
            print "Daemon not running"
            return

        print "Stopping daemon..."
        pid = int(open(self.pidFile).read())
        os.kill(pid, SIGTSTP)

    def play(self):
        while True:
            if self.proc is None:
                song = self.getNextSong()

                if not os.path.exists(song):
                    print "File not found: %s" %  song
                    continue

                print "Playing " + song
                self.proc = subprocess.Popen(
                    [self.mpg123, song]
                )
            else:
                if self.proc.poll() is not None:
                    self.proc = None
            time.sleep(0.5)

    def shutdown(self):
        print "Shutting down..."
        if self.proc is not None:
            os.kill(self.proc.pid, SIGTERM)

        if self.daemon_instance is not None:
            self.daemon_instance.close()
        sys.exit(0)

    def skipSong(self):
        if self.proc is not None:
            os.kill(self.proc.pid, SIGTERM)

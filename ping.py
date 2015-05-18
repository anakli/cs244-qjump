import logging
logger = logging.getLogger(__name__)

class PingManager(object):

    def __init__(self, net, src, dst, dir=None, filename="ping.txt"):
        self.src = net.get(src)
        self.dst = net.get(dst)
        self.logfilename = os.path.join(dir, filename) if dir else filename

    def start(self, interval=0.1):
        args = ("ping", self.dst.IP(), "-i", str(self.interval))
        self.logfile = open(self.logfilename)
        proc = src.popen(args, stdout=self.logfile)
        return proc

    def stop(self):
        self.proc.terminate()

import os.path
import logging
logger = logging.getLogger(__name__)

class PingManager(object):

    def __init__(self, net, src, dst):
        self.src = net.get(src)
        self.dst = net.get(dst)

    def start(self, env=None, interval=0.1, dir=None, filename="ping.txt"):
        logfilename = os.path.join(dir, filename) if dir else filename
        logfile = open(logfilename, "w")
        args = ["ping", self.dst.IP(), "-i", str(interval)]
        logging.info("Starting ping stream at interval %s seconds" % interval)
        self.proc = self.src.popen(args, stdout=logfile, env=env, stderr=logfile)
        return self.proc

    def stop(self):
        self.proc.terminate()

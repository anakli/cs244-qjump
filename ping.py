import os.path
import re
import logging
logger = logging.getLogger(__name__)

class PingManager(object):

    def __init__(self, net, src, dst, dir=None, filename="ping.txt"):
        self.src = net.get(src)
        self.dst = net.get(dst)
        self.logfilename = os.path.join(dir, filename) if dir else filename

    def start(self, env=None, interval=0.1):
        logfile = open(self.logfilename, "w")
        args = ["ping", self.dst.IP(), "-i", str(interval)]
        logging.info("Starting ping stream from %s to %s at interval %s seconds" % (self.src, self.dst, interval))
        self.proc = self.src.popen(args, stdout=logfile, env=env, stderr=logfile)
        return self.proc

    def stop(self):
        self.proc.terminate()

    def get_times(self, logfilename=None):
        """Returns a list of times. Where no return packet was received,
        None is placed in the list."""
        if logfilename is None:
            logfilename = self.logfilename
        logfile = open(self.logfilename)
        times = []
        for line in logfile:
            m = re.match(r"\d+ bytes from \d+\.\d+\.\d+\.\d+\: icmp_seq=(\d+) ttl=(\d+) time=(\d+\.?\d*)", line)
            if not m:
                continue 
            icmp_seq = int(m.group(1))
            time = float(m.group(3))
            times.extend([None] * (icmp_seq - len(times) - 1))
            times.append(time)
        return times

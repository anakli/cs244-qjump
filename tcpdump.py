import logging
import os
logging = logging.getLogger(__name__)
from util import kill_safe

class TcpdumpManager(object):

    def __init__(self, net, raw=False, dir=None, tcpdumpfile="tcpdump_iperf.txt"):
        self.net = net
        self.raw = raw
        self.tcpdumpfile = os.path.join(dir, tcpdumpfile) if dir else tcpdumpfile

    def start(self, client):
        logger.debug("Starting tcpdump on %s..." % client)
        self.tcplogfile = open(self.tcpdumpfile, "w")
        args = ["tcpdump"]
        if self.raw:
            args.extend(["-w", "-"])
        self.proc = self.net.get(client).popen(args, stdout=self.tcplogfile)
        return self.proc

    def stop(self):
        kill_safe(self.proc)
        self.tcplogfile.close()
        self.tcplogfile = None
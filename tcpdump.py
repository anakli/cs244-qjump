import logging
import os
logging = logging.getLogger(__name__)
from util import kill_safe

class TcpdumpManager(object):

    def __init__(self, net, raw=False, dir=None, tcpdumpdir="tcpdump"):
        self.net = net
        self.raw = raw
        self.tcpdumpdir = os.path.join(dir, tcpdumpdir) if dir else tcpdumpdir

    def start(self, interfaces):
        if not isinstance(interfaces, list):
            interfaces = [interfaces]
        self.procs = []
        self.files = []

        for interface in interfaces:
            # extract host, interface, sensible filename
            # arguments are either ('h1', 'h1-eth0') or just 'h1-eth0'
            if isinstance(interface, tuple):
                host, intf = interface
                filename = host + "-" + intf
            else:
                host = interface.split("-")[0]
                intf = interface
                filename = interface

            # start logging
            logger.debug("Starting tcpdump on host %s, interface %s..." % (host, intf))
            filename = os.path.join(tcpdumpdir, filename + (".pcap" if self.raw else ".txt"))
            dumpfile = open(filename, "w")
            args = ["tcpdump", "-i", intf]
            if self.raw:
                args.extend(["-w", "-"])
            proc = self.net.get(host).popen(args, stdout=dumpfile)

            # take note of process and file handles
            self.procs.append(proc)
            self.files.append(dumpfile)

        return self.procs

    def stop(self):
        for proc in self.procs:
            kill_safe(proc)
        for dumpfile in self.files:
            dumpfile.close()
            dumpfile = None
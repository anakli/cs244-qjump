import logging
import sys
import os
import re
from util import kill_safe
logger = logging.getLogger(__name__)

class IperfManager(object):
    """Class to manage Iperf instances on a Mininet network."""

    def __init__(self, net, server, dir=None, filename="iperf.txt"):
        self.net = net
        self.server = net.get(server)
        self.server_proc = None
        self.client_procs = []
        self.logfilename = os.path.join(dir, filename) if dir else filename

    @staticmethod
    def _num2size(num):
        # lazy for now, eventually convert numbers to "16m" etc.
        return str(num)

    def start(self, client, time=10, windowsize="16m", packetlen=1400, protocol="udp"):
        logger.info("Starting iperf stream from %s to %s..." % (client, self.server.name))

        args = ["iperf", "-s", "-w", self._num2size(windowsize)]
        self.server_proc = self.server.popen(args)

        self.logfile = open(self.logfilename, "w")

        args = ["iperf", "-c", self.server.IP(), "-t", str(time), "-i", "1", "-f", "b", "-l", str(packetlen), "-b", "10m"]
        if protocol == "udp":
            args.append("-u")
        logger.info(" ".join(args))
        client_proc = self.net.get(client).popen(args, stdout=self.logfile)
        self.client_procs.append(client_proc)

        return self.client_procs

    def server_is_alive(self):
        retcode = self.server_proc.poll()
        if retcode is not None:
            logger.debug("Iperf server process is dead!")
        return retcode is None

    def clients_are_alive(self):
        alive = []
        for proc in self.client_procs:
            retcode = proc.poll()
            alive.append(retcode is None)
        if not all(alive):
            logger.debug("%d of the iperf processes died!" % alive.count(False))
        return alive

    def stop(self):
        logger.info("Stopping iperf stream(s)...")
        for proc in self.client_procs:
            kill_safe(proc)
        kill_safe(self.server_proc)
        self.logfile.close()
        self.logfile = None

    def get_bandwidths(self, logfilename=None):
        """Returns a list of bandwidths. Where a time period was skipped,
        None is placed in the list. Assumes that -i=1 was used and requires
        that -f=b was used when calling iperf."""
        if logfilename is None:
            logfilename = self.logfilename
        logfile = open(self.logfilename)
        bandwidths = []
        for line in logfile:
            m = re.match(r"\[\s*\d+\]\s*(\d+\.?\d*)-\s*(\d+\.?\d*)\s+sec\s+(\d+\.?\d*) ([KMGkmg]?)Bytes\s+(\d+\.?\d*) ([KMGkmg]?)bits/sec", line)
            if not m:
                continue
            time1 = int(float(m.group(1)))
            bandwidth = float(m.group(5)) / 1e6
            if m.group(4) != "" or m.group(6) != "":
                raise RuntimeError("iperf must be run with --format b.")
            bandwidths.extend([None] * (time1 - len(bandwidths)))
            bandwidths.append(bandwidth)
        logfile.close()
        return bandwidths



import logging
import sys
import os
import re
from util import kill_safe
logger = logging.getLogger(__name__)

class IperfManager(object):
    """Class to manage Iperf instances on a Mininet network."""

    def __init__(self, net, server, dir=None, filename_server="iperf_server.txt", filename_client="iperf_client.txt"):
        self.net = net
        self.server = net.get(server)
        self.server_proc = None
        self.client_procs = []
        self.logfilename_server = os.path.join(dir, filename_server) if dir else filename_server
        self.logfilename_client = os.path.join(dir, filename_client) if dir else filename_client

    @staticmethod
    def _num2size(num):
        # lazy for now, eventually convert numbers to "16m" etc.
        return str(num)

    def start(self, client, time=10, windowsize="16m", packetlen=1400, protocol="udp", env=None):
        logger.info("Starting iperf stream from %s to %s..." % (client, self.server.name))

        args = ["iperf", "-s", "-w", self._num2size(windowsize), "-i", "1"]
        if protocol == "udp":
            args.extend(["-u", "-l", str(packetlen)])
        self.logfile_server = open(self.logfilename_server, "w")
        self.server_proc = self.server.popen(args, env=env, stdout=self.logfile_server)

        args = ["iperf", "-c", self.server.IP(), "-t", str(time), "-i", "1", "-f", "b"]
        if protocol == "udp":
            args.extend(["-u", "-l", str(packetlen), "-b", "10m"])
        logger.info(" ".join(args))
        self.logfile_client = open(self.logfilename_client, "w")
        client_proc = self.net.get(client).popen(args, stdout=self.logfile_client, env=env)
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
        self.logfile_server.close()
        self.logfile_server = None
        self.logfile_client.close()
        self.logfile_client = None

    def get_bandwidths(self, logfilename=None):
        """Returns a list of bandwidths. Where a time period was skipped,
        None is placed in the list. Assumes that -i=1 was used and requires
        that -f=b was used when calling iperf."""
        if logfilename is None:
            logfilename = self.logfilename_client
        logfile = open(logfilename)
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



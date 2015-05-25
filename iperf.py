import logging
import sys
import os
from util import kill_safe
logger = logging.getLogger(__name__)

class IperfManager(object):
    """Class to manage Iperf instances on a Mininet network."""

    def __init__(self, net, server):
        self.net = net
        self.server = net.get(server)
        self.server_proc = None
        self.client_procs = []

    @staticmethod
    def _num2size(num):
        # lazy for now, eventually convert numbers to "16m" etc.
        return str(num)

    def start(self, client, time=10, windowsize="16m", dir=None, filename="iperf.txt"):
        logger.info("Starting iperf stream(s)...")

        args = ["iperf", "-s", "-w", self._num2size(windowsize)]
        self.server_proc = self.server.popen(args)

        logfilename = os.path.join(dir, filename) if dir else filename
        logfile = open(logfilename, "w")

        args = ["iperf", "-c", self.server.IP(), "-t", str(time), "-i", "1"]
        client_proc = self.net.get(client).popen(args, stdout=logfile)
        self.client_procs.append(client_proc)

        return client_proc

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

import logging
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

    def start(self, client, time=10, windowsize="16m"):
        logger.info("Starting iperf server...")

        args = ["iperf", "-s", "-w", self._num2size(windowsize)]
        self.server_proc = self.server.popen(args)

        args = ["iperf", "-c", self.server.IP(), "-t", str(time)]
        client_proc = self.net.get(client).popen(args)
        self.client_procs.append(client_proc)

        return client_proc

    def stop(self):
        for proc in self.client_procs:
            proc.terminate()
        self.server_proc.terminate()


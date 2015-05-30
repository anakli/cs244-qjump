import logging
import os
from mininet.link import Intf
logger = logging.getLogger(__name__)
from util import kill_safe

class TcpdumpManager(object):

    def __init__(self, net, raw=False, dir=None, tcpdumpdir="tcpdump"):
        self.net = net
        self.raw = raw
        self.tcpdumpdir = os.path.join(dir, tcpdumpdir) if dir else tcpdumpdir
        os.makedirs(self.tcpdumpdir)

    def _resolve_interface_arg(self, arg):
        """Returns tuple: (Node object, intfname, filename)"""
        if isinstance(arg, Intf):
            return arg.node, arg.name, arg.name
        if isinstance(arg, tuple):
            nodename, intfname = arg
            return self.net.get(nodename), intfname, nodename + "-"  + intfname
        if isinstance(arg, str):
            return self.net.get(arg.split("-")[0]), arg, arg
        raise TypeError(arg)

    def start(self, interfaces):
        self.procs = []
        self.files = []

        for interface in interfaces:
            node, intfname, filename = self._resolve_interface_arg(interface)

            # start logging
            logger.debug("Starting tcpdump on node %s, interface %s..." % (node.name, intfname))
            filename = os.path.join(self.tcpdumpdir, filename + (".pcap" if self.raw else ".txt"))
            dumpfile = open(filename, "w")
            args = ["tcpdump", "-i", intfname]
            if self.raw:
                args.extend(["-w", "-"])
            proc = node.popen(args, stdout=dumpfile)

            # take note of process and file handles
            self.procs.append(proc)
            self.files.append(dumpfile)

        return self.procs

    def start_all(self):
        def all_intfs():
            for node in self.net.values():
                for intf in node.intfList():
                    if intf.name == "lo": continue
                    yield intf
                non_vlan_intfs = set(i.split(".")[0] for i in node.intfNames()) - set(node.intfNames())
                for intf in non_vlan_intfs:
                    if intf == "lo": continue
                    yield intf
        self.start(all_intfs())

    def stop(self):
        for proc in self.procs:
            kill_safe(proc)
        for dumpfile in self.files:
            dumpfile.close()
            dumpfile = None

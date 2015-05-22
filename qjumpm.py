import os.path
import logging
logger = logging.getLogger(__name__)

import subprocess

class QJumpManager(object):

    DEFAULT_MODULE_CONFIG = {
        "verbose": 4,
        "timeq": 15,
        "bytesq": 1550,
    }

    def install_module(self, **kwargs):
        """Installs the qjump module, uninstalling the existing one if it was already installed."""
        if self.is_module_installed():
            self.remove_module()

        args = ["insmod", "sch_qjump.ko"]
        for item in self.DEFAULT_MODULE_CONFIG.iteritems():
            kwargs.setdefault(*item)
        args.extend("%s=%s" % (k, v) for k, v in kwargs.iteritems())
        logger.info("Installing: " + " ".join(args))
        subprocess.call(args)

    def remove_module(self):
        logger.info("Removing qjump module")
        subprocess.call(["rmmod", "sch_qjump"])

    def is_module_installed(self):
        retcode = subprocess.call("lsmod | grep sch_qjump", shell=True)
        return retcode == 0

    def create_env(self, verbosity=0, priority=0, window=9999999):
        """Creates an environment variables dict that can be passed to a
        subprocess.Popen constructor in order to run that command with
        qjump."""
        new_env = dict(os.environ)
        new_env["QJAU_VERBOSITY"] = str(verbosity)
        new_env["QJAU_PRIORITY"]  = str(priority)
        new_env["QJAU_WINDOW"] = str(window)
        new_env["LD_PRELOAD"] = "./qjump-app-util.so"
        return new_env
        
               
    def _install_qjump(self, node, ifname):
        """Installs qjump on a particular node and interface."""
        _, err, exitcode = node.pexec("tc qdisc add dev %s parent 5:1 handle 6: qjump" % ifname)
        if exitcode != 0:
            print("Error binding qjump to port %s:" % ifname)
            print err
        return exitcode

    def install_qjump(self, net):
        """Installs qjump on all interfaces and nodes in a network."""
        results = []
        ifnames = []
        for nodename in net:
            node = net.get(nodename)
            for ifname in node.intfNames():
                if ifname == "lo":
                    continue
                ifnames.append(ifname)
                results.append(self._install_qjump(node, ifname))
        if all(r == 0 for r in results):
            print("Installed QJump on all ports: " + ", ".join(ifnames))
        else:
            raise RuntimeError("Could not install QJump")


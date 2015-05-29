import os.path
import logging
logger = logging.getLogger(__name__)

import subprocess
from util import check_pexec

class QJumpManager(object):

    DEFAULT_MODULE_CONFIG = {
        "verbose": 5,
    }
    VLAN_ID = "2"

    def __init__(self, dir="."):
        self.dir = dir

    def install_module(self, **kwargs):
        """Installs the qjump module, uninstalling the existing one if it was already installed."""
        if self.is_module_installed():
            self.remove_module()

        args = ["insmod", "sch_qjump.ko"]
        for item in self.DEFAULT_MODULE_CONFIG.iteritems():
            kwargs.setdefault(*item)
        args.extend("%s=%s" % (k, v) for k, v in kwargs.iteritems())
        logger.info("Installing: " + " ".join(args))
        try:
            subprocess.check_call(args)
        except subprocess.CalledProcessError as e:
            logger.error("Error installing qjump: " + str(e))

    def remove_module(self):
        try:
            subprocess.check_call(["rmmod", "sch_qjump"])
        except subprocess.CalledProcessError as e:
            logger.error("Error removing qjump: " + str(e))
            return False
        logger.info("Removing qjump module")
        return True
        
    def is_module_installed(self):
        exitcode = subprocess.call("lsmod | grep sch_qjump", shell=True, stdout=subprocess.PIPE)
        return exitcode == 0
    
    def is_8021q_installed(self):
        exitcode = subprocess.call("lsmod | grep 8021q", shell=True, stdout=subprocess.PIPE)
        return exitcode == 0

    def install_8021q(self):
        if self.is_8021q_installed():
            logger.debug("802.1Q kernel module is already installed")
            return
        try:
            subprocess.check_call(["modprobe", "8021q"])
        except subprocess.CalledProcessError as e:
            logger.error("Error installing 802.1Q kernel module: " + str(e))
            return False
        logger.info("Installed the 802.1Q kernel module")
        return True

    def _config_8021q(self, node, ifname):
        try:
            check_pexec(node, ["vconfig", "add", ifname, self.VLAN_ID])
            for i in range(8):
                check_pexec(node, ["vconfig", "set_egress_map", ifname + "." + self.VLAN_ID, str(i), str(i)])
                check_pexec(node, ["vconfig", "set_ingress_map", ifname + "." + self.VLAN_ID, str(i), str(i)])
        except subprocess.CalledProcessError as e:
            logger.error("Error configuring 802.1Q kernel module: " + str(e))
            return False
        return True

    def config_8021q(self, net):
        results = []
        ifnames = []
        for host in net.hosts:
            for ifname in host.intfNames():
                if ifname == "lo": continue
                ifnames.append(ifname)
                results.append(self._config_8021q(host, ifname))
        if all(results):
            logger.info("Configured 802.1Q on all ports: " + ", ".join(ifnames))
        else:
            logger.error("Error configuring 802.1Q")
            raise RuntimeError("Could not configure 802.1Q")

    def _log_vlan(self, host, ifname, vlandir):
        out, err, exitcode = host.pexec(["cat", "/proc/net/vlan/%s.%s" % (ifname, self.VLAN_ID)])
        logfile = open(os.path.join(vlandir, host.name + "-" + ifname + "-vlan.txt"), "w")
        logfile.write(out)
        logfile.write(err)
        logfile.write("exit code: %d" % exitcode)
        logfile.close()
    
    def log_vlan(self, net):
        vlandir = os.path.join(self.dir, "vlan")
        os.makedirs(vlandir)
        for host in net.hosts:
            for ifname in host.intfNames():
                if ifname == "lo": continue
                self._log_vlan(host, ifname, vlandir)

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
        
    def _install_qjump(self, node, ifname, tc_child):
        """Installs qjump on a particular node and interface."""
        try:
            if tc_child:
                check_pexec(node, "tc qdisc add dev %s parent 5:1 handle 6: qjump" % ifname)
            else:
                check_pexec(node, "tc qdisc add dev %s root qjump" % ifname)
        except subprocess.CalledProcessError as e:
            logger.error("Error binding qjump to port %s: " % ifname + str(e))
            return False
        return True

    def install_qjump(self, net, tc_child):
        """Installs qjump on all interfaces and nodes in a network."""
        results = []
        ifnames = []
        for node in net.hosts:
            intfnames = set(i.split(".")[0] for i in node.intfNames())
            for ifname in intfnames:
                if ifname == "lo":
                    continue
                ifnames.append(ifname)
                results.append(self._install_qjump(node, ifname, tc_child))
        if all(results):
            logger.info("Installed QJump on all ports: " + ", ".join(ifnames))
        else:
            raise RuntimeError("Could not install QJump")


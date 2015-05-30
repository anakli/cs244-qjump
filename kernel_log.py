import subprocess
import os
from util import kill_safe
import logging
logger = logging.getLogger(__name__)

class KernelLogManager(object):
    
    def __init__(self, dir="."):
        self.dir = dir

    def start(self, dir=".", logfilename="kernel_log.txt"):
        self.logfilename = os.path.join(self.dir, logfilename)
        self.logfile = open(self.logfilename, "w")
        self.proc = subprocess.Popen("tail /var/log/kern.log -f | grep QJump", shell=True, stdout=self.logfile)
    
    def stop(self):
        kill_safe(self.proc)
        self.logfile.close()

    def process(self, filename="kernel_stats.txt"):
        pass


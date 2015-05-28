import os.path
import logging
logger = logging.getLogger(__name__)

import matplotlib 
matplotlib.use('Agg') 
import matplotlib.pyplot as plt 
import numpy as np 
from matplotlib import pylab 

class Plotter(object):

    def __init__(self, app_alone=None, app_noQjump=None, app_Qjump=None):
        self.app_alone = app_alone
        self.app_noQjump = app_noQjump
        self.app_Qjump = app_Qjump

    def plotCDFs(self,dir=None, figname="pingCDFfig"):
        figname = os.path.join(dir, figname) if dir else figname
        logging.info("Plotting CDF...")
        
        plt.clf()        

        if self.app_alone:
           logging.info("Plotting app alone data...")
           self.plotCDF(self.app_alone, 'b', 'solid', dir, figname, "ping")

        if self.app_noQjump:
           logging.info("Plotting app without Qjump data...")
           self.plotCDF(self.app_noQjump, 'r', 'dashed', dir, figname, "ping+iperf w/out QJump")

        if self.app_Qjump:
           logging.info("Plotting app with Qjump data...")
           self.plotCDF(self.app_Qjump, 'g', 'dotted', dir, figname, "ping+iperf w/ QJump")

    def plotCDF(self, values, color='b', style='solid', dir=None, figname="pingCDFfig", label=""):
        min_val = np.min(values)
        max_val = np.max(values)
        bin_width = 1
        bin_range = max_val - min_val
        num_bins = min(2500, bin_range / bin_width)
        print "Binning into %d bins and plotting..." % (num_bins) 
        # plot a cumulative histogram line diagram
        (n, bins, patches) = plt.hist(values, log=False, normed=True,
                                  cumulative=True, histtype="step",
                                  linestyle=style, color=color, label=label)
        # discard last datapoint to make plot neater (no bar plot-like drop)
        patches[0].set_xy(patches[0].get_xy()[:-1])
        #plt.xlim(0, 100)
        #plt.xticks([0, 1000, 2000, 3000, 4000], ['0', '1', '2', '3', '4'], ha='left')
        #plt.ylim(0, 1.0)
        #plt.yticks(np.arange(0, 1.01, 0.2), [str(x) for x in np.arange(0, 1.01, 0.2)])
        plt.legend(loc='lower right', handletextpad=0.2, frameon=True,
            borderaxespad=0.2, handlelength=2.5)
        plt.xlabel("Latency in ms")
        plt.title("Latency CDF")
        plt.savefig("%s.pdf" % figname, format="pdf", bbox_inches='tight')

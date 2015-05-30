import os.path
import logging
logger = logging.getLogger(__name__)

import matplotlib 
matplotlib.use('Agg') 
import matplotlib.pyplot as plt 
import numpy as np 
from matplotlib import pylab 

class Plotter(object):

    def plotCDFs(self, app_alone=None, app_noQjump=None, app_Qjump=None, dir=None, figname="pingCDFfig"):
        logging.info("Plotting CDF...")
        plt.clf()

        if app_alone:
           logging.info("Plotting app alone data...")
           self._plotCDF(app_alone, 'b', 'solid', "ping")

        if app_Qjump:
           logging.info("Plotting app with Qjump data...")
           self._plotCDF(app_Qjump, 'g', 'dotted', "ping+iperf w/ QJump")

        if app_noQjump:
           self._finalize(dir, figname + "-detail")
           logging.info("Plotting app without Qjump data...")
           self._plotCDF(app_noQjump, 'r', 'dashed', "ping+iperf w/out QJump")

        self._finalize(dir, figname)

    def plotCDF(self, values, color='b', style='solid', label="", dir=None, figname="pingCDFfig"):
        self._plotCDF(values, color, style, label)
        self._finalize(dir, figname, legend=False)

    def _finalize(self, dir, figname, legend=True):
        figname = os.path.join(dir, figname) if dir else figname
        plt.xlabel("Latency in ms")
        plt.title("Latency CDF")
        if legend:
            plt.legend(loc='lower right', handletextpad=0.2, frameon=True,
                borderaxespad=0.2, handlelength=2.5)
        plt.savefig("%s.pdf" % figname, format="pdf", bbox_inches='tight')
        plt.savefig("%s.png" % figname, format="png", bbox_inches='tight')

    def _plotCDF(self, values, color='b', style='solid', label=""):
        min_val = np.min(values)
        max_val = np.max(values)
        bin_width = 0.001
        bin_range = max_val - min_val
        num_bins = min(2500, bin_range / bin_width)
        print "Binning into %d bins and plotting..." % (num_bins) 
        # plot a cumulative histogram line diagram
        (n, bins, patches) = plt.hist(values, log=False, normed=True,
                                  cumulative=True, histtype="step",
                                  linestyle=style, color=color, label=label,
                                  bins=num_bins)
        # discard last datapoint to make plot neater (no bar plot-like drop)
        patches[0].set_xy(patches[0].get_xy()[:-1])
        plt.ylim(0, 1)

#!/usr/bin/python

"CS244 Spring 2015 Assignment 3: Reproducing QJump paper results [NSDI'15]"

from mininet.topo import Topo
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.net import Mininet
from mininet.log import lg, info
from mininet.util import dumpNodeConnections
from mininet.cli import CLI

from subprocess import Popen, PIPE
from time import sleep, time
from multiprocessing import Process
from argparse import ArgumentParser

import sys
import os
import os.path
import math


# TODO: Don't just read the TODO sections in this code.  Remember that
# one of the goals of this assignment is for you to learn how to use
# Mininet. :-)

parser = ArgumentParser(description="Qjump arguments")
parser.add_argument('--bw-link', '-B',
                    type=float,
                    help="Bandwidth of host links (Mb/s)",
                    default=10)

parser.add_argument('--dir', '-d',
                    help="Directory to store outputs",
                    default='results')

parser.add_argument('--time', '-t',
                    help="Duration (sec) to run the experiment",
                    type=int,
                    default=10)

# Linux uses CUBIC-TCP by default 
parser.add_argument('--cong',
                    help="Congestion control algorithm to use",
                    default="cubic")

# Expt parameters
args = parser.parse_args()



class SimpleTopo(Topo):
    "Simple topology for qjump experiment."

    def build(self, n=2):


        # Here we create a switch.  If you change its name, its
        # interface names will change from s0-eth1 to newname-eth1.
        switch = self.addSwitch('s0')

        #create two hosts and links
	host1 = self.addHost('h1')
	self.addLink(host1, switch, bw=args.bw_link)

	host2 = self.addHost('h2')
	self.addLink(host2, switch, bw=args.bw_link)

        return

def start_iperf(net):
    h2 = net.get('h2')
    print "Starting iperf server..."
    server = h2.popen("iperf -s -w 16m")
    h1 = net.get('h1')
    client = h1.popen("iperf -c %s -t %s" % (h2.IP(), args.time))
    return client


def start_ping(net):
    h1 = net.get('h1')
    h2 = net.get('h2')
    filename = os.path.join(args.dir, "ping.txt")
    proc = h1.popen("ping %s -i 0.1 > %s" % (h2.IP(), filename), shell=True)
    return proc

def qjump():
    if not os.path.exists(args.dir):
        os.makedirs(args.dir)
    os.system("sysctl -w net.ipv4.tcp_congestion_control=%s" % args.cong)
    topo = SimpleTopo()
    net = Mininet(topo=topo, host=CPULimitedHost, link=TCLink)
    net.start()
    # This dumps the topology and how nodes are interconnected through
    # links.
    dumpNodeConnections(net.hosts)
    # This performs a basic all pairs ping test.
    net.pingAll()

    ping = start_ping(net)

    # Start iperf, webservers, etc.
    start_iperf(net)
    
    ping.terminate()
    net.stop()

if __name__ == "__main__":
    qjump()

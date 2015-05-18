#!/usr/bin/python

"CS244 Spring 2015 Assignment 3: Reproducing QJump paper results [NSDI'15]"

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
import time

from iperf import IperfManager
from ping import PingManager

def qjump(topocls, src, dst, dir=".", expttime=10, cong="cubic"):
    os.system("sysctl -w net.ipv4.tcp_congestion_control=%s" % cong)
    topo = topocls()
    net = Mininet(topo=topo, host=CPULimitedHost, link=TCLink)
    net.start()

    dumpNodeConnections(net.hosts)
    net.pingAll()

    iperfm = IperfManager(net, 'h2')
    iperfm.start('h1', time=expttime)

    pingm = PingManager(net, 'h1', 'h2', dir=dir)
    pingm.start()

    time.sleep(expttime)

    pingm.stop()
    iperfm.stop()
    net.stop()

if __name__ == "__main__":
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
    parser.add_argument('--cong',
                        help="Congestion control algorithm to use",
                        default="cubic") # Linux uses CUBIC-TCP by default
    args = parser.parse_args()

    if not os.path.exists(args.dir):
        os.makedirs(args.dir)

    from topos import SimpleTopo
    qjump(SimpleTopo, 'h1', 'h2', dir=args.dir, expttime=args.time, cong=args.cong)

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

def _install_qjump(net, node, ifname):
    out, err, exitcode = host.pexec("tc qdisc add dev %s-%s parent 5:1 handle 6: qjump" % (node.name, ifname))
    if exitcode != 0:
        print("Error binding qjump to port %s-%s:" % (node.name, ifname))
        print err
    return exitcode

def install_qjump(net):
    results = []
    for node in net:
        for ifname in node.intfNames():
            results.append(_install_qjump(node, ifname))
    if all(r == 0 for r in results):
        print("Installed QJump on all ports")
    else:
        raise RuntimeError("Could not install QJump")

def qjump(topocls, src, dst, dir=".", expttime=10, cong="cubic", iperf=True, qjump=True):
    os.system("sysctl -w net.ipv4.tcp_congestion_control=%s" % cong)
    topo = topocls()

    try:
        net = Mininet(topo=topo, host=CPULimitedHost, link=TCLink)
        net.start()

        dumpNodeConnections(net.hosts)
        net.pingAll()

        if iperf:
            iperfm = IperfManager(net, 'h2')
            iperfm.start('h1', time=expttime)

        if qjump:
            install_qjump(net)

        pingm = PingManager(net, 'h1', 'h2', dir=dir)
        pingm.start()

        time.sleep(expttime)

    finally:
        pingm.stop()
        if iperf:
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
    parser.add_argument('--no-qjump', dest="qjump",
                        help="Don't use QJump",
                        action="store_false",
                        default=True)
    parser.add_argument('--no-iperf', dest="iperf",
                        help="Don't use Iperf",
                        action="store_false",
                        default=True)
    parser.add_argument('--verbosity', '-v',
                        help="Logging level",
                        default="info")
    args = parser.parse_args()
    lg.setLogLevel(args.verbosity)

    if not os.path.exists(args.dir):
        os.makedirs(args.dir)

    from topos import SimpleTopo
    qjump(SimpleTopo, 'h1', 'h2', dir=args.dir, expttime=args.time,
            cong=args.cong, iperf=args.iperf, qjump=args.qjump)

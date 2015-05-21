#!/usr/bin/python

"CS244 Spring 2015 Assignment 3: Reproducing QJump paper results [NSDI'15]"

from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.net import Mininet
from mininet.util import dumpNodeConnections
from mininet.cli import CLI
import mininet.log

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
from qjumpm import QJumpManager

def _install_qjump(node, ifname):
    _, err, exitcode = node.pexec("tc qdisc add dev %s parent 5:1 handle 6: qjump" % ifname)
    if exitcode != 0:
        print("Error binding qjump to port %s:" % ifname)
        print err
    return exitcode

def install_qjump(net):
    results = []
    ifnames = []
    for nodename in net:
        node = net.get(nodename)
        for ifname in node.intfNames():
            if ifname == "lo":
                continue
            ifnames.append(ifname)
            results.append(_install_qjump(node, ifname))
    if all(r == 0 for r in results):
        print("Installed QJump on all ports: " + ", ".join(ifnames))
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

        if qjump:
            #install_qjump(net)
            qjumpm = QJumpManager()
            qjumpm.install_qjump(net)
            hpenv = qjumpm.create_env(priority=7)
        else:
            hpenv = None

        if iperf:
            iperfm = IperfManager(net, 'h2')
            iperfm.start('h1', time=expttime)

        pingm = PingManager(net, 'h1', 'h2', dir=dir)
        pingm.start(new_env=hpenv)

        start = time.time()
        while time.time() - start < expttime:
            sys.stdout.write("%.1f seconds remaining...\r" % (expttime + start - time.time()))
            sys.stdout.flush()
            if iperf:
                if not iperfm.server_is_alive():
                    raise RuntimeError("Iperf server is dead!")
                clients_alive = iperfm.clients_are_alive()
                if not all(clients_alive):
                    raise RuntimeError("%d iperf client(s) are dead!" % clients_alive.count(False))
        
        print("Done.")

    except Exception as e:
        print("Error: " + str(e))
        import traceback
        traceback.print_exc()

    finally:
        if 'pingm' in locals():
            pingm.stop()
        if 'iperfm' in locals() and iperf:
            iperfm.stop()
        if 'net' in locals():
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
    mininet.log.lg.setLogLevel(args.verbosity)

    import logging
    logging.basicConfig(level=mininet.log.LEVELS[args.verbosity])

    if not os.path.exists(args.dir):
        os.makedirs(args.dir)

    from topos import SimpleTopo
    qjump(SimpleTopo, 'h1', 'h2', dir=args.dir, expttime=args.time,
            cong=args.cong, iperf=args.iperf, qjump=args.qjump)

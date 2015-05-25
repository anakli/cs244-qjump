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
from plotter import Plotter

def qjump(topo, iperf_src, iperf_dst, ping_src, ping_dst, dir=".", expttime=10, cong="cubic", iperf=True, qjump=True):
    os.system("sysctl -w net.ipv4.tcp_congestion_control=%s" % cong)

    try:
        net = Mininet(topo=topo, link=TCLink)
        net.start()

        dumpNodeConnections(net.hosts)
        net.pingAll()

        if qjump:
            qjumpm = QJumpManager()
            qjumpm.install_8021q()
            qjumpm.config_8021q(net)
            qjumpm.install_module(p0rate=1, p1rate=5, p3rate=30, p4rate=15, p5rate=0, p6rate=0, p7rate=300)
            qjumpm.install_qjump(net)
            hpenv = qjumpm.create_env(priority=0)
        else:
            hpenv = None

        if iperf:
            iperfm = IperfManager(net, iperf_dst, dir=dir)
            iperfm.start(iperf_src, time=expttime)

        pingm = PingManager(net, ping_src, ping_dst, dir=dir)
        pingm.start(env=hpenv)

        start = time.time()
        last_report = expttime
        while time.time() - start < expttime:
            secs_remaining = int(expttime + start - time.time())
            if secs_remaining != last_report:
                sys.stdout.write("%d seconds remaining...\r" % secs_remaining)
                sys.stdout.flush()
                last_report = secs_remaining
            if iperf:
                if not iperfm.server_is_alive():
                    raise RuntimeError("Iperf server is dead!")
                clients_alive = iperfm.clients_are_alive()
                if not all(clients_alive):
                    raise RuntimeError("%d iperf client(s) are dead!" % clients_alive.count(False))
        
        print("Done.")

        print sorted(pingm.get_times())
        if iperf:
            print iperfm.get_bandwidths()
        # plotter = Plotter(pingm.get_times())
        # plotter.plotCDFs(dir=args.dir, figname="pingCDF")
        
    except Exception as e:
        print("Error: " + str(e))
        import traceback
        traceback.print_exc()

    finally:
        if 'pingm' in locals():
            pingm.stop()
        if 'iperfm' in locals() and iperf:
            iperfm.stop()
        if 'qjumpm' in locals():
            qjumpm.remove_module()
        if 'net' in locals():
            try:
                net.stop()
            except Exception as e:
                print e

    return pingm.get_times()

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
    parser.add_argument('--runall',
                        help="Run ping alone, with iperf no qjump, with qjump",
                        action="store_true",
                        default=False)
    parser.add_argument('--topo', choices=("simple", "dc"),
                        type=str, help="Topology to use",
                        default="simple")
    args = parser.parse_args()
    mininet.log.lg.setLogLevel(args.verbosity)

    import logging
    logging.basicConfig(level=mininet.log.LEVELS[args.verbosity])

    if not os.path.exists(args.dir):
        os.makedirs(args.dir)

    kwargs = dict(dir=args.dir, expttime=args.time, cong=args.cong)

    if args.topo == "simple":
        from topos import SimpleTopo
        topo = SimpleTopo(bw=args.bw_link)
        kwargs.update(dict(iperf_src='h1', iperf_dst='h2', ping_src='h1', ping_dst='h2'))
    elif args.topo == "dc":
        from topos import DCTopo
        topo = DCTopo(bw=args.bw_link)
        kwargs.update(dict(iperf_src='h7', iperf_dst='h10', ping_src='h8', ping_dst='h10'))

    if args.runall:
        print "********** Running all tests for Figure 3..."
        print "********** Running ping alone..."
        ping_alone = qjump(topo, iperf=False, qjump=False, **kwargs)
        print "********** Running ping + iperf, no Qjump..."
        ping_noQjump = qjump(topo, iperf=True, qjump=False, **kwargs)
        print "********** Running ping + iperf with Qjump..."
        ping_Qjump = qjump(topo, iperf=True, qjump=True, **kwargs)
        
        plotter = Plotter(ping_alone, ping_noQjump, ping_Qjump)
        plotter.plotCDFs(dir=args.dir, figname="pingCDFs")

    else:
        qjump(topo, iperf=args.iperf, qjump=args.qjump, **kwargs)



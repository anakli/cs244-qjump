#!/usr/bin/python

"CS244 Spring 2015 Assignment 3: Reproducing QJump paper results [NSDI'15]"

from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.net import Mininet
from mininet.util import dumpNodeConnections
import mininet.log

import subprocess
from argparse import ArgumentParser

import sys
import os
import os.path
import time
import logging
logger = logging.getLogger(__name__)

from iperf import IperfManager
from ping import PingManager
from qjumpm import QJumpManager
from plotter import Plotter

DEFAULT_QJUMP_MODULE_ARGS = dict(timeq=15, bytesq=1550, p0rate=1, p1rate=5, p3rate=30, p4rate=15, p5rate=0, p6rate=0, p7rate=300)
DEFAULT_QJUMP_ENV_ARGS = dict(priority=0, window=15500)
DEFAULT_RESULTS_DIR = "."

def log_arguments(topo, **kwargs):
    argsfile = open(os.path.join(kwargs.get("dir", DEFAULT_RESULTS_DIR), "args.txt"), "w")
    argsfile.write("Started at " + time.asctime() + "\n")
    argsfile.write("Git commit: " + subprocess.check_output(['git', 'rev-parse', 'HEAD']) + "\n")
    argsfile.write("Topology: " + topo.description_for_qjump + "\n")
    argsfile.write("\nQJump module arguments:\n")
    for name, value in sorted(kwargs["qjump_module_args"].items()):
        argsfile.write(" {0:>15} = {1}\n".format(name, value))
    argsfile.write("\nQJump environment arguments:\n")
    for name, value in sorted(kwargs["qjump_env_args"].items()):
        argsfile.write(" {0:>15} = {1}\n".format(name, value))
    argsfile.write("\nOther keyword arguments:\n")
    kwargs = dict(kwargs)
    kwargs.pop("qjump_module_args")
    kwargs.pop("qjump_env_args")
    for name, value in sorted(kwargs.items()):
        argsfile.write(" {0:>15} = {1}\n".format(name, value))

def make_results_dir(dir):
    if dir is None:
        dir = os.path.join("results", "results" + time.strftime("%Y%m%d-%H%M%S"))
        if os.path.exists("last"):
            os.unlink("last")
        os.symlink(dir, "last")
    if not os.path.exists(dir):
        os.makedirs(dir)
    return dir

def update_qjump_args(kwargs):
    module_args = dict(DEFAULT_QJUMP_MODULE_ARGS)
    if "qjump_module_args" in kwargs:
        module_args.update(kwargs["qjump_module_args"])
    env_args = dict(DEFAULT_QJUMP_ENV_ARGS)
    if "qjump_env_args" in kwargs:
        env_args.update(kwargs["qjump_env_args"])
    kwargs["qjump_module_args"] = module_args
    kwargs["qjump_env_args"] = env_args

def qjump_all(*args, **kwargs):
    """Runs all three tests for Figure 3a. Replaces 'iperf' and 'qjump'
    arguments with its own."""

    dirname = make_results_dir(kwargs.get("dir", DEFAULT_RESULTS_DIR))
    kwargs["dir"] = dirname
    update_qjump_args(kwargs)
    log_arguments(*args, **kwargs)

    print("*** Test for ping alone")
    os.mkdir(os.path.join(dirname, "ping-alone"))
    kwargs.update(dict(iperf=False, qjump=False, dir=os.path.join(dirname, "ping-alone")))
    ping_alone = qjump(*args, **kwargs)

    print("*** Test for ping + iperf without QJump")
    os.mkdir(os.path.join(dirname, "ping-iperf-noqjump"))
    kwargs.update(dict(iperf=True, qjump=False, dir=os.path.join(dirname, "ping-iperf-noqjump")))
    ping_noQjump = qjump(*args, **kwargs)

    print("*** Test for ping + iperf with QJump")
    os.mkdir(os.path.join(dirname, "ping-iperf-qjump"))
    kwargs.update(dict(iperf=True, qjump=True, dir=os.path.join(dirname, "ping-iperf-qjump")))
    ping_Qjump = qjump(*args, **kwargs)
    if ping_Qjump.count(None) > 0:
        logger.warning("Ignoring %d dropped ping packets in QJump run", ping_Qjump.count(None))
    ping_Qjump = filter(lambda x: x is not None, ping_Qjump)
    plotter = Plotter(ping_alone, ping_noQjump, ping_Qjump)
    plotter.plotCDFs(dir=dirname, figname="pingCDFs")

def qjump_once(*args, **kwargs):
    dirname = make_results_dir(kwargs.get("dir", DEFAULT_RESULTS_DIR))
    kwargs["dir"] = dirname
    update_qjump_args(kwargs)
    log_arguments(*args, **kwargs)
    qjump(*args, **kwargs)

def qjump(topo, iperf_src, iperf_dst, ping_src, ping_dst, dir=".", expttime=10, \
        cong="cubic", iperf=True, qjump=True, tc_child=False, qjump_module_args=dict(), \
        qjump_env_args=dict(), ping_interval=0.01):

    try:
        subprocess.check_call(["sysctl", "-w", "net.ipv4.tcp_congestion_control=%s" % cong])
    except subprocess.CalledProcessError as e:
        logger.error("Error setting TCP congestion control algorithm: " + str(e))

    try:
        net = Mininet(topo=topo, link=TCLink)
        net.start()

        dumpNodeConnections(net.hosts)
        net.pingAll()

        if qjump:
            qjumpm = QJumpManager()
            qjumpm.install_8021q()
            qjumpm.config_8021q(net)
            qjumpm.install_module(**qjump_module_args)
            qjumpm.install_qjump(net, tc_child)
            hpenv = qjumpm.create_env(**qjump_env_args)
        else:
            hpenv = None

        if iperf:
            iperfm = IperfManager(net, iperf_dst, dir=dir)
            iperfm.start(iperf_src, time=expttime)

        pingm = PingManager(net, ping_src, ping_dst, dir=dir)
        pingm.start(env=hpenv, interval=ping_interval)

        start = time.time()
        last_report = expttime
        while time.time() - start < expttime:
            time.sleep(0.5)
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

        resultsfile = open(os.path.join(dir, "results.txt"), "w")
        resultsfile.write("Ping results:\n")
        resultsfile.write(", ".join(map(str, pingm.get_times())))
        resultsfile.write("\nPing results, sorted:\n")
        resultsfile.write(", ".join(map(str, sorted(pingm.get_times()))))
        if iperf:
            resultsfile.write("\n\nIperf bandwidths:\n")
            resultsfile.write(", ".join(map(str, iperfm.get_bandwidths())))
        resultsfile.close()    

        print "ping times:", sorted(pingm.get_times())
        if iperf:
            print "iperf bandwidths:", iperfm.get_bandwidths()

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
            try:
                net.stop()
            except Exception as e:
                print e
        if 'qjumpm' in locals():
            qjumpm.remove_module()

    try:
        return pingm.get_times()
    except NameError:
        return []

if __name__ == "__main__":
    parser = ArgumentParser(description="Qjump arguments")
    parser.add_argument('--bw-link', '-B', type=str, help="Bandwidth of host links (Mb/s)", default="10")
    parser.add_argument('--dir', '-d', help="Directory to store outputs", default=None)
    parser.add_argument('--time', '-t', help="Duration (sec) to run the experiment", type=int, default=10)
    parser.add_argument('--cong', help="Congestion control algorithm to use", default="cubic") # Linux uses CUBIC-TCP by default
    parser.add_argument('--no-qjump', dest="qjump", help="Don't use QJump", action="store_false", default=True)
    parser.add_argument('--no-iperf', dest="iperf", help="Don't use Iperf", action="store_false", default=True)
    parser.add_argument('--verbosity', '-v', help="Logging level", default="info")
    parser.add_argument('--topo', choices=("simple", "dc"), type=str, help="Topology to use", default="simple")
    parser.add_argument("--ping-interval", type=float, help="Ping interval", default=0.01)
    parser.add_argument("--bytesq", "-b", type=int, help="QJump's bytesq option", default=None)
    parser.add_argument("--timeq", type=int, help="Qjump's timeq option", default=None)
    parser.add_argument("--priority", dest="ping_priority", type=int, help="Priority level for ping", default=None)
    parser.add_argument("--qjump-window", "--qjw", type=int, help="QJump environment's window for ping", default=None)
    parser.add_argument("--all-priorities", action="store_true", help="Loop through all priorities", default=False)
    parser.add_argument('--runall', '--all',
                        help="Run ping alone, with iperf no qjump, with qjump",
                        action="store_true",
                        default=False)
    args = parser.parse_args()
    mininet.log.lg.setLogLevel(args.verbosity)

    import logging
    logging.basicConfig(level=mininet.log.LEVELS[args.verbosity])

    if "none".startswith(args.bw_link.lower()):
        bw_link = None
    else:
        bw_link = float(args.bw_link)

    qjump_module_args = dict()
    qjump_env_args = dict()
    if args.bytesq is not None:
        qjump_module_args["bytesq"] = args.bytesq
    if args.timeq is not None:
        qjump_module_args["timeq"] = args.timeq
    if args.ping_priority is not None:
        qjump_env_args["priority"] = args.ping_priority
    if args.qjump_window is not None:
        qjump_env_args["window"] = args.qjump_window
    kwargs = dict(dir=args.dir, expttime=args.time, cong=args.cong, tc_child=(bw_link is not None), ping_interval=args.ping_interval,
            qjump_module_args=qjump_module_args, qjump_env_args=qjump_env_args)

    if args.topo == "simple":
        from topos import SimpleTopo
        topo = SimpleTopo(bw=bw_link)
        kwargs.update(dict(iperf_src='h1', iperf_dst='h2', ping_src='h1', ping_dst='h2'))
    elif args.topo == "dc":
        from topos import DCTopo
        topo = DCTopo(bw=bw_link)
        kwargs.update(dict(iperf_src='h7', iperf_dst='h10', ping_src='h8', ping_dst='h10'))

    if args.runall:
        qjump_all(topo, **kwargs)
    elif args.all_priorities:
        dirname = make_results_dir(kwargs.get("dir", DEFAULT_RESULTS_DIR))
        for priority in range(8):
            qjump_env_args["priority"] = priority
            kwargs["dir"] = os.path.join(dirname, "p%d" % priority)
            qjump_all(topo, **kwargs)
    else:
        qjump_once(topo, iperf=args.iperf, qjump=args.qjump, **kwargs)



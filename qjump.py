#!/usr/bin/python

"""CS244 Spring 2015 Assignment 3: Reproducing QJump paper results [NSDI'15]
Chuan-Zheng Lee and Ana Klimovic
CS 244 Spring 2015, Stanford University
"""

import sys
sys.path.insert(0, "../mininet_qjump")
import os
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.net import Mininet
from mininet.util import dumpNodeConnections
import mininet.log
print "mininet is in " + os.path.dirname(mininet.log.__file__)

import subprocess
from argparse import ArgumentParser

import time
import logging
logger = logging.getLogger(__name__)

from iperf import IperfManager
from ping import PingManager
from qjumpm import QJumpManager
from tcpdump import TcpdumpManager
from kernel_log import KernelLogManager
from plotter import Plotter

from functools import partial
from vlanhost import VLANHost

DEFAULT_QJUMP_MODULE_ARGS = dict(timeq=28800, bytesq=1550, p0rate=1, p1rate=5, p3rate=30, p4rate=300, p5rate=0, p6rate=0, p7rate=300)
DEFAULT_QJUMP_ENV_ARGS = dict(window=15500)
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

def print_stats(data, label):
    data = filter(lambda x: x is not None, data)
    print("{label}: min {min:.3f}, avg {avg:.3f}, max {max:.3f}".format(
            label=label, min=min(data), max=max(data),
            avg=sum(data)/len(data) if len(data) > 0 else 0.0
    ))

def is_8021q_installed():
    exitcode = subprocess.call("lsmod | grep 8021q", shell=True, stdout=subprocess.PIPE)
    return exitcode == 0

def install_8021q():
    if is_8021q_installed():
        logger.debug("802.1Q kernel module is already installed")
        return
    try:
        subprocess.check_call(["modprobe", "8021q"])
    except subprocess.CalledProcessError as e:
        logger.error("Error installing 802.1Q kernel module: " + str(e))
        return False
    logger.info("Installed the 802.1Q kernel module")
    return True

def qjump_all(*args, **kwargs):
    """Runs all three tests for Figure 3a. Replaces 'iperf' and 'qjump'
    arguments with its own."""

    dirname = make_results_dir(kwargs.get("dir", DEFAULT_RESULTS_DIR))
    kwargs["dir"] = dirname
    update_qjump_args(kwargs)
    log_arguments(*args, **kwargs)


    print("*** Test for ping alone ***\n")
    os.mkdir(os.path.join(dirname, "ping-alone"))
    kwargs.update(dict(iperf=False, qjump=False, dir=os.path.join(dirname, "ping-alone")))
    ping_alone = qjump(*args, **kwargs)

    print("\n*** Test for ping + iperf without QJump ***\n")
    os.mkdir(os.path.join(dirname, "ping-iperf-noqjump"))
    kwargs.update(dict(iperf=True, qjump=False, dir=os.path.join(dirname, "ping-iperf-noqjump")))
    ping_noQjump = qjump(*args, **kwargs)

    print("\n*** Test for ping + iperf with QJump ***\n")
    os.mkdir(os.path.join(dirname, "ping-iperf-qjump"))
    kwargs.update(dict(iperf=True, qjump=True, dir=os.path.join(dirname, "ping-iperf-qjump")))
    ping_Qjump = qjump(*args, **kwargs)
    if ping_Qjump.count(None) > 0:
        logger.warning("Ignoring %d dropped ping packets in QJump run", ping_Qjump.count(None))
    ping_Qjump = filter(lambda x: x is not None, ping_Qjump)
    plotter = Plotter()
    plotter.plotCDFs(ping_alone, ping_noQjump, ping_Qjump, dir=dirname, figname="pingCDFs")

    print("\nResults all saved to " + dirname)

def qjump_once(*args, **kwargs):
    dirname = make_results_dir(kwargs.get("dir", DEFAULT_RESULTS_DIR))
    kwargs["dir"] = dirname
    update_qjump_args(kwargs)
    log_arguments(*args, **kwargs)
    ping_times = qjump(*args, **kwargs)
    if ping_times:
        plotter = Plotter()
        plotter.plotCDF(ping_times, dir=dirname, figname="pingCDF")
        print("Results saved to " + dirname)

def qjump(topo, iperf_src, iperf_dst, ping_src, ping_dst, dir=".", expttime=10, \
        cong="cubic", iperf=True, ping=True, qjump=True, tc_child=False, qjump_module_args=dict(), \
        qjump_env_args=dict(), ping_interval=0.01, tcpdump=False, ping_priority=0,
        iperf_priority=4, iperf_protocol="udp", bw=None, kernel_log=False):

    try:
        subprocess.check_call(["sysctl", "-w", "net.ipv4.tcp_congestion_control=%s" % cong])
    except subprocess.CalledProcessError as e:
        logger.error("Error setting TCP congestion control algorithm: " + str(e))

    try:
        install_8021q()
        vlanhost = partial(VLANHost, vlan=2)
        net = Mininet(topo=topo, link=TCLink, host=vlanhost)
        net.start()

        dumpNodeConnections(net.hosts)
        net.pingAll()

        if tcpdump:
            tcpdumpm = TcpdumpManager(net, raw=(tcpdump=="raw"), dir=dir)
            tcpdumpm.start_all()

        if kernel_log:
            klogm = KernelLogManager(dir=dir)
            klogm.start()

        if qjump:
            qjumpm = QJumpManager(dir=dir)
            qjumpm.config_8021q(net)
            qjumpm.install_module(**qjump_module_args)
            qjumpm.install_qjump(net, tc_child)
            print "Setting ping priority to %d" % ping_priority
            hpenv = qjumpm.create_env(priority=ping_priority, **qjump_env_args)
            print "Setting iperf priority to %d" % iperf_priority
            lpenv = qjumpm.create_env(priority=iperf_priority, **qjump_env_args)
        else:
            hpenv = None
            lpenv = None

        if iperf:
            iperfm = IperfManager(net, iperf_dst, dir=dir)
            iperfm.start(iperf_src, time=expttime, env=lpenv, protocol=iperf_protocol, bw=bw)

        if ping:
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

        print 
        print("Done.")

        resultsfile = open(os.path.join(dir, "results.txt"), "w")

        if ping:
            ping_times = pingm.get_times()
            if len(ping_times) == 0:
                raise RuntimeError("There weren't any ping response times!")
            resultsfile.write("Ping results:\n")
            resultsfile.write(", ".join(map(str, ping_times)))
            resultsfile.write("\nPing results, sorted:\n")
            resultsfile.write(", ".join(map(str, sorted(ping_times))))
            print_stats(ping_times, "ping times")

        if iperf:
            iperf_bandwidths = iperfm.get_bandwidths()
            resultsfile.write("\n\nIperf bandwidths:\n")
            resultsfile.write(", ".join(map(str, iperf_bandwidths)))
            print_stats(iperf_bandwidths, "iperf bandwidths")

        resultsfile.close()

        if qjump:
            qjumpm.log_vlan(net)

        if kernel_log:
            klogm.process(dir)

    except Exception as e:
        print("Uncaught exception in qjump(): ")
        print(str(e))
        import traceback
        traceback.print_exc()

    finally:
        if 'resultsfile' in locals():
            resultsfile.close()
        if 'pingm' in locals():
            pingm.stop()
        if 'iperfm' in locals() and iperf:
            iperfm.stop()
        if 'tcpdumpm' in locals():
            tcpdumpm.stop()
        if 'klogm' in locals():
            klogm.stop()
        if 'net' in locals():
            try:
                net.stop()
            except Exception as e:
                print e
        time.sleep(3)
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
    parser.add_argument('--time', '-t', help="Duration (sec) to run the experiment", type=float, default=10.0)
    parser.add_argument('--cong', help="Congestion control algorithm to use", default="cubic") # Linux uses CUBIC-TCP by default
    parser.add_argument('--no-qjump', dest="qjump", help="Don't use QJump", action="store_false", default=True)
    parser.add_argument('--no-iperf', dest="iperf", help="Don't use Iperf", action="store_false", default=True)
    parser.add_argument('--no-ping', dest="ping", help="Don't use ping", action="store_false", default=True)
    parser.add_argument('--verbosity', '-v', help="Logging level", default="info")
    parser.add_argument('--topology', choices=("simple", "dc"), type=str, help="Topology to use", default="dc")
    parser.add_argument('--ping_src', type=str, help="host initiating ping", default="h8")
    parser.add_argument('--ping_dst', type=str, help="host receiving pings", default="h10")
    parser.add_argument('--iperf_src', type=str, help="iperf client host", default="h7")
    parser.add_argument('--iperf_dst', type=str, help="iperf server host", default="h10")
    parser.add_argument("--ping-interval", type=float, help="Ping interval", default=0.01)
    parser.add_argument("--bytesq", "-b", type=int, help="QJump's bytesq option", default=None)
    parser.add_argument("--timeq", type=int, help="Qjump's timeq option", default=None)
    parser.add_argument("--ping-priority", "-P", type=int, help="Priority level for ping", default=0)
    parser.add_argument("--iperf-priority", "-I", type=int, help="Priority level for iperf", default=6)
    parser.add_argument("--iperf-protocol", "--protocol", choices=("tcp", "udp"), type=str, help="Run iperf using TCP", default="udp")
    parser.add_argument("-f", "--factor", action="append", type=str, dest="qjump_factor", help="QJump throughput factor, e.g. -f5=300", default=[])
    parser.add_argument("--qjump-window", "--qjw", type=int, help="QJump environment's window for ping", default=None)
    parser.add_argument("--qjump-verbosity", type=int, help="QJump TC module verbosity", default=None)
    parser.add_argument("--all-priorities", action="store_true", help="Loop through all priorities", default=False)
    parser.add_argument("--tcpdump", action="store_const", const=True, dest="tcpdump", help="Run tcpdump", default=False)
    parser.add_argument("--tcpdump-raw", action="store_const", const="raw", dest="tcpdump", help="Run tcpdump to write raw packets", default=False)
    parser.add_argument("--kernel-log", action="store_true", help="Take note of kernel logs", default=False)
    parser.add_argument('--runall', '--all', help="Run ping alone, with iperf no qjump, with qjump", action="store_true", default=False)
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
    if args.qjump_verbosity is not None:
        qjump_module_args["verbose"] = args.qjump_verbosity
    for setting in args.qjump_factor:
        try:
            priority, factor = map(int, setting.split("="))
            assert priority in range(8)
        except (ValueError, AssertionError):
            raise ValueError("Invalid --factor setting: %s" % setting)
        qjump_module_args["p%drate" % priority] = factor
    if args.qjump_window is not None:
        qjump_env_args["window"] = args.qjump_window
    kwargs = dict(dir=args.dir, expttime=args.time, cong=args.cong, tc_child=(bw_link is not None), ping_interval=args.ping_interval,
            qjump_module_args=qjump_module_args, qjump_env_args=qjump_env_args, tcpdump=args.tcpdump,
            ping_priority=args.ping_priority, iperf_priority=args.iperf_priority, iperf_protocol=args.iperf_protocol,
            kernel_log=args.kernel_log)
    if args.iperf_protocol == "udp":
        kwargs["bw"] = bw_link * 1e6

    if args.topology == "simple":
        from topos import SimpleTopo
        topo = SimpleTopo(bw=bw_link)
        kwargs.update(dict(iperf_src='h1', iperf_dst='h2', ping_src='h1', ping_dst='h2'))
    elif args.topology == "dc":
        from topos import DCTopo
        topo = DCTopo(bw=bw_link)
        kwargs.update(dict(iperf_src=args.iperf_src, iperf_dst=args.iperf_dst, ping_src=args.ping_src, ping_dst=args.ping_dst))

    if args.runall:
        qjump_all(topo, **kwargs)
    elif args.all_priorities:
        dirname = make_results_dir(kwargs.get("dir", DEFAULT_RESULTS_DIR))
        for ping_priority in range(8):
            kwargs["ping_priority"] = ping_priority
            kwargs["dir"] = os.path.join(dirname, "p%d" % priority)
            qjump_all(topo, **kwargs)
    else:
        qjump_once(topo, iperf=args.iperf, ping=args.ping, qjump=args.qjump, **kwargs)



Reproducing results from the NSDI ’15 QJump paper
================================================
*Ana Klimovic and Chuan-Zheng Lee*<br/>
*CS 244 (Advanced Topics in Networking), Stanford University*

This repository contains code used in a CS 244 class project to reproduce the
results of Matthew P. Grosvenor *et al.* in "[Queues Don’t Matter When You Can
JUMP Them!](https://www.usenix.org/conference/nsdi15/technical-sessions/presentation/grosvenor)", presented at the 12th USENIX Symposium on
Networked Systems Design and Implementation (NSDI ’15).

Instructions
------------
1. Start an Amazon EC2 instance from the **CS244-Spr15-Mininet** (ami-cba48cfb)
   Amazon machine image. (It's listed under Community AMIs. You must be on the
   US West (Oregon) region to find this.) We used a c3.xlarge instance. Log into
   the instance.

   (For more details, see the [CS 244 page on EC2 setup](http://web.stanford.edu/class/cs244/ec2setup.html).)

2. Clone this repository, the [QJump traffic control (TC) module](https://github.com/czlee/qjump-tc) and the [QJump Application Utility](https://github.com/camsas/qjump-app-util).
   Also, clone our [modified version of Mininet](https://github.com/czlee/mininet), but clone it to the directory
   `mininet_qjump`.

        $ git clone https://github.com/anakli/cs244-qjump.git
        $ git clone https://github.com/czlee/qjump-tc.git
        $ git clone https://github.com/camsas/qjump-app-util.git
        $ git clone https://github.com/czlee/mininet.git mininet_qjump

   (The QJump TC module is slightly modified from the original: it uses the
   kernel clock rather than the processor's timestamp counter. A pull request is
   planned, eventually. Mininet was modified to create eight transmit queues
   on each interface, rather than just one. At the moment it's hard-coded, 
   but a more configurable pull request is also planned, eventually.)

3. Build the QJump TC module:

        $ cd qjump-tc
        $ make
        make -C /lib/modules/3.13.0-48-generic/build M=/home/ubuntu/qjump-tc modules
        make[1]: Entering directory `/usr/src/linux-headers-3.13.0-48-generic'
          CC [M]  /home/ubuntu/qjump-tc/sch_qjump.o
          Building modules, stage 2.
          MODPOST 1 modules
          CC      /home/ubuntu/qjump-tc/sch_qjump.mod.o
          LD [M]  /home/ubuntu/qjump-tc/sch_qjump.ko
        make[1]: Leaving directory `/usr/src/linux-headers-3.13.0-48-generic'

4. Build the QJump application utility:

        $ cd ../qjump-app-util
        $ make
        rm -f qjump-app-util.so*
        gcc -O3 -fPIC -shared -Werror -Wall -o qjump-app-util.so  qjump-app-util.c -ldl

5. Create symbolic links to the TC module and application utility from the
   `cs244-qjump` directory (or just copy it over if you prefer):

        $ cd ../cs244-qjump
        $ ln -s ../qjump-tc/sch_qjump.ko sch_qjump.ko
        $ ln -s ../qjump-app-util/qjump-app-util.so qjump-app-util.so

6. Install the VLAN configuration program.

        $ sudo apt-get update
        $ sudo apt-get install vlan

7. Run!

        $ sudo python qjump.py --all

   Results will be stored in a timestamped subdirectory of the `results/` directory. A symlink
   to the most recent results directory is placed at `last`.

Options
-------
The default setting is to run tests for 10 seconds with 10 Mbit/s links using the
[topology used by Grosvenor *et al.*](http://www.cl.cam.ac.uk/research/srg/netos/qjump/nsdi2015/network.html).
Some useful options:

- `--time=TIME`, `-t=TIME`: how long to run the experiment
- `--bw-link=BANDWIDTH`: the bandwidth of various links
- `--timeq=EPOCH`: a network epoch length, in microseconds
- `--bytesq=BYTESQ`: how many bytes a high-priority sender can send in a network epoch

To see all options:
    
    $ python qjump.py --help
    

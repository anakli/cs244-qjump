from mininet.topo import Topo

class SimpleTopo(Topo):
    "Simple topology for qjump experiment."

    def build(self, n=2, bw=10):
        switch = self.addSwitch('s0')
        for i in range(n):
            host = self.addHost('h%d' % (i+1))
            self.addLink(host, switch, bw=bw)



class DCTopo(Topo):
    "Datacenter topology for qjump experiment in Figure 3 of NSDI'15 paper."

    #               AGGR_SW
    #                 |  
    #       _____________________
    #      /          |          \
    #   ToR1        ToR2        ToR3
    #  /    \     /   | \     /  |   \
    # H1... H6    H7 H8 H9   H10 H11 H12
    def build(self, num_hosts=12, bw=10):
        
        # create switches
        aggr_switch = self.addSwitch('s0-aggr')
        ToR1_switch = self.addSwitch('s1-ToR')
        ToR2_switch = self.addSwitch('s2-ToR')
        ToR3_switch = self.addSwitch('s3-ToR')
        
        # link aggr switch to ToRs
        self.addLink(aggr_switch, ToR1_switch, bw=bw)
        self.addLink(aggr_switch, ToR2_switch, bw=bw)
        self.addLink(aggr_switch, ToR3_switch, bw=bw)
        for i in range(1,n+1):
            host = self.addHost('h%d' % i)
            if i in range(1,7):
                self.addLink(host, ToR1_switch, bw=bw)
            if i in range(7,10):
                self.addLink(host, ToR2_switch, bw=bw)
            if i in range(10,13):
                self.addLink(host, ToR3_switch, bw=bw)


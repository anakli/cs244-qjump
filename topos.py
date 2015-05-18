from mininet.topo import Topo

class SimpleTopo(Topo):
    "Simple topology for qjump experiment."

    def build(self, n=2, bw=10):
        switch = self.addSwitch('s0')
        for i in range(n):
            host = self.addHost('h%d' % (i+1))
            self.addLink(host, switch, bw=bw)


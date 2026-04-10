from mininet.topo import Topo

class Mytopo(Topo):
    def build(self):
        # Add core switch
        sw1 = self.addSwitch('s1')

        # Add distribution switches
        sw2 = self.addSwitch('s2')
        sw3 = self.addSwitch('s3')

        # Add access switches
        sw4 = self.addSwitch('s4')
        sw5 = self.addSwitch('s5')
        sw6 = self.addSwitch('s6')
        sw7 = self.addSwitch('s7')

        # Add hosts
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        h3 = self.addHost('h3')
        h4 = self.addHost('h4')
        h5 = self.addHost('h5')
        h6 = self.addHost('h6')
        h7 = self.addHost('h7')
        h8 = self.addHost('h8')

        # Connect Core to Distribution
        self.addLink(sw1, sw2)
        self.addLink(sw1, sw3)

        # Connect Distribution to Access
        self.addLink(sw2, sw4)
        self.addLink(sw2, sw5)
        self.addLink(sw3, sw6)
        self.addLink(sw3, sw7)

        # Connect Access to Hosts
        self.addLink(sw4, h1)
        self.addLink(sw4, h2)
        self.addLink(sw5, h3)
        self.addLink(sw5, h4)
        self.addLink(sw6, h5)
        self.addLink(sw6, h6)
        self.addLink(sw7, h7)
        self.addLink(sw7, h8)

topos = {'mytopo': (lambda: Mytopo())}

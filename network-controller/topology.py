from mininet.topo import Topo
from mininet.link import TCLink
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
import time

#usage: sudo mn --switch ovsk --controller remote --custom ./topology.py --topo testTopology
#alternative usage: sudo python3 topology.py

class TestTopology(Topo):

    def build(self):
        # Add the central switch
        s1 = self.addSwitch('s1')

        # Connect hosts
        for h in range(3, 10):
            host = self.addHost(f'h{h}', mac=f'00:00:00:00:00:0{h}')
            self.addLink(s1, host, cls=TCLink, bw=40, delay='15ms')

        # Add additional hosts and links (with greater bandwidth)
        h1 = self.addHost('h1', mac=f'00:00:00:00:00:01')
        h2 = self.addHost('h2', mac=f'00:00:00:00:00:02')
        h10 = self.addHost('h10', mac=f'00:00:00:00:00:10')
        h11 = self.addHost('h11', mac=f'00:00:00:00:00:11')
        web1 = self.addHost('web1', mac=f'aa:00:00:00:00:01')
        sus1 = self.addHost('sus1', mac=f'aa:aa:aa:aa:aa:aa')
        #sus2 = self.addHost('sus2', mac=f'ff:00:00:00:00:02')
        self.addLink(s1, h1, cls=TCLink, bw=80, delay='15ms')
        self.addLink(s1, h2, cls=TCLink, bw=80, delay='15ms')
        self.addLink(s1, h10, cls=TCLink, bw=40, delay='15ms')
        self.addLink(s1, h11, cls=TCLink, bw=40, delay='15ms')
        self.addLink(s1, web1, cls=TCLink, bw=100, delay='5ms')
        self.addLink(s1, sus1, cls=TCLink, bw=50, delay='20ms')
        #self.addLink(s1, sus2, cls=TCLink, bw=50, delay='20ms')


def simulateTraffic(net):
    "simulateTraffic is a command that will simulate background traffic on the network"
    
    h1, h2 = net.get('h1', 'h2')
    h3, h5 = net.get('h3', 'h5')

    h1.cmd('iperf -s &')  # Start the server on h1
    time.sleep(1)
    h2.cmd(f'iperf -c {h1.IP()} -t 0 &')  # Start the client on h2
    h5.cmd(f'iperf -c {h1.IP()} -t 0 &')  # Start the client with faster bandwidth on h5

# the topologies accessible to the mn tool's `--topo` flag
topos = {
    'testTopology': (lambda: TestTopology()),
}

def main():
    topo = TestTopology()
    net = Mininet(topo=topo, link=TCLink, controller=RemoteController, switch=OVSSwitch)
    net.start()
    net.interact()

    net.stop()

if __name__ == '__main__':
    main()

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

        # Connect h2, h3, h4 to the switch
        for h in range(4, 10):
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

class RealisticTopology(Topo):
    
    def build(self):
        # Add the central switch
        s1 = self.addSwitch('s1')

        # Connect hosts with varying bandwidth and delay
        hosts = [
            ('h1', '00:00:00:00:00:01', 80, '10ms'),
            ('h2', '00:00:00:00:00:02', 60, '15ms'),
            ('i1', '00:00:00:00:00:03', 20, '20ms'),
            ('h3', '00:00:00:00:00:04', 90, '12ms'),
            ('h4', '00:00:00:00:00:05', 100, '5ms'),
            ('i2', '00:00:00:00:00:06', 10, '25ms'),
            ('i3', '00:00:00:00:00:07', 30, '18ms'),
            ('h5', '00:00:00:00:00:08', 70, '13ms'),
            ('i4', '00:00:00:00:00:09', 25, '22ms'),
            ('i5', '00:00:00:00:00:0A', 15, '28ms'),
            ('h6', '00:00:00:00:00:0B', 65, '16ms'),
            ('h7', '00:00:00:00:00:0C', 35, '19ms'),
            ('h8', '00:00:00:00:00:0D', 95, '8ms'),
            ('h9', '00:00:00:00:00:0E', 12, '26ms'),
            ('h10', '00:00:00:00:00:0F', 75, '14ms'),
            ('h11', '00:00:00:00:00:10', 40, '17ms'),
            ('i6', '00:00:00:00:00:11', 28, '21ms'),
            ('i7', '00:00:00:00:00:12', 8, '29ms'),
            ('h12', '00:00:00:00:00:13', 85, '11ms'),
            ('i8', '00:00:00:00:00:14', 50, '16ms'),
            ('i9', '00:00:00:00:00:15', 18, '23ms'),
            ('web1', '00:00:00:00:00:16', 100, '5ms'),
            ('sus1', '00:00:00:00:00:17', 80, '5ms'),
            ('sus2', '00:00:00:00:00:18', 80, '5ms')
        ]

        for name, mac, bw, delay in hosts:
            host = self.addHost(name, mac=mac)
            self.addLink(s1, host, cls=TCLink, bw=bw, delay=delay)

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

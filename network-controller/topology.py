from mininet.topo import Topo
from mininet.link import TCLink
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
import time


#*******************************************************************************************************************************
# THIS IS THE EXAMPLE MININET TOPOLOGY FROM THE RYU TUTORIAL, IT WILL BE CHANGED IN THE FUTURE, BUT IS USED FOR TESTING CURRENTLY
#*******************************************************************************************************************************

#usage: sudo mn --switch ovsk --controller remote --custom ./topology.py --topo testTopology
#alternative usage: sudo python3 topology.py


class TutorialTopology(Topo):

    def build(self):
        # Add the central switch
        s1 = self.addSwitch('s1')

        # Connect h2, h3, h4 to the switch
        for h in range(2, 5):
            host = self.addHost(f'h{h}', mac=f'00:00:00:00:00:0{h}')
            self.addLink(s1, host, cls=TCLink, bw=40, delay='15ms')

        # Add additional hosts and links (with greater bandwidth)
        h1 = self.addHost('h1', mac=f'00:00:00:00:00:01')
        h5 = self.addHost('h5', mac=f'00:00:00:00:00:05')
        self.addLink(s1, h1, cls=TCLink, bw=80, delay='15ms')
        self.addLink(s1, h5, cls=TCLink, bw=80, delay='15ms')

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
    'testTopology': (lambda: TutorialTopology()), #will add in more complex topologies in the future
}

def main():
    topo = TutorialTopology()
    net = Mininet(topo=topo, link=TCLink, controller=RemoteController, switch=OVSSwitch)
    net.start()

    time.sleep(60)
    print("Rasa is now available...")
    simulateTraffic(net)

    net.interact()
    net.stop()

if __name__ == '__main__':
    main()

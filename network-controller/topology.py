from mininet.topo import Topo
from mininet.link import TCLink
from mininet.net import Mininet
from mininet.node import OVSController
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

        # connect n hosts to the switch
        hosts = []
        for h in range(1, 4):
            hosts.append(self.addHost(f"h{h}"))
            self.addLink(s1, hosts[h-1], cls=TCLink, bw=40, delay='15ms')

        hosts.append(self.addHost('h1'))
        hosts.append(self.addHost('h5'))
        self.addLink(s1, hosts[0], cls=TCLink, bw=80, delay='15ms')
        self.addLink(s1, hosts[4], cls=TCLink, bw=80, delay='15ms')

def simulateTraffic(net):
    "simulateTraffic is a command that will simulate background traffic on the network"
    
    h1, h2 = net.get('h1', 'h2')
    h3, h5 = net.get('h3', 'h5')

    h1.cmd('iperf -s &') #start the server on h1
    time.sleep(1)
    h2.cmd(f'iperf -c  + {h1} -t 0 &') #start the client on h2
    h5.cmd(f'iperf -c + {h1} & -t 0 &') #start the client with faster bandwidth on h4
    h3.cmd('ping 10.0.0.4 > /dev/null &') #start the ping on h3 to h5 (supressed output)

# the topologies accessible to the mn tool's `--topo` flag
topos = {
    'testTopology': (lambda: TutorialTopology()), #will add in more complex topologies in the future
}

def main():
    topo = TutorialTopology()
    net = Mininet(topo=topo, link=TCLink, controller=OVSController)
    net.start()

    time.sleep(60)
    print("Rasa is now available...")
    simulateTraffic(net)
    net.interact()
    net.stop()

if __name__ == '__main__':
    main()

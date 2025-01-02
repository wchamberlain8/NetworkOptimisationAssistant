from mininet.topo import Topo
from mininet.link import TCLink


#*******************************************************************************************************************************
# THIS IS THE EXAMPLE MININET TOPOLOGY FROM THE RYU TUTORIAL, IT WILL BE CHANGED IN THE FUTURE, BUT IS USED FOR TESTING CURRENTLY
#*******************************************************************************************************************************

#usage: sudo mn --switch ovsk --controller remote --custom ./topology.py --topo testTopology


class TutorialTopology(Topo):

    def build(self):

        # Add the central switch
        s1 = self.addSwitch('s1')

        # connect n hosts to the switch
        hosts = []
        for h in range(0, 5):
            hosts.append(self.addHost("h{}".format(h+1)))
            self.addLink(s1, hosts[h], cls=TCLink, bw=40, delay='15ms')


# the topologies accessible to the mn tool's `--topo` flag
topos = {
    'testTopology': (lambda: TutorialTopology()),
}

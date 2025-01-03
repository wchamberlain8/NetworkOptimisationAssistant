# -*- coding: utf-8 -*-

#************************************************************************************************************************
# THIS IS THE CONTROLLER TEMPLATE USED IN THE RYU TUTORIAL (up to level 2) TO BE EXPANDED UPON AND IMPROVED IN THE FUTURE
# I WILL CHANGE PARTS AS TO NOT COPY THE CONTROLLER.py PROVIDED IN THE TEMPLATE
#************************************************************************************************************************

"""
Ryu Tutorial Controller

This controller allows OpenFlow datapaths to act as Ethernet Hubs. Using the
tutorial you should convert this to a layer 2 learning switch.

See the README for more...
"""

from ryu.base.app_manager import RyuApp
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import *
from ryu.lib.dpid import dpid_to_str


class Controller(RyuApp):

    mac_to_port = {} #dictionary to hold the address -> port translations

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(Controller, self).__init__(*args, **kwargs)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def features_handler(self, ev):
        '''
        Handshake: Features Request Response Handler

        Installs a low level (0) flow table modification that pushes packets to
        the controller. This acts as a rule for flow-table misses.
        '''
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self.logger.info("Handshake taken place with {}".format(dpid_to_str(datapath.id)))
        self.__add_flow(datapath, 0, match, actions)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        '''
        Packet In Event Handler

        Takes packets provided by the OpenFlow packet in event structure and
        floods them to all ports. This is the core functionality of the Ethernet
        Hub.
        '''
        msg = ev.msg
        datapath = msg.datapath
        ofproto = msg.datapath.ofproto
        parser = msg.datapath.ofproto_parser
        dpid = msg.datapath.id #dpid = datapath id

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        if eth is None:
            print("Not ethernet\n")
            return
        
        src_mac = eth.src
        dst_mac = eth.dst
        in_port = msg.match['in_port']
        a = False

        if dst_mac.startswith('33:33'):
            self.logger.info(f"Multicast traffic detected. src={src_mac}, dst={dst_mac}")
            a = True
        
        if dst_mac == "ff:ff:ff:ff:ff:ff":
            self.logger.info(f"Broadcast packet detected. src={src_mac}, dst={dst_mac}")
            a = True
            

        self.mac_to_port.setdefault(dpid, {})

        self.mac_to_port[dpid][src_mac] = in_port #store that the device with src_mac reachable through in_port on dpid 
        self.logger.info(f"Learned MAC {src_mac} on port {in_port} for switch {dpid}!")

        if dst_mac in self.mac_to_port[dpid]: 
            #if we know the route:
            out_port = self.mac_to_port[dpid][dst_mac]
            self.logger.info(f"MAC {dst_mac} known, forwarding to port {out_port}")
        else:
            #if we haven't seen the route before, flood until we do:
            out_port = ofproto.OFPP_FLOOD
            if a == False:
                self.logger.info(f"MAC {dst_mac} unknown, flooding...")

        actions = [parser.OFPActionOutput(out_port)]

        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data 
        else: None
            
        out = parser.OFPPacketOut(atapath=datapath, buffer_id=msg.buffer_id, in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)

        #make a flow rule in the flow table
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst_mac)
            self.__add_flow(datapath, 1, match, actions)
            return






    def __add_flow(self, datapath, priority, match, actions):
        '''
        Install Flow Table Modification

        Takes a set of OpenFlow Actions and a OpenFlow Packet Match and creates
        the corresponding Flow-Mod. This is then installed to a given datapath
        at a given priority.
        '''
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority, match=match, instructions=inst)
        self.logger.info("Flow-Mod written to {}".format(dpid_to_str(datapath.id)))
        datapath.send_msg(mod)

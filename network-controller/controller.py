# -*- coding: utf-8 -*-
import subprocess
import time
from time import sleep
from ryu.base.app_manager import RyuApp
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto.ofproto_v1_2 import OFPG_ANY
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import vlan, ethernet, packet
from ryu.lib.dpid import dpid_to_str
import threading
import socket
import requests


class Controller(RyuApp):

    mac_to_port = {} #dictionary to hold the address -> port translations
    whitelist = []
    guest_list = []
    VLAN_GUEST_TAG = 10
    VLAN_TRUSTED_TAG = 20

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(Controller, self).__init__(*args, **kwargs)
        self.stats_data = None
        self.stats_data_event = threading.Event()
        self.live_request = None
        self.lock = threading.Lock()
        self.ports = {}
        self.start_time = time.time()

        subprocess.run([
            "sudo", "ovs-vsctl", "--all", "destroy", "QoS"
        ])
        
        subprocess.run([
            "sudo", "ovs-vsctl", "--all", "destroy", "Queue"
        ])

    def start_socket_server(self, datapath):
        #Start a socket server to receive data from the API
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('127.0.0.2', 9090))
        s.listen(5)

        while True:
            connection, address = s.accept()
            with connection:
                print(f"Connected to {address}")
                data = connection.recv(1024).decode("utf-8")
                if data:
                    try:
                        if "=" in data:
                            command, mac = data.split("=")
                            if command == "throttle_device":
                                self.logger.info(f"Attempting to throttle device {mac}")
                                result = self.set_device_queue(datapath, mac, 1)
                                message = "success" if result else "error"
                                connection.sendall(message.encode("utf-8"))
                            elif command == "prioritise_device":
                                self.logger.info(f"Attempting to prioritise device {mac}")
                                result = self.set_device_queue(datapath, mac, 2)
                                message = "success" if result else "error"
                                connection.sendall(message.encode("utf-8"))
                            elif command == "unthrottle_device":
                                self.logger.info(f"Attempting to unthrottle device {mac}")
                                result = self.delete_device_queue(datapath, mac)
                                message = "success" if result else "error"
                                connection.sendall(message.encode("utf-8"))
                            elif command == "deprioritise_device":
                                self.logger.info(f"Attempting to deprioritise device {mac}")
                                result = self.delete_device_queue(datapath, mac)
                                message = "success" if result else "error"
                                connection.sendall(message.encode("utf-8"))
                            elif command == "whitelist_device":
                                self.logger.info(f"Attempting to whitelist device {mac}")
                                result = self.whitelist_device(datapath, mac)
                                message = "success" if result else "error"
                                connection.sendall(message.encode("utf-8"))
                            else:
                                print("Invalid command received from socket.")
                        elif data == "get_live_stats":
                            self.request_live_stats(datapath)
                        elif data == "get_guest_list":
                            self.get_guest_list()
                        else:
                            print("Invalid command received from socket.")
                    except Exception as e:
                        print(f"Error processing command: {e}")


    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def features_handler(self, ev):

        datapath = ev.msg.datapath
        self.logger.info(f"Connected to switch {datapath.id}")
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]

        self.request_ports(datapath)

        self.logger.info("Handshake taken place with {}".format(dpid_to_str(datapath.id)))
        self.__add_flow(datapath, 0, match, actions)
        self.request_stats_periodically(datapath)
        threading.Thread(target=self.start_socket_server, args=(datapath,), daemon=True).start()

        #drop packets on the guest/unknown vlan
        match = parser.OFPMatch(eth_type=0x8100, vlan_vid=(ofproto_v1_3.OFPVID_PRESENT | self.VLAN_GUEST_TAG))
        actions = [] 
        self.__add_flow(datapath, 20, match, actions)
        

    def request_ports(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        request = parser.OFPPortDescStatsRequest(datapath, 0)
        datapath.send_msg(request)


    @set_ev_cls(ofp_event.EventOFPPortDescStatsReply, MAIN_DISPATCHER)
    def port_description_handler(self, ev):

        datapath = ev.msg.datapath
        for port in ev.msg.body:
            if port.port_no == 4294967294: #ignore the special port
                continue
            self.create_qos_queue(datapath.id, port.port_no)
            self.logger.info(datapath.id)


    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):

        msg = ev.msg
        datapath = msg.datapath
        ofproto = msg.datapath.ofproto
        parser = msg.datapath.ofproto_parser
        dpid = msg.datapath.id #dpid = datapath id
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        vlan_pkt = pkt.get_protocol(vlan.vlan)
        
        if eth is None:
            return
    
        src_mac = eth.src
        dst_mac = eth.dst
        in_port = msg.match['in_port']
        
        #self.logger.info(f"Packet in event received: src_mac={src_mac}")
            
        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][src_mac] = in_port #store that the device with src_mac reachable through in_port on dpid 
        
        #self.logger.info(f"Learned MAC {src_mac} on port {in_port} for switch {dpid}!")

        current_time = time.time()
        elapsed_time = current_time - self.start_time

        out_port = self.mac_to_port[dpid].get(dst_mac, ofproto.OFPP_FLOOD)
        
        actions = []

        actions.append(parser.OFPActionSetQueue(0))
        actions.append(parser.OFPActionOutput(out_port))
            
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id, in_port=in_port, actions=actions, data=msg.data if msg.buffer_id == ofproto.OFP_NO_BUFFER else None)
        datapath.send_msg(out)

        if out_port != ofproto.OFPP_FLOOD:

            if elapsed_time <= 60:
                vlan_id = self.VLAN_TRUSTED_TAG
                if src_mac not in self.whitelist:
                    self.whitelist.append(src_mac)
            else:
                vlan_id = self.VLAN_GUEST_TAG
                if src_mac not in self.guest_list and src_mac not in self.whitelist:
                    self.guest_list.append(src_mac)

            actions.append(parser.OFPActionPushVlan(0x8100))
            actions.append(parser.OFPActionSetField(vlan_vid = (vlan_id | ofproto.OFPVID_PRESENT)))

            match = parser.OFPMatch(eth_dst=dst_mac)
            self.logger.info("Attempting to add a new flow rule...")
            self.__add_flow(datapath, 10, match, actions)
            return
        

    def __add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority, match=match, instructions=inst)
        datapath.send_msg(mod)
        self.logger.info(f"Flow added for switch {datapath.id}")


    #Periodically request + post flow stats to the API to keep a record of bandwidth usage

    def request_stats_periodically(self, datapath):

        with self.lock:
            self.live_request = False

        parser = datapath.ofproto_parser
        request = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(request)
        
        threading.Timer(20, self.request_stats_periodically, args=[datapath]).start()



    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def flow_stats_response_handler(self, ev):
        #Get and calculate the flow stats from the switch (from the event)
        body = ev.msg.body
        stats = []

        for stat in body:
            flow_id = stat.match.get("eth_src", "N/A") + stat.match.get("eth_dst", "N/A") #TODO: improve this in future, make a hash function
            stats.append({
                "flow_id": flow_id,
                "src_mac": stat.match.get("eth_src", "N/A"),
                "dst_mac": stat.match.get("eth_dst", "N/A"),
                "byte_count": stat.byte_count,
                "packet_count": stat.packet_count,
                "duration_sec": stat.duration_sec
            })

        with self.lock:
            if self.live_request:
                self.logger.info("Inside lock, getting live stats now!")
                self.stats_data = stats
                self.stats_data_event.set()
            else:
                payload = {"stats": stats}
                self.logger.info(f"Payload being sent: {payload}")

                try:
                    response = requests.post("http://127.0.0.1:8000/update_historical_stats", json=payload)
                except requests.exceptions.RequestException as e:
                    print(f"Error sending historical data: {e}")
    
    
    def request_live_stats(self, datapath):
        #Upon communication from the API, get the live flow stats (two sets, a second apart) and send them to the API

        self.logger.info("Starting the process to get and send live stats...")

        with self.lock:
            self.live_request = True

        parser = datapath.ofproto_parser
        request = parser.OFPFlowStatsRequest(datapath)
        
        stats1 = []
        stats2 = []
        
        datapath.send_msg(request) #send a request for the first set of stats
        
        if not self.stats_data_event.wait(timeout=3):
            self.logger.info("Timeout Error: Could not retrieve first snapshot of stats")
            return
        
        with self.lock:
            stats1 = self.stats_data
        
        self.stats_data_event.clear()

        sleep(1) #wait a second

        datapath.send_msg(request) #send another request for the second set of stats

        if not self.stats_data_event.wait(timeout=3):
            self.logger.info("Timeout Error: Could not retrieve second snapshot of stats")
        
        with self.lock:
            stats2 = self.stats_data

        self.stats_data_event.clear()

        self.logger.info("Live stats received, sending to API...")

        payload = {
            "snapshot1": stats1,
            "snapshot2": stats2
        }

        self.logger.info(f"Payload being sent: {payload}")

        try:
            response = requests.post("http://127.0.0.1:8000/send_live_stats", json=payload)
        except requests.exceptions.RequestException as e:
            print(f"Error sending data: {e}")

        with self.lock:
            self.live_request = False



    def create_qos_queue(self, dpid, port_no):

        port_name = f"s{dpid}-eth{port_no}"
        self.logger.info(f"Port Name: {port_name}")

        subprocess.run([
            "sudo", "ovs-vsctl", "set", "Port", port_name, f"qos=@qos{port_name}", "--", f"--id=@qos{port_name}", "create", "QoS", "type=linux-htb", "other-config:max-rate=100000000",
            "queues:0=@default", "queues:1=@throttled", "queues:2=@priority", 
            "--", "--id=@default", "create", "Queue", "other-config:max-rate=100000000",  # Default (Unrestricted)
            "--", "--id=@throttled", "create", "Queue", "other-config:max-rate=10000000",  # Throttled (10Mbps)
            "--", "--id=@priority", "create", "Queue", "other-config:max-rate=50000000", "other-config:priority=10"  # Priority (50Mbps, highest priority)
        ], stdout=subprocess.DEVNULL)


    # Used for throttling or prioritising a device
    def set_device_queue(self, datapath, dst_mac, queue_id):
        # Set a new flow rule to assign a queue (throttling or priority) to a destination MAC address
        # This tells the switch "If anything is destined for this MAC address, send it via the specified queue"

        dpid = datapath.id

        port_no = self.mac_to_port[dpid].get(dst_mac)
        if port_no is None:
            self.logger.error(f"Port for MAC {dst_mac} not found in mac_to_port table.")
            return False

        self.logger.info(f"Setting queue {queue_id} for {dst_mac} on port {port_no} of switch {dpid}")
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto

        try:
            match = parser.OFPMatch(eth_dst=dst_mac)

            actions = [parser.OFPActionSetQueue(queue_id), parser.OFPActionOutput(port_no)]
            inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]

            mod = parser.OFPFlowMod(datapath=datapath, match=match, instructions=inst, priority=10, command=ofproto.OFPFC_ADD)
            datapath.send_msg(mod)

            self.logger.info(f"Queue {queue_id} successfully set for {dst_mac}")
            
            return True

        except Exception as e:
            print(f"Error setting queue for device: {e}")
            return False  

    
    #Used for removing throttling or prioritisation from a device
    def delete_device_queue(self, datapath, dst_mac, queue_id):
        # Delete a flow rule that previously assigned a queue to a destination MAC address
        # This tells the switch to stop sending packets via that the specified queue, and instead use a default setting

        dpid = datapath.id

        port_no = self.mac_to_port[dpid].get(dst_mac)
        if port_no is None:
            self.logger.error(f"Port for MAC {dst_mac} not found in mac_to_port table.")
            return False

        self.logger.info(f"Deleting queue for {dst_mac} on port {port_no} of switch {dpid}")
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto

        try:
            match = parser.OFPMatch(eth_dst=dst_mac)
            mod = parser.OFPFlowMod(datapath=datapath, match=match, priority=10, out_port=port_no, out_group=OFPG_ANY, command=ofproto.OFPFC_DELETE)
            datapath.send_msg(mod)

            self.logger.info(f"Queue successfully deleted for {dst_mac}")
            return True

        except Exception as e:
            print(f"Error deleting queue for device: {e}")
            return False
        
    
    def get_guest_list(self):
        try:
            payload = {"guest_list": self.guest_list}
            requests.post("http://127.0.0.1:8000/send_guest_list", json=payload)
        except requests.exceptions.RequestException as e:
            print(f"Error sending guest list: {e}")

    
    def get_whitelist(self):
        return self.whitelist
    
    def whitelist_device(self, datapath, mac):
        try:
            if mac not in self.guest_list:
                self.logger.info(f"Device {mac} not in guest list, cannot whitelist")
                return False
            
            #remove from guest list, add to whitelist
            self.guest_list.remove(mac)
            self.whitelist.append(mac)

            ofproto = datapath.ofproto
            parser = datapath.ofproto_parser
    
            #delete existing flow rule for this device
            match = parser.OFPMatch(eth_src=mac, vlan_vid=(self.VLAN_GUEST_TAG | ofproto_v1_3.OFPVID_PRESENT))
            mod = parser.OFPFlowMod(datapath=datapath, match=match, priority=20, command=ofproto.OFPFC_DELETE)
            datapath.send_msg(mod)

            actions = [parser.OFPActionPushVlan(0x8100), parser.OFPActionSetField(vlan_vid = (self.VLAN_TRUSTED_TAG | ofproto_v1_3.OFPVID_PRESENT)),
                       parser.OFPActionOutput(ofproto.OFPP_NORMAL)] #should this be OFPP_NORMAL or the port number?
            
            match = parser.OFPMatch(eth_src=mac)
            self.__add_flow(datapath, 1, match, actions)

            self.logger.info(f"Device {mac} whitelisted successfully")
            return True

        except Exception as e:
            print(f"Error whitelisting device: {e}")
            return False
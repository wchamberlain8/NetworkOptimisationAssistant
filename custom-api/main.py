from fastapi import FastAPI
from pydantic import BaseModel
import socket
import asyncio
import re

#initialise the FastAPI
app = FastAPI()

bandwidth_stats = {}
historical_stats = {}
top_consumer_cache = asyncio.Queue()

#Hardcoded dictionary to hold the MAC address to hostname translations
mac_to_hostname = {
    "00:00:00:00:00:01": "Laptop",
    "00:00:00:00:00:02": "Smart TV",
    "00:00:00:00:00:03": "Ring Doorbell",
    "00:00:00:00:00:04": "XBOX",
    "00:00:00:00:00:05": "Gaming PC"
}

hostname_to_mac = {}
for mac, hostname in mac_to_hostname.items():
    normalised_hostname = re.sub(r'[^a-zA-Z0-9]', '', hostname.lower()) #normalise the hostname to allow for different spellings etc.
    hostname_to_mac[normalised_hostname] = mac

#data model if we want to pass some data to the API
class InputModel(BaseModel):
    input_value: str

#an api endpoint to test it works
@app.post("/test")
async def test(input: InputModel):
    if input.input_value == "test":
        return {"message": "Hello World! - You have connected to the API!"}
    return {"message": "Invalid input provided."}


#--------------------------------------------------------------------------------------------------------------------
#/mac_translation - Used for translating a MAC address to a hostname, or vice versa
#--------------------------------------------------------------------------------------------------------------------
@app.post("/mac_translation")
async def mac_translation(input: InputModel):

    #if input == a mac address, find the relevant hostname translation, if not, return "Unknown"
    str = input.input_value
    
    if mac_address_check(str):
        hostname = mac_to_hostname.get(str)
        if hostname: #if there is a correlated hostname to that mac
            return {"mac": str, "hostname": hostname}
        else:
            return {"mac": str, "hostname": "Unknown Device"}
        
    #else, if input == a hostname, try and find the relevant mac address translation, if not, return None
    else:
        normalised_input = re.sub(r'[^a-zA-Z0-9]', '', str.lower())
        mac_address = hostname_to_mac.get(normalised_input)
        if mac_address:
            return {"mac": mac_address, "hostname": str}
        else:
            return {"mac": None, "hostname": str}
     

#--------------------------------------------------------------------------------------------------------------------
#/update_historical_stats - Used by the network controller to keep a consistent record of past bandwidth usage
#--------------------------------------------------------------------------------------------------------------------
@app.post("/update_historical_stats")
async def update_historical_stats(data: dict):
    global historical_stats

    stats = data.get("stats", [])
    if stats:
        historical_stats = stats

#--------------------------------------------------------------------------------------------------------------------
#/get_historic_stats - Used to retrieve the historic bandwidth usage data as well as network uptime
#--------------------------------------------------------------------------------------------------------------------
@app.get("/get_historic_stats")
async def get_historic_stats():
    global historical_stats

    if not historical_stats:
        return {"message": "No bandwidth data has been recorded"}
    
    aggregate_count = {}
    max_duration = 0

    for stat in historical_stats:
        src_mac = stat["src_mac"]
        dst_mac = stat["dst_mac"]
        byte_count = stat["byte_count"]
        #duration = stat["duration_sec"]

        if src_mac ==  "N/A" and dst_mac == "N/A": #the base flow entry
            max_duration = stat["duration_sec"]
            continue

        aggregate_count[src_mac] = aggregate_count.get(src_mac, 0) + byte_count
        #max_duration = max(max_duration, duration) #figure out how long the network has been live (first flow added)

    minutes = max_duration // 60
    seconds = max_duration % 60
    network_uptime = f"{minutes} min {seconds} secs"

    stats_list = []

    for src_mac, byte_count in aggregate_count.items():
        stats = {
            "src_mac": src_mac,
            "overall_byte_count": format_bytes(byte_count)
            #"duration_sec": TODO: MAKE IT SO EACH DEVICE ALSO TRACKS HOW LONG THAT FLOW HAS BEEN LIVE INCASE IT GETS REMOVED etc.
        }
        stats_list.append(stats)

    
    payload = {
        "uptime": network_uptime,
        "stats": stats_list
    }

    return payload

#--------------------------------------------------------------------------------------------------------------------
#/get_live_stats - Used to request live stats from the network controller and returns them upon completion 
#--------------------------------------------------------------------------------------------------------------------
@app.get("/get_live_stats")
async def get_live_stats():
    global top_consumer_cache

    #connect to the socket and request the live stats from the controller
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.2", 9090))
        s.sendall(b"get_live_stats")
    except Exception as e:
        print(f"Error connecting to the controller: {e}")

    #using asyncio to wait for the top consumer to be calculated, then returning a result, if any
    try:
        combined_data = await asyncio.wait_for(top_consumer_cache.get(), timeout=5)
        return {"data": combined_data}
    except asyncio.TimeoutError:
        return {"message": "Timeout: The API did not receive stats from the controller in time"}

#--------------------------------------------------------------------------------------------------------------------
#/send_live_stats - Used for retrieving and structuring live flow stats to find the top live consumer and set a flag
#--------------------------------------------------------------------------------------------------------------------
@app.post("/send_live_stats")
async def send_live_stats(data: dict):
    global top_consumer_cache
    live_flows = []
    aggregate_mac_bandwidth = {}

    snapshot1 = data.get("snapshot1", [])
    snapshot2 = data.get("snapshot2", [])

    for flow1 in snapshot1:
        for flow2 in snapshot2:
            if flow1.get("flow_id") == flow2.get("flow_id"): #make sure we are comparing the same flow
                if flow1.get("byte_count") != flow2.get("byte_count"): #make sure the flow has changed (is live)
                    byteDifference = flow2.get("byte_count", 0) - flow1.get("byte_count", 0)
                    packetDifference = flow2.get("packet_count", 0) - flow1.get("packet_count", 0)

                    bandwidth = round((byteDifference * 8) / 1000000, 2)

                    live_flows.append({
                        "flow_id": flow2.get("flow_id"),
                        "src_mac": flow2.get("src_mac"),
                        "dst_mac": flow2.get("dst_mac"),
                        "byte_count": byteDifference,
                        "packet_count": packetDifference,
                        "bandwidth": bandwidth
                    })
                    break

    if live_flows:
        print(f"Here are the live flows: {live_flows}\n")

        for flow in live_flows:
            dst_mac = flow.get("dst_mac")

            if dst_mac not in aggregate_mac_bandwidth:
                aggregate_mac_bandwidth[dst_mac] = {"dst_mac": dst_mac, "total_bandwidth": 0}
            aggregate_mac_bandwidth[dst_mac]["total_bandwidth"] += flow.get("bandwidth")     #if needed, i can easily update this to send the src_mac to say where stuff is coming from etc.

        try:
            top_consumer = max(aggregate_mac_bandwidth, key=lambda x: aggregate_mac_bandwidth[x]["total_bandwidth"], default=None) #find the highest bandwidth consumer
            top_consumer = aggregate_mac_bandwidth[top_consumer]
            print(f"Top Consumer = {top_consumer}\n")

            filtered_live_flows = [flow for flow in live_flows if flow.get("dst_mac") != top_consumer.get("dst_mac")]

            combined_data = {
                "top_consumer": top_consumer,
                "live_flows": filtered_live_flows
            }

            await top_consumer_cache.put(combined_data) #put the top consumer into the cache
        except Exception as e:
            print(f"Error calculating top consumer: {e}")
    else:
        print("***** There is currently nothing using bandwidth *****\n")


#--------------------------------------------------------------------------------------------------------------------
#/throttle_device - Used for throttling a specific device on the network
#--------------------------------------------------------------------------------------------------------------------
@app.post("/throttle_device")
async def throttle_device(json: dict):

    device = json.get("device")

    if device:

        #figure out whether the user's input was a mac address or a hostname
        if mac_address_check(device):
            mac = device
            print("MAC ADDRESS DETECTED: ", mac)
        else:
            print("HOSTNAME DETECTED: ", device)
            normalised_hostname = re.sub(r'[^a-zA-Z0-9]', '', device.lower())
            mac = hostname_to_mac.get(normalised_hostname)
            print("CONVERTED TO MAC: ", mac)
            if not mac:
                return {"message": "Unknown device"}
        
        #connect to the socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("127.0.0.2", 9090))
            message = f"throttle_device={mac}"
            s.sendall(message.encode('utf-8'))
            s.close()

            return {"message": "success"}
        except Exception as e:
            print(f"Error connecting to the controller: {e}")
    
    else:
        return {"message": "No device could be parsed from the JSON payload"}
    
#--------------------------------------------------------------------------------------------------------------------
#/prioritise_device - Used for prioritising a specific device on the network
#--------------------------------------------------------------------------------------------------------------------
@app.post("/prioritise_device")
async def prioritise_device(json: dict):

    device = json.get("device")

    if device:

        #figure out whether the user's input was a mac address or a hostname
        if mac_address_check(device):
            mac = device
            print("MAC ADDRESS DETECTED: ", mac)
        else:
            print("HOSTNAME DETECTED: ", device)
            normalised_hostname = re.sub(r'[^a-zA-Z0-9]', '', device.lower())
            mac = hostname_to_mac.get(normalised_hostname)
            print("CONVERTED TO MAC: ", mac)
            if not mac:
                return {"message": "Unknown device"}
        
        #connect to the socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("127.0.0.2", 9090))
            message = f"prioritise_device={mac}"
            s.sendall(message.encode('utf-8'))
            s.close()

            return {"message": "success"}
        except Exception as e:
            print(f"Error connecting to the controller: {e}")

    else:
        return {"message": "No device could be parsed from the JSON payload"}
    
#--------------------------------------------------------------------------------------------------------------------
#/unthrottle_device - Used for unthrottling a specific device on the network
#--------------------------------------------------------------------------------------------------------------------
@app.post("/unthrottle_device")
async def unthrottle_device(json: dict):

    device = json.get("device")

    if device:

        #figure out whether the user's input was a mac address or a hostname
        if mac_address_check(device):
            mac = device
            print("MAC ADDRESS DETECTED: ", mac)
        else:
            print("HOSTNAME DETECTED: ", device)
            normalised_hostname = re.sub(r'[^a-zA-Z0-9]', '', device.lower())
            mac = hostname_to_mac.get(normalised_hostname)
            print("CONVERTED TO MAC: ", mac)
            if not mac:
                return {"message": "Unknown device"}
        
        #connect to the socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("127.0.0.2", 9090))
            message = f"unthrottle_device={mac}"
            s.sendall(message.encode('utf-8'))
            s.close()

            return {"message": "success"}

        except Exception as e:
            print(f"Error connecting to the controller: {e}")

    else:
        return {"message": "No device could be parsed from the JSON payload"}
    
#--------------------------------------------------------------------------------------------------------------------
#/deprioritise_device - Used for deprioritisng a specific device on the network
#--------------------------------------------------------------------------------------------------------------------
@app.post("/deprioritise_device")
async def deprioritise_device(json: dict):

    device = json.get("device")

    if device:

        #figure out whether the user's input was a mac address or a hostname
        if mac_address_check(device):
            mac = device
            print("MAC ADDRESS DETECTED: ", mac)
        else:
            print("HOSTNAME DETECTED: ", device)
            normalised_hostname = re.sub(r'[^a-zA-Z0-9]', '', device.lower())
            mac = hostname_to_mac.get(normalised_hostname)
            print("CONVERTED TO MAC: ", mac)
            if not mac:
                return {"message": "Unknown device"}
        
        #connect to the socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("127.0.0.2", 9090))
            message = f"deprioritise_device={mac}"
            s.sendall(message.encode('utf-8'))
            s.close()

            return {"message": "success"}

        except Exception as e:
            print(f"Error connecting to the controller: {e}")

    else:
        return {"message": "No device could be parsed from the JSON payload"}


#*****************************************
#           Helper Functions
#*****************************************

def mac_address_check(mac):
    if ":" in mac:
        parts = mac.split(":")
    else: 
        return False
    
    if len(parts) != 6:
           return False
        
    for part in parts:
        if len(part) != 2:
            return False
        
    return True

def format_bytes(bytes):
    if bytes >= 1_000_000_000:
        return f"{round(bytes / 1_000_000_000, 2)} GB"
    elif bytes >= 1_000_000:
        return f"{round(bytes / 1_000_000, 2)} MB"
    elif bytes >= 1_000:
        return f"{round(bytes / 1_000, 2)} KB"
    else:
        return f"{bytes} B"
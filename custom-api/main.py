from fastapi import FastAPI
from pydantic import BaseModel
import socket
import asyncio

#initialise the FastAPI
app = FastAPI()

bandwidth_stats = {}
historical_stats = {}
top_consumer_cache = asyncio.Queue()

#data model if we want to pass some data to the API
class InputModel(BaseModel):
    input_value: str

#an api endpoint to test it works
@app.post("/test")
async def test(input: InputModel):
    if input.input_value == "test":
        return {"message": "Hello World! - You have connected to the API!"}
    return {"message": "Invalid input provided."}



#api endpoint for bandwidth stats
@app.post("/update_historical_stats")
async def update_historical_stats(data: dict):
    global historical_stats

    stats = data.get("stats", [])
    if stats:
        historical_stats = stats


#api endpoint for getting the past x minutes of bandwidth information
@app.get("/get_historic_stats")
async def get_historic_stats():
    global historical_stats

    if not historical_stats:
        return {"message": "No bandwidth data has been recorded"}
    
    aggregate_count = {}
    max_duration = 0

    for stat in historical_stats:
        src_mac = stat["src_mac"]
        byte_count = stat["byte_count"]
        duration = stat["duration_sec"]

        aggregate_count[src_mac] = aggregate_count.get(src_mac, 0) + byte_count
        max_duration = max(max_duration, duration) #figure out how long the network has been live (first flow added)

    network_uptime = round(max_duration/60, 2)

    stats_list = []

    for src_mac, byte_count in aggregate_count.items():
        stats = {
            "src_mac": src_mac,
            "overall_byte_count": byte_count
        }
        stats_list.append(stats)

    
    payload = {
        "uptime": network_uptime,
        "stats": stats_list
    }

    return payload



#api endpoint for Rasa to request live stats
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
        top_consumer = await asyncio.wait_for(top_consumer_cache.get(), timeout=5)
        return {"top_consumer": top_consumer}
    except asyncio.TimeoutError:
        return {"message": "Timeout: The API did not receive stats from the controller in time"}



#api endpoint for retrieving and deciphering live flow stats to find top LIVE consumer
@app.post("/send_live_stats")
async def send_live_stats(data: dict):
    global top_consumer_cache
    live_flows = []

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
        try:
            top_consumer = max(live_flows, key=lambda x: x["bandwidth"], default=None) #find the highest bandwidth consumer
            print(f"Top Consumer = {top_consumer}\n")
            await top_consumer_cache.put(top_consumer) #put the top consumer into the cache
        except Exception as e:
            print(f"Error calculating top consumer: {e}")
    else:
        print("***** There is currently nothing using bandwidth *****\n")

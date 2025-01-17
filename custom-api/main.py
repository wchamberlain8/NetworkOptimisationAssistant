from fastapi import FastAPI
from pydantic import BaseModel
import socket
import time
import asyncio

#initialise the FastAPI
app = FastAPI()

bandwidth_stats = {}
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
@app.post("/update_stats")
async def update_stats(data: dict):
    global bandwidth_stats
    bandwidth_stats = data



#api endpoint for getting the bandwidth information
@app.get("/retrieve_bandwidth")
async def retrieve_bandwidth():
    global bandwidth_stats
    top_consumer = None
    
    if not bandwidth_stats or "stats" not in bandwidth_stats or not bandwidth_stats["stats"]:
        print("ERROR: NO DATA FOUND")
    else:
        try:
            top_consumer = max(bandwidth_stats["stats"], key=lambda x: round((x.get("byte_count", 0) * 8) / x.get("duration_sec", 1) / 1000000), default=None) #find the highest bandwidth consumer
        except Exception as e:
            print(f"Error calculating top consumer: {e}")
    
    return {"top_consumer": top_consumer}



#api endpoint for Rasa to request live stats
@app.get("/get_live_stats")
async def get_live_stats():
    #connect to the socket and request the live stats from the controller

    global top_consumer_cache

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.2", 9090))
        s.sendall(b"get_live_stats")
    except Exception as e:
        print(f"Error connecting to the controller: {e}")

    try:
        top_consumer = await asyncio.wait_for(top_consumer_cache.get(), timeout=10)
        return {"top_consumer": top_consumer}
    except asyncio.TimeoutError:
        return {"message": "Timeout: The API did not receive stats from the controller in time"}





#api endpoint for retrieving and deciphering live flow stats to find top LIVE consumer
@app.post("/send_live_stats")
async def send_live_stats(data: dict):
    snapshot1 = data.get("snapshot1", [])
    snapshot2 = data.get("snapshot2", [])
    global top_consumer_cache

    print("Snapshot 1: ", snapshot1)
    print("Snapshot 2: ", snapshot2)

    live_flows = []

    for flow1 in snapshot1:
        for flow2 in snapshot2:
            if flow1.get("flow_id") == flow2.get("flow_id"): #make sure we are comparing the same flow
                if flow1.get("byte_count") != flow2.get("byte_count"): #make sure the flow has changed (is live)
                    byteDifference = flow2.get("byte_count", 0) - flow1.get("byte_count", 0)
                    packetDifference = flow2.get("packet_count", 0) - flow1.get("packet_count", 0)

                    bandwidth = round((byteDifference * 8) / 1000000, 2)  # bytes to bits to Mbps
    
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
            print(f"Top_consumer = {top_consumer}\n")
            await top_consumer_cache.put(top_consumer)
        except Exception as e:
            print(f"Error calculating top consumer: {e}")
    else:
        print("There is currently nothing using bandwidth.")

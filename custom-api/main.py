from fastapi import FastAPI
from pydantic import BaseModel
import socket

#initialise the FastAPI
app = FastAPI()

bandwidth_stats = {}
top_consumer_cache = None

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

    top_consumer_cache = None

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.2", 9090))
        s.sendall(b"get_live_stats")
    except Exception as e:
        print(f"Error connecting to the controller: {e}")

    while True:
        if top_consumer_cache:
            return {"top_consumer": top_consumer_cache}
        else:
            continue





#api endpoint for retrieving and deciphering live flow stats to find top LIVE consumer
@app.post("/send_live_stats")
async def send_live_stats(data: dict):
    snapshot1 = data.get("snapshot1", [])
    snapshot2 = data.get("snapshot2", [])
    global top_consumer_cache

    live_flows = []

    for flow1 in snapshot1:
        for flow2 in snapshot2:
            if flow1.get("flow_id") == flow2.get("flow_id"):
                if flow1.get("byte_count") != flow2.get("byte_count"):
                    live_flows.append(flow2)
                    break

    if live_flows:
        print(f"Here are the live flows: {live_flows}\n")
        try:
            top_consumer = max(live_flows, key=lambda x: round((x.get("byte_count", 0) * 8) / x.get("duration_sec", 1) / 1000000), default=None) #find the highest bandwidth consumer
            top_consumer_cache = top_consumer
        except Exception as e:
            print(f"Error calculating top consumer: {e}")

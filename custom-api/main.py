from fastapi import FastAPI
from pydantic import BaseModel

#initialise the FastAPI
app = FastAPI()

bandwidth_stats = {}

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
    print("IT WORKED!!!")
    print(bandwidth_stats)
    #need to figure out how to properly retrieve bandwidth stats


#api endpoint for getting the bandwidth information
@app.get("/retrieve_bandwidth")
async def retrieve_bandwidth():
    global bandwidth_stats
    if not bandwidth_stats:
        print("ERROR: NO DATA FOUND")
    
    top_consumer = max(bandwidth_stats["stats"], key=lambda x: x["bytes"], default=None)
    
    return {"top_consumer": top_consumer}
# api/index.py
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json

# Load telemetry data once at startup
try:
    json_path = os.path.join(os.path.dirname(__file__), "q-vercel-latency.json")
    with open(json_path, "r") as f:
        telemetry = json.load(f)
except FileNotFoundError:
    telemetry = []
    print(f"Warning: telemetry file not found at {json_path}")
except json.JSONDecodeError:
    telemetry = []
    print(f"Warning: telemetry file is not valid JSON at {json_path}")

# Request body model
class LatencyRequest(BaseModel):
    regions: list[str]
    threshold_ms: float

app = FastAPI()

# Enable CORS for all origins and methods
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # Allow any origin
    allow_methods=["*"],      # Allow POST, GET, OPTIONS, etc.
    allow_headers=["*"],      # Allow all headers
    allow_credentials=False
)

# OPTIONS preflight route to handle CORS
@app.options("/latency")
async def latency_options():
    return Response(status_code=200)

# POST endpoint to calculate metrics
@app.post("/latency")
async def check_latency(req: LatencyRequest):
    if not telemetry:
        raise HTTPException(status_code=500, detail="Telemetry data not available")

    response = {}

    for region in req.regions:
        region_data = [r for r in telemetry if r["region"] == region]

        if not region_data:
            response[region] = {
                "avg_latency": None,
                "p95_latency": None,
                "avg_uptime": None,
                "breaches": 0
            }
            continue

        latencies = [r["latency_ms"] for r in region_data]
        uptimes = [r["uptime_pct"] for r in region_data]

        # avg_latency
        avg_latency = sum(latencies) / len(latencies)

        # p95_latency
        sorted_lat = sorted(latencies)
        idx = int(0.95 * len(sorted_lat)) - 1
        p95_latency = sorted_lat[max(idx, 0)]

        # avg_uptime
        avg_uptime = sum(uptimes) / len(uptimes)

        # breaches
        breaches = sum(1 for l in latencies if l > req.threshold_ms)

        response[region] = {
            "avg_latency": round(avg_latency, 2),
            "p95_latency": round(p95_latency, 2),
            "avg_uptime": round(avg_uptime, 3),
            "breaches": breaches
        }

    return response

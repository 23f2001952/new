# api/index.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from pydantic import BaseModel
import json
import statistics

# Load telemetry data once at startup
with open("q-vercel-latency.json") as f:
    telemetry = json.load(f)

# Define request body model
class LatencyRequest(BaseModel):
    regions: list[str]
    threshold_ms: float

app = FastAPI()

# Enable CORS for all origins and POST
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST"],
    allow_headers=["*"],
)

@app.post("/latency")
async def check_latency(req: LatencyRequest):
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
        p95_latency = sorted_lat[max(idx,0)]

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

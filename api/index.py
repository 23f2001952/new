# api/index.py
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
from pathlib import Path
import os
import json

app = FastAPI()

# Enable CORS for all origins and methods
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
    expose_headers=["*"],
)

# Middleware to add Access-Control-Allow-Private-Network
@app.middleware("http")
async def add_pna_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Private-Network"] = "true"
    return response

# Load telemetry dataset at startup
DATA_FILE = Path(__file__).parent / "q-vercel-latency.json"
if DATA_FILE.exists():
    df = pd.read_json(DATA_FILE)
else:
    df = pd.DataFrame()
    print(f"Warning: telemetry file not found at {DATA_FILE}")

@app.get("/")
async def root():
    return {"message": "Vercel Latency Analytics API is running."}

@app.get("/latency")
async def get_latency():
    if df.empty:
        raise HTTPException(status_code=500, detail="Telemetry data not available")
    all_regions = df["region"].unique()
    return {"regions": calculate_metrics(all_regions, 180)}

@app.post("/latency")
async def post_latency(request: Request):
    if df.empty:
        raise HTTPException(status_code=500, detail="Telemetry data not available")

    payload = await request.json()
    regions_to_process = payload.get("regions", [])
    threshold = payload.get("threshold_ms", 200)

    return {"regions": calculate_metrics(regions_to_process, threshold)}

# Shared function using pandas + numpy
def calculate_metrics(regions, threshold_ms):
    results = []
    for region in regions:
        region_df = df[df["region"] == region]

        if region_df.empty:
            results.append({
                "region": region,
                "avg_latency": None,
                "p95_latency": None,
                "avg_uptime": None,
                "breaches": 0
            })
            continue

        avg_latency = round(region_df["latency_ms"].mean(), 2)
        p95_latency = round(np.percentile(region_df["latency_ms"], 95), 2)
        avg_uptime = round(region_df["uptime_pct"].mean(), 3)
        breaches = int(region_df[region_df["latency_ms"] > threshold_ms].shape[0])

        results.append({
            "region": region,
            "avg_latency": avg_latency,
            "p95_latency": p95_latency,
            "avg_uptime": avg_uptime,
            "breaches": breaches
        })
    return results

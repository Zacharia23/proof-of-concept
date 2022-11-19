#!/usr/bin/env python
import asyncio
import sqlite3

import aiohttp
import aioredis
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Create our app
app = FastAPI(
    title="POC-CB",
    description="Proof of Concept for the Quick Response while Backgrounding the Heavy Processes",
)
# Request session
SESSION = None

# add Cors
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


# Close all Connections
async def close():
    global SESSION
    print("Closing Connection...")
    # Close all connection
    await SESSION.close()
    SESSION = None


# Our async requests
async def send_req(url: str, data: dict, method="GET"):
    if method == "GET":
        async with SESSION.get(url) as resp:
            reply = await resp.json()
            return reply
    if method == "POST":
        async with SESSION.post(url, json=data) as resp:
            reply = await resp.json()
            return reply


@app.on_event("startup")
async def startup_event():
    global SESSION
    print("Opening App")
    SESSION = aiohttp.ClientSession()


@app.post("/control_number")
async def control_number(data: Request):
    body = await data.json()
    # print(f"Body: {body}")
    resp = await send_req("http://localhost:3000/control_number", body, "POST")
    # print(f"Response: {resp}")
    return JSONResponse(status_code=200, content=resp)


@app.post("/callback")
async def callback(data: Request):
    body = await data.json()
    print(f"Body: {body}")
    return JSONResponse(status_code=200, content=body)


@app.on_event("shutdown")
async def shutdown_event():
    print("Shutting Down...")
    await close()


if __name__ == "__main__":
    uvicorn.run("cb:app", port=3001, reload=True)
# uvicorn poc:app --reload

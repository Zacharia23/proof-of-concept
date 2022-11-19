#!/usr/bin/env python
import asyncio
import sqlite3

import aiohttp
import aioredis
import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, BaseSettings, ValidationError

from db import Database


# Our default configs
class Config(BaseSettings):
    redis_url: str = "redis://localhost:6379"


# Bill Model
class Bill(BaseModel):
    id: int
    name: str
    price: float


# Not recommended but for now, this keeps track of current index to get next Control Number
CURRENT_INDEX = 0
# Callback url
CALLBACK_URL = "http://localhost:3001/callback"
# SQLite3 database instance
db = Database()
# Loading our Config
config = Config()
# Create our app
app = FastAPI(
    title="POC",
    description="Proof of Concept for the Quick Response while Backgrounding the Heavy Processes",
)
# Request session
SESSION = None
# Instead of using Databases it is adviced to user separate instances
# Eg. redis-server --port 6379 and redis-server --port 6380
# The Initial Control Numbers
nums = aioredis.from_url(config.redis_url, decode_responses=True)
# The Used Control Numbers
used = aioredis.from_url(config.redis_url, db=1, decode_responses=True)

# add Cors
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


# Simple function to seed sample data to Redis DB
async def seed(rds, length=20):
    print("Seeding data for POC...")
    from nanoid import generate

    for id in range(length):
        await rds.set(id, generate())


# Clears all data from Redis DBs
async def clear():
    print("Clearing DBs...")
    # Clear all data in DB
    db.deleteAll()
    await nums.flushdb()
    await used.flushdb()


# Close all Connections
async def close():
    global SESSION
    print("Closing Connections...")
    # Close all redis connections
    db.connection.close()
    await nums.close()
    await used.close()
    await SESSION.close()
    SESSION = None


async def save_to_db(control_number, bill):
    print("Saving to DB...")
    db.insertOne(bill.id, bill.name, bill.price, control_number)
    print(f"Control Number: {control_number} - Bill: {bill}")
    print("Saved to DB")


# Get all data from given Redis DB, in a Dictionary
async def get_all(rds):
    keys = await rds.keys("*")
    if len(keys) > 0:
        all = {}
        for k in keys:
            all[k] = await rds.get(k)
        return all
    return []


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
    # Seed our Control Numbers
    print("Opening App")
    SESSION = aiohttp.ClientSession()
    db.execute(
        "CREATE TABLE IF NOT EXISTS bills(id INTEGER PRIMARY KEY AUTOINCREMENT, bill_id INTEGER(8) NOT NULL, name TEXT NOT NULL, price REAL NOT NULL, control_number TEXT)"
    )
    db.deleteAll()
    await seed(nums)


@app.get("/restart")
async def restart(background_tasks: BackgroundTasks):
    global CURRENT_INDEX
    CURRENT_INDEX = 0
    await clear()
    background_tasks.add_task(seed, nums)
    print("System Refreshed")
    return {"code": 200, "message": "Restarted"}


@app.post("/control_number")
async def control_number(req: Request, background_tasks: BackgroundTasks):
    global CURRENT_INDEX
    body = await req.json()
    try:
        bill = Bill(**body)
        # bill = Bill.parse_obj(body)
    except ValidationError as e:
        error_resp = await send_req(
            CALLBACK_URL,
            {"message": "Failed", "error": e.errors()},
            "POST",
        )
        return HTTPException(
            status_code=422,
            detail=e.errors(),
        )
    await send_req(CALLBACK_URL, {"message": "Successful"}, "POST")
    # await nums.move(CURRENT_INDEX, 1)
    # CLIENT
    cn = await nums.get(CURRENT_INDEX)  # getdel
    await nums.delete(CURRENT_INDEX)
    await used.set(bill.id, cn)
    CURRENT_INDEX += 1
    await send_req(
        CALLBACK_URL,
        {"control_number": cn},
        "POST",
    )
    # UPDATE DETAILS TO DB
    background_tasks.add_task(save_to_db, cn, bill)
    return JSONResponse(
        status_code=200,
        content={
            "code": 200,
            "message": "Successful",
            "data": {"control_number": cn},
        },
    )


@app.get("/all")
async def all():
    all_nums = await get_all(nums)
    all_used = await get_all(used)
    print(f"Nums: {all_nums} - Used: {all_used}")

    return {
        "code": 200,
        "message": "Successful",
        "data": {"nums": all_nums, "used": all_used},
    }


@app.get("/control_numbers")
async def control_numbers():
    c_nums = await get_all(nums)

    return {"code": 200, "message": "Successful", "data": c_nums}


@app.get("/used")
async def c_used():
    c_used = await get_all(used)

    return {"code": 200, "message": "Successful", "data": c_used}


@app.get("/db")
async def db_get():
    al = db.getData()

    return {"code": 200, "message": "Successful", "data": al}


@app.on_event("shutdown")
async def shutdown_event():
    print("Shutting Down...")
    await clear()
    await close()


if __name__ == "__main__":
    uvicorn.run("poc:app", port=3000, reload=True)

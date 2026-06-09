from fastapi import FastAPI, File, UploadFile, Form 
import os
import time
import requests
import asyncio
import random
import aiofiles
from httpx import AsyncClient
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from fastapi.responses import StreamingResponse
from fastapi.exceptions import HTTPException
from fastapi.params import Header
# mysql connection
from mysql.connector.aio import connect

from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

# cors
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_HOST = os.environ.get("DB_HOST") 
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_PORT = int(os.environ.get("DB_PORT") or 3306)


@app.get("/")
def read_root():
    return {"Hello": "World"}

# Use def for Blocking operations (Blocking I/O) - It uses Thread Pool
@app.get("/t")
def thread_pool():
    print("Slow started")
    time.sleep(10)
    print("Slow finished")
    return {"Hello": "World"}

# Use Async + Awaitable I/O to avoid blocking the event loop (Non Blocking I/O)
@app.get("/f")
async def event_loop():
    try:
        print("Fast started")
        async with AsyncClient() as ac:
            r = await ac.get("https://jsonplaceholder.typicode.com/todos/1")
        print("Fast finished")
        return {"Hello": "World"}
    except Exception as e:
        print(e)

#  This is a BAD PRACTICE - it blocks the event loop
@app.get("/f2")
async def bad_practice():
    try:
        print("Fast started")
        r = requests.get("https://jsonplaceholder.typicode.com/todos/1")
        print("Fast finished")
        return {"Hello": "World"}
    except Exception as e:
        print(e)


# For Highly CPU-bound work (image processing, ML inference, heavy computation) use a `ProcessPoolExecutor`
# For Background Tasks - Use Celery


# GIL (Global Interpreter Lock) - Python's GIL means threads don't give real CPU parallelism
# Due to the GIL, only one thread per Python process can execute Python bytecode at a given moment.
# The interpreter periodically releases and reacquires the GIL (roughly every few milliseconds), allowing another thread to run.
# So it switches between threads only when GIL is released
# Gunicorn with multiple workers can give real CPU parallelism
# Multiple Gunicorn workers (separate processes) each have their own GIL, enabling real parallelism across CPU cores.
@app.get("/cpu_bound")
def cpu_bound():
    try:
        sum_res = 0
        print("CPU started")
        for i in range(10**9):
            sum_res += i
        print("CPU finished")
        return { "sum": sum_res }
    except Exception as e:
        print(e)


async def asyncio_exec_fn(number):
    print("Asyncio started", number)

    await asyncio.sleep(10)

    print("Asyncio finished", number)

    return {"Hello": "World"}

#  Total wait time of n simultaneous requests is around 10 , instead of number of requests * 10 
@app.get("/asyncio/{number}")
async def asyncio_fn(number):
    number = int(number)
    return await asyncio_exec_fn(number)

# DB execution

@app.get("/db/{number}")
async def db_fn(number):
    num = number
    number = int(number) + random.randint(1, 10)

    print("Request", num)
    con = await connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT
    )
    cursor = await con.cursor()
    await cursor.execute("SELECT SLEEP(%s)", (number,))
    # await cursor.execute("SELECT 1+0 AS result ")
    # result = await cursor.fetchone()
    await con.close()

    print("Response", num)

    return { "result": num }


# FILE UPLOAD
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    contents = await file.read()

    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size": len(contents)
    }

# chunked upload
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/upload-chunk")
async def upload_chunk(
    chunk: UploadFile = File(...),
    filename: str = Form(...),
    chunkIndex: int = Form(...),
    totalChunks: int = Form(...)
):
    filepath = os.path.join(UPLOAD_DIR, filename)

    data = await chunk.read()

    # wb - write binary
    # ab - append binary
    mode = "wb" if chunkIndex == 0 else "ab"

    # with open(filepath, mode) as f:
    #     f.write(data)

    async with aiofiles.open(filepath, mode) as f: 
        await f.write(data)

    return {
        "chunk": chunkIndex,
        "total": totalChunks
    }

# Video Stream
VIDEO_PATH = "sample.mp4"

@app.get("/video")
def stream_video(range: str = Header(None)):
    if not os.path.exists(VIDEO_PATH):
        raise HTTPException(status_code=404, detail="Video file not found")
    
    file_size = os.path.getsize(VIDEO_PATH)
    
    # Default chunk size (approx 1MB)
    chunk_size = 1024 * 1024
    start = 0
    end = file_size - 1

    # Parse the Range header (e.g., "bytes=0-")
    if range:
        range_value = range.replace("bytes=", "").split("-")
        start = int(range_value[0])
        if range_value[1]:
            end = int(range_value[1])
        else:
            end = min(start + chunk_size, file_size - 1)

    # Ensure the requested range is valid
    if start >= file_size or end >= file_size:
        raise HTTPException(status_code=416, detail="Requested Range Not Satisfiable")

    content_length = end - start + 1

    # Generator to read the file in chunks
    def video_stream_generator():
        with open(VIDEO_PATH, "rb") as video_file:
            video_file.seek(start)
            remaining = content_length
            while remaining > 0:
                chunk_to_read = min(1024 * 64, remaining)  # Read in 64KB internal chunks
                data = video_file.read(chunk_to_read)
                if not data:
                    break
                remaining -= len(data)
                yield data

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Type": "video/mp4",
    }

    return StreamingResponse(video_stream_generator(), status_code=206, headers=headers)
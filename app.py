from fastapi import FastAPI
import time
import requests
import asyncio
from httpx import AsyncClient

app = FastAPI()


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

#  This is a bad practice - it blocks the event loop
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

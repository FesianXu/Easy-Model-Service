import asyncio
from fastapi import FastAPI, HTTPException, Request
from contextlib import asynccontextmanager
import aiohttp
import traceback

ALL_URLS = ["url1", "url2"]
AGENT_PORTS = list(range(10000, 10032))
HEALTH_CHECK_INTERVAL = 5
REQUEST_TIMEOUT = 30
MAX_QUEUE_SIZE = 1000

class LoadBalancer:
    def __init__(self):
        self.backends = [f"http://{url}:{port}" 
            for port in AGENT_PORTS
            for url in ALL_URLS]
        
        self.active_backends = self.backends.copy()
        self.current_index = 0
        self.request_queue = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)
        self.session = None
        self.index_lock = asyncio.Lock()

    async def initialize(self):
        self.session = aiohttp.ClientSession()

    async def health_checker(self):
        while True:
            await asyncio.sleep(HEALTH_CHECK_INTERVAL)
            alive = []
            for url in self.backends:
                try:
                    async with self.session.get(f"{url}/health", timeout=2) as resp:
                        if resp.status == 200:
                            alive.append(url)
                except Exception as e:
                    print(f"Health check failed for {url}: {e}")
                    continue
            
            async with self.index_lock:
                self.active_backends = alive
                self.current_index = 0 
            print(f"Active backends: {len(alive)}")

    async def worker(self):
        while True:
            request_data = await self.request_queue.get()
            client_request, client_response = request_data
            
            async with self.index_lock:
                if not self.active_backends:
                    client_response(({"detail": "No backends available"}, 503))
                    self.request_queue.task_done()
                    continue
                # RR to select one active backend
                self.current_index %= len(self.active_backends)
                backend_url = self.active_backends[self.current_index]
                self.current_index += 1

            try:
                headers = dict(client_request.headers)
                headers.pop("Host", None)
                async with self.session.request(
                    method=client_request.method,
                    url=f"{backend_url}{client_request.url.path}",
                    headers=headers,
                    data=await client_request.body(),
                    timeout=REQUEST_TIMEOUT
                ) as resp:
                    content = await resp.read()
                    client_response((content, resp.status))
            except asyncio.TimeoutError:
                client_response(({"detail": "Backend timeout"}, 504))
            except Exception as e:
                traceback.print_exc()
                print(f"Error forwarding to {backend_url}: {e}")
                client_response(({"detail": "Internal error"}, 500))
            finally:
                self.request_queue.task_done()

@asynccontextmanager
async def lifespan(app: FastAPI):
    lb = LoadBalancer()
    await lb.initialize()
    tasks = [
        asyncio.create_task(lb.health_checker()),
        *[asyncio.create_task(lb.worker()) for _ in range(32)]
    ]
    app.state.lb = lb
    yield
    
    for task in tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    await lb.session.close()

app = FastAPI(lifespan=lifespan)

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_request(request: Request):
    lb = request.app.state.lb
    if lb.request_queue.full():
        raise HTTPException(429, detail="Too many requests")
    response = asyncio.Future()
    await lb.request_queue.put((request, response.set_result))
    content, status_code = await response

    if status_code != 200:
        raise HTTPException(status_code=status_code, detail=content.get("detail"))
    return content

import httpx
from keymesh import SyncKeyPool

class SyncKeymeshTransport(httpx.BaseTransport):
    def __init__(self, base_transport: httpx.BaseTransport, pool: SyncKeyPool):
        self.base_transport = base_transport
        self.pool = pool

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        key = self.pool.acquire()
        request.headers["Authorization"] = f"Bearer {key}"
        try:
            response = self.base_transport.handle_request(request)
            if response.status_code == 429:
                self.pool.mark_rate_limited(key)
            return response
        except Exception:
            self.pool.mark_failed(key)
            raise
        finally:
            self.pool.release(key)
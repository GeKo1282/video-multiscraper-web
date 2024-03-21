import aiohttp, asyncio
from scripts.helper.util import generate_id

class Requester:
    requesters = {}

    def __init__(self, id: str = None, *, default_user_agent: str = None, default_headers: dict = None,
     default_timeout: int = 10, default_retries: int = 3, default_retry_delay: int = 5, backoff_exponent: int = 2,
     default_proxies: dict = None, max_concurrent_requests: int = 100, max_requests_per_second: int = -1,
     max_requests_per_minute: int = -1):
        if not id:
            id = generate_id(16, "hex", avoid=list(self.requesters.keys()))

        if id in Requester.requesters:
            raise ValueError("Requester with the same ID already exists!")
        
        Requester.requesters[id] = self

        self.id = id
        self.default_user_agent = default_user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        self.default_headers = default_headers or {}
        self.default_timeout = default_timeout
        self.default_retries = default_retries
        self.default_retry_delay = default_retry_delay
        self.backoff_exponent = backoff_exponent
        self.default_proxies = default_proxies or {}
        self.max_concurrent_requests = max_concurrent_requests
        self.max_requests_per_second = max_requests_per_second
        self.max_requests_per_minute = max_requests_per_minute

        self._requests_second = 0
        self._requests_minute = 0

        self._requests_total = 0
        self._requests_failed = 0
        self._requests_retried = 0

        self._total_data_sent = 0
        self._total_data_received = 0

        self._current_backoff = 1
        self._current_requests = 0

        self._requests_on_hold = 0

    @staticmethod
    def get_requester(id: str) -> "Requester":
        return Requester.requesters.get(id)

    async def _reset_counters(self):
        seconds = 0

        while True:
            await asyncio.sleep(1)
            seconds += 1

            if self.max_requests_per_second != -1 and seconds >= 60:
                self._requests_second = 0
                seconds = 0

            if self.max_requests_per_minute != -1:
                self._requests_minute = 0

    def _should_hold(self):
        return self._current_requests >= self.max_concurrent_requests or \
             self._requests_minute >= self.max_requests_per_minute or \
             self._requests_second >= self.max_requests_per_second

    async def _request(self, method: str, url: str, *, headers: dict = None, timeout: int = None, retries: int = None,
        retry_delay: int = None, backoff_exponent: int = None, proxies: dict = None, data: dict = None, allow_redirects: bool = True, **kwargs) -> aiohttp.ClientResponse:
            if self._should_hold():
                self._requests_on_hold += 1

                while self._should_hold():
                    await asyncio.sleep(.2)

                self._requests_on_hold -= 1

            if not headers:
                headers = self.default_headers
            else:
                headers = {**self.default_headers, **headers}
    
            if not timeout:
                timeout = self.default_timeout
    
            if not retries:
                retries = self.default_retries
    
            if not retry_delay:
                retry_delay = self.default_retry_delay
    
            if not backoff_exponent:
                backoff_exponent = self.backoff_exponent
    
            if not proxies:
                proxies = self.default_proxies
    
            if self.default_user_agent not in headers:
                headers["User-Agent"] = self.default_user_agent
    
            self._current_requests += 1
            self._requests_total += 1
    
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, headers=headers, timeout=timeout, data=data, allow_redirects=allow_redirects, **kwargs) as response:
                    self._current_requests -= 1
    
                    if response.status >= 400:
                        self._requests_failed += 1
                        if retries == 0:
                            return None
                        
                        self._requests_retried += 1
                        await asyncio.sleep(retry_delay)
                        self._current_backoff *= backoff_exponent
                        return await self._request(method, url, headers=headers, timeout=timeout, retries=retries - 1,
                            retry_delay=retry_delay * backoff_exponent, backoff_exponent=backoff_exponent, proxies=proxies, data=data,
                            allow_redirects=allow_redirects, **kwargs)

                    self._requests_second += 1
                    self._requests_minute += 1
                    self._current_backoff = 1
    
                    return {
                         "status": response.status,
                         "headers": response.headers,
                         "text": await response.text()
                    }
                
    async def get(self, url: str, *, headers: dict = None, timeout: int = None, retries: int = None, retry_delay: int = None,
        backoff_exponent: int = None, proxies: dict = None, params: dict = None, allow_redirects: bool = True, ssl: bool = True,
        verify_ssl: bool = True, **kwargs):
            return await self._request("GET", url, headers=headers, timeout=timeout, retries=retries, retry_delay=retry_delay,
                backoff_exponent=backoff_exponent, proxies=proxies, params=params, allow_redirects=allow_redirects, ssl=ssl,
                verify_ssl=verify_ssl, **kwargs)
    
    async def post(self, url: str, *, headers: dict = None, timeout: int = None, retries: int = None, retry_delay: int = None,
        backoff_exponent: int = None, proxies: dict = None, data: dict = None, json: dict = None, allow_redirects: bool = True,
        ssl: bool = True, verify_ssl: bool = True, **kwargs):
            return await self._request("POST", url, headers=headers, timeout=timeout, retries=retries, retry_delay=retry_delay,
                backoff_exponent=backoff_exponent, proxies=proxies, data=data, json=json, allow_redirects=allow_redirects, ssl=ssl,
                verify_ssl=verify_ssl, **kwargs)
    
    async def head(self, url: str, *, headers: dict = None, timeout: int = None, retries: int = None, retry_delay: int = None,
        backoff_exponent: int = None, proxies: dict = None, data: dict = None, json: dict = None, allow_redirects: bool = True,
        ssl: bool = True, verify_ssl: bool = True, **kwargs):
            return await self._request("HEAD", url, headers=headers, timeout=timeout, retries=retries, retry_delay=retry_delay,
                backoff_exponent=backoff_exponent, proxies=proxies, data=data, json=json, allow_redirects=allow_redirects, ssl=ssl,
                verify_ssl=verify_ssl, **kwargs)
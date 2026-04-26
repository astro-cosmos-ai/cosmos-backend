import asyncio
import httpx
from app.core.config import settings
from app.core.exceptions import AstrologyAPIError

BASE_URL = "https://json.astrologyapi.com/v1"

# Lazy per-loop semaphore: module-level asyncio.Semaphore binds to the loop
# that was running when it was created, causing RuntimeError across test runs
# (each async test gets a fresh loop). Keying by loop id avoids this.
_semaphores: dict[int, asyncio.Semaphore] = {}


def _get_semaphore() -> asyncio.Semaphore:
    loop = asyncio.get_running_loop()
    loop_id = id(loop)
    if loop_id not in _semaphores:
        _semaphores[loop_id] = asyncio.Semaphore(5)
    return _semaphores[loop_id]


async def _post(endpoint: str, payload: dict, client: httpx.AsyncClient) -> dict | None:
    url = f"{BASE_URL}/{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "x-astrologyapi-key": settings.astrology_api_key,
        "Accept-Language": "en",
    }
    async with _get_semaphore():
        for attempt in range(3):
            if attempt > 0:
                await asyncio.sleep(15 * attempt)
            try:
                resp = await client.post(url, headers=headers, json=payload, timeout=30)
                if resp.status_code == 200:
                    return resp.json()
                if resp.status_code == 429:
                    continue
                return None
            except Exception:
                if attempt == 2:
                    return None
    return None


async def fetch_endpoint(endpoint: str, payload: dict) -> dict | None:
    async with httpx.AsyncClient() as client:
        return await _post(endpoint, payload, client)


async def fetch_many(calls: list[tuple[str, dict]]) -> list[dict | None]:
    async with httpx.AsyncClient() as client:
        tasks = [_post(endpoint, payload, client) for endpoint, payload in calls]
        return await asyncio.gather(*tasks)

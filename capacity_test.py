import asyncio
import aiohttp
import time
import statistics

API_KEY = "dKVk85DEx9QXUfK17ZSSpnPBAVurorCOAjz9cPCMg6PCY6FqEY"
API_URL = "https://api.ambient.xyz/v1/chat/completions"
MODEL = "moonshotai/kimi-k2.7-code"

PROMPTS = [
    "What are the top 3 risks of DeFi lending?",
    "What is a reentrancy attack?",
    "What is 2+2?",
    "Explain proof of work in one sentence.",
    "What is impermanent loss?"
]

async def send(session, req_id, prompt):
    start = time.time()
    try:
        async with session.post(
            API_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={"model": MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": 150},
            timeout=aiohttp.ClientTimeout(total=45)
        ) as resp:
            latency = round(time.time() - start, 2)
            data = await resp.json()
            content = data["choices"][0]["message"].get("reasoning_content") or data["choices"][0]["message"].get("content") or ""
            quality = "OK" if len(content) > 30 else "DEGRADED"
            return {"id": req_id, "status": resp.status, "latency": latency, "quality": quality}
    except Exception as e:
        return {"id": req_id, "status": 0, "latency": round(time.time()-start, 2), "quality": "FAILED", "error": str(e)}

async def run_wave(n, label, delay_between=0):
    print(f"\n--- {label}: {n} requests ---")
    async with aiohttp.ClientSession() as session:
        start = time.time()
        tasks = [send(session, i, PROMPTS[i % len(PROMPTS)]) for i in range(n)]
        results = await asyncio.gather(*tasks)
        total = round(time.time() - start, 2)

        success = [r for r in results if r["status"] == 200]
        failed = [r for r in results if r["status"] != 200]
        degraded = [r for r in results if r.get("quality") == "DEGRADED"]
        latencies = [r["latency"] for r in success]

        print(f"Total time  : {total}s")
        print(f"Success     : {len(success)}/{n}")
        print(f"Failed      : {len(failed)}")
        print(f"Degraded    : {len(degraded)}")
        if latencies:
            print(f"Avg latency : {round(statistics.mean(latencies), 2)}s")
            print(f"Spread      : {round(max(latencies)-min(latencies), 2)}s")
        return results

async def main():
    print("=" * 55)
    print("Ambient Capacity Test — Week 17")
    print("=" * 55)

    await run_wave(10, "Wave 1 — Baseline")
    await asyncio.sleep(5)
    await run_wave(25, "Wave 2 — Medium load")
    await asyncio.sleep(5)
    await run_wave(50, "Wave 3 — Heavy load")
    await asyncio.sleep(5)
    await run_wave(10, "Wave 4 — Recovery check")

asyncio.run(main())

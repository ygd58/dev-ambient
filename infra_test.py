import asyncio
import aiohttp
import time
import statistics

API_KEY = "dKVk85DEx9QXUfK17ZSSpnPBAVurorCOAjz9cPCMg6PCY6FqEY"
API_URL = "https://api.ambient.xyz/v1/chat/completions"
MODEL = "moonshotai/kimi-k2.7-code"

PROMPT = "What are the top 3 risks of DeFi lending protocols?"

async def send(session, req_id, batch):
    start = time.time()
    try:
        async with session.post(
            API_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={"model": MODEL, "messages": [{"role": "user", "content": PROMPT}], "max_tokens": 200},
            timeout=aiohttp.ClientTimeout(total=60)
        ) as resp:
            latency = time.time() - start
            data = await resp.json()
            content = data["choices"][0]["message"].get("reasoning_content") or data["choices"][0]["message"].get("content") or ""
            return {"id": req_id, "batch": batch, "status": resp.status, "latency": round(latency, 2), "len": len(content)}
    except Exception as e:
        return {"id": req_id, "batch": batch, "status": 0, "latency": round(time.time()-start, 2), "error": str(e)}

async def run_batch(n, label):
    print(f"\n--- {label}: {n} parallel requests ---")
    async with aiohttp.ClientSession() as session:
        start = time.time()
        results = await asyncio.gather(*[send(session, i, n) for i in range(n)])
        total = time.time() - start
        success = [r for r in results if r["status"] == 200]
        failed = [r for r in results if r["status"] != 200]
        latencies = [r["latency"] for r in success]
        print(f"Total time  : {round(total, 2)}s")
        print(f"Success     : {len(success)}/{n}")
        print(f"Failed      : {len(failed)}")
        if latencies:
            print(f"Avg latency : {round(statistics.mean(latencies), 2)}s")
            print(f"Min latency : {min(latencies)}s")
            print(f"Max latency : {max(latencies)}s")
            print(f"Spread      : {round(max(latencies)-min(latencies), 2)}s")
        if failed:
            print(f"First error : {failed[0].get('error', failed[0].get('status'))}")
    return results

async def main():
    print("=" * 50)
    print("Ambient Infra Loop — Week 14 SGLANG Load Test")
    print("=" * 50)
    
    await run_batch(5, "Light load")
    await asyncio.sleep(5)
    await run_batch(10, "Medium load")
    await asyncio.sleep(5)
    await run_batch(20, "Heavy load")

asyncio.run(main())

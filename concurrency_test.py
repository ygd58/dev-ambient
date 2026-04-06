import asyncio
import aiohttp
import time
import statistics

API_KEY = "nwxog69qsdx1Of28dzVJxaDKmT3wvvuPmK46WnzhtYH03jS6jP"
API_URL = "https://api.ambient.xyz/v1/chat/completions"

PROMPT_SIMPLE = "What is 2+2?"
PROMPT_MEDIUM = "Explain proof of work in 3 sentences."
PROMPT_HEAVY = "List 5 risks of decentralized AI inference with likelihood and impact."

async def send_request(session, prompt, req_id):
    start = time.time()
    try:
        async with session.post(
            API_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={"model": "zai-org/GLM-5-FP8", "messages": [{"role": "user", "content": prompt}], "max_tokens": 200},
            timeout=aiohttp.ClientTimeout(total=60)
        ) as resp:
            await resp.json()
            latency = time.time() - start
            return {"id": req_id, "status": resp.status, "latency": latency, "error": None}
    except Exception as e:
        return {"id": req_id, "status": 0, "latency": time.time() - start, "error": str(e)}

async def run_batch(n, prompt, label):
    print(f"\n--- {label}: {n} parallel requests ---")
    async with aiohttp.ClientSession() as session:
        start = time.time()
        tasks = [send_request(session, prompt, i) for i in range(n)]
        results = await asyncio.gather(*tasks)
        total = time.time() - start
        
        success = [r for r in results if r["status"] == 200]
        failed = [r for r in results if r["status"] != 200]
        latencies = [r["latency"] for r in success]
        
        print(f"Total time    : {total:.2f}s")
        print(f"Success       : {len(success)}/{n}")
        print(f"Failed        : {len(failed)}")
        if latencies:
            print(f"Avg latency   : {statistics.mean(latencies):.2f}s")
            print(f"Min latency   : {min(latencies):.2f}s")
            print(f"Max latency   : {max(latencies):.2f}s")
        if failed:
            print(f"First error   : {failed[0]['error']}")

async def main():
    print("=" * 50)
    print("Ambient Concurrency Test — Week 10")
    print("=" * 50)
    
    for n in [10, 50, 100]:
        await run_batch(n, PROMPT_SIMPLE, f"Simple prompt x{n}")
        await asyncio.sleep(5)
    
    await run_batch(10, PROMPT_HEAVY, "Heavy prompt x10")

asyncio.run(main())

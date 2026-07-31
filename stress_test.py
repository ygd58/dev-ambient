import asyncio
import aiohttp
import time
import statistics
import json

API_KEY = "dKVk85DEx9QXUfK17ZSSpnPBAVurorCOAjz9cPCMg6PCY6FqEY"
API_URL = "https://api.ambient.xyz/v1/chat/completions"
MODEL = "moonshotai/kimi-k2.7-code"

PROMPTS = [
    "What is liquidation risk in DeFi?",
    "What is 2+2?",
    "Explain proof of work in one sentence.",
    "What is impermanent loss?",
    "What is a smart contract audit?"
]

async def send(session, req_id, prompt):
    start = time.time()
    try:
        async with session.post(
            API_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={"model": MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": 150},
            timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            latency = round(time.time() - start, 2)
            data = await resp.json()
            content = data["choices"][0]["message"].get("reasoning_content") or data["choices"][0]["message"].get("content") or ""
            return {"id": req_id, "status": resp.status, "latency": latency, "ok": len(content) > 20}
    except asyncio.TimeoutError:
        return {"id": req_id, "status": 0, "latency": 30, "ok": False, "error": "TIMEOUT"}
    except Exception as e:
        return {"id": req_id, "status": 0, "latency": round(time.time()-start, 2), "ok": False, "error": str(e)[:30]}

async def run_wave(session, n, label, delay=0):
    if delay:
        await asyncio.sleep(delay)
    start = time.time()
    results = await asyncio.gather(*[send(session, i, PROMPTS[i % len(PROMPTS)]) for i in range(n)])
    total = round(time.time() - start, 2)
    success = [r for r in results if r["status"] == 200 and r["ok"]]
    failed = [r for r in results if not (r["status"] == 200 and r["ok"])]
    latencies = [r["latency"] for r in success]
    print(f"\n{label}: {n} requests")
    print(f"  Success    : {len(success)}/{n}")
    print(f"  Failed     : {len(failed)}")
    print(f"  Total time : {total}s")
    if latencies:
        print(f"  Avg latency: {round(statistics.mean(latencies), 2)}s")
        print(f"  Spread     : {round(max(latencies)-min(latencies), 2)}s")
        print(f"  Throughput : {round(len(success)/total, 2)} req/s")
    return results

async def main():
    print("=" * 55)
    print("Ambient Stress Test — Week 19 Infra Loop")
    print("=" * 55)

    all_results = []
    async with aiohttp.ClientSession() as session:
        # Wave 1: Baseline
        r1 = await run_wave(session, 10, "Wave 1 — Baseline")
        all_results.extend(r1)
        await asyncio.sleep(5)

        # Wave 2: Medium sustained
        r2 = await run_wave(session, 25, "Wave 2 — Medium sustained")
        all_results.extend(r2)
        await asyncio.sleep(5)

        # Wave 3: Heavy burst
        r3 = await run_wave(session, 50, "Wave 3 — Heavy burst")
        all_results.extend(r3)
        await asyncio.sleep(10)

        # Wave 4: Recovery check
        r4 = await run_wave(session, 10, "Wave 4 — Recovery check")
        all_results.extend(r4)

    print("\n" + "=" * 55)
    print("OVERALL SUMMARY")
    print("=" * 55)
    total_ok = [r for r in all_results if r["status"] == 200 and r["ok"]]
    total_failed = [r for r in all_results if not (r["status"] == 200 and r["ok"])]
    all_latencies = [r["latency"] for r in total_ok]
    print(f"Total requests : {len(all_results)}")
    print(f"Total success  : {len(total_ok)}")
    print(f"Total failed   : {len(total_failed)}")
    print(f"Overall rate   : {round(len(total_ok)/len(all_results)*100, 1)}%")
    if all_latencies:
        print(f"Overall avg lat: {round(statistics.mean(all_latencies), 2)}s")

    with open("stress_results.json", "w") as f:
        json.dump(all_results, f, indent=2)
    print("Saved to stress_results.json")

asyncio.run(main())

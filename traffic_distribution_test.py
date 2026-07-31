import asyncio
import aiohttp
import time
import statistics
import json

API_KEY = "dKVk85DEx9QXUfK17ZSSpnPBAVurorCOAjz9cPCMg6PCY6FqEY"
API_URL = "https://api.ambient.xyz/v1/chat/completions"

MODELS = [
    "moonshotai/kimi-k2.7-code",
    "moonshotai/kimi-k2.7-code",
    "moonshotai/kimi-k2.7-code",
]

async def send(session, model, prompt, req_id):
    start = time.time()
    try:
        async with session.post(
            API_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 100},
            timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            latency = round(time.time() - start, 2)
            data = await resp.json()
            if resp.status == 429:
                return {"id": req_id, "model": model, "status": 429, "latency": latency, "error": "RATE_LIMITED"}
            content = data.get("choices", [{}])[0].get("message", {}).get("content") or \
                      data.get("choices", [{}])[0].get("message", {}).get("reasoning_content") or ""
            return {"id": req_id, "model": model, "status": resp.status, "latency": latency, "ok": len(content) > 5}
    except asyncio.TimeoutError:
        return {"id": req_id, "model": model, "status": 0, "latency": 30, "error": "TIMEOUT"}
    except Exception as e:
        return {"id": req_id, "model": model, "status": 0, "latency": round(time.time()-start, 2), "error": str(e)[:30]}

async def burst_test(session, n, model, label):
    print(f"\n{label}: {n} requests → {model}")
    start = time.time()
    results = await asyncio.gather(*[send(session, model, "What is 2+2?", i) for i in range(n)])
    total = round(time.time()-start, 2)
    ok = [r for r in results if r.get("ok")]
    rate_limited = [r for r in results if r.get("status") == 429]
    timeout = [r for r in results if r.get("error") == "TIMEOUT"]
    failed = [r for r in results if not r.get("ok") and r.get("status") != 429]
    lats = [r["latency"] for r in ok]
    print(f"  Success      : {len(ok)}/{n}")
    print(f"  Rate limited : {len(rate_limited)}")
    print(f"  Timeout      : {len(timeout)}")
    print(f"  Other failed : {len(failed)}")
    print(f"  Total time   : {total}s")
    if lats:
        print(f"  Avg latency  : {round(statistics.mean(lats), 2)}s")
    return results

async def failover_test(session):
    print("\nFailover Test — try failed model then fallback")
    results = []
    for model in MODELS:
        r = await send(session, model, "What is 2+2?", 0)
        status = "OK" if r.get("ok") else f"FAIL({r.get('status', r.get('error', ''))})"
        print(f"  {model}: {r['latency']}s | {status}")
        results.append({"model": model, "ok": r.get("ok", False), "latency": r["latency"]})
        if r.get("ok"):
            print(f"  → Serving with {model}")
            break
        await asyncio.sleep(2)
    return results

async def main():
    print("=" * 55)
    print("Ambient Traffic Distribution — Week 21 Infra")
    print("=" * 55)

    all_results = []
    async with aiohttp.ClientSession() as session:
        # Test 1: Burst on working model
        r1 = await burst_test(session, 20, "moonshotai/kimi-k2.7-code", "Burst test")
        all_results.extend(r1)
        await asyncio.sleep(5)

        # Test 2: Recovery after burst
        r2 = await burst_test(session, 10, "moonshotai/kimi-k2.7-code", "Recovery check")
        all_results.extend(r2)
        await asyncio.sleep(5)

        # Test 3: Failover across models
        r3 = await failover_test(session)

    print("\n" + "=" * 55)
    print("OVERALL SUMMARY")
    print("=" * 55)
    ok_all = [r for r in all_results if r.get("ok")]
    rl_all = [r for r in all_results if r.get("status") == 429]
    print(f"Total requests : {len(all_results)}")
    print(f"Success        : {len(ok_all)}/{len(all_results)}")
    print(f"Rate limited   : {len(rl_all)}")

    with open("traffic_results.json", "w") as f:
        json.dump(all_results, f, indent=2)
    print("Saved to traffic_results.json")

asyncio.run(main())

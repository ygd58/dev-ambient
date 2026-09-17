import asyncio
import aiohttp
import time
import statistics
import json

API_KEY = "dKVk85DEx9QXUfK17ZSSpnPBAVurorCOAjz9cPCMg6PCY6FqEY"
API_URL = "https://api.ambient.xyz/v1/chat/completions"
MODEL = "ambient/large"

async def send(session, prompt, max_tokens, req_id):
    start = time.time()
    try:
        async with session.post(
            API_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={"model": MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens},
            timeout=aiohttp.ClientTimeout(total=60)
        ) as resp:
            latency = round(time.time() - start, 2)
            data = await resp.json()
            msg = data.get("choices", [{}])[0].get("message", {})
            content = msg.get("content") or msg.get("reasoning") or ""
            error_type = data.get("error", {}).get("type", "")
            return {
                "id": req_id,
                "status": resp.status,
                "latency": latency,
                "ok": len(content.strip()) > 5,
                "error": error_type
            }
    except asyncio.TimeoutError:
        return {"id": req_id, "status": 0, "latency": 60, "ok": False, "error": "TIMEOUT"}
    except Exception as e:
        return {"id": req_id, "status": 0, "latency": round(time.time()-start, 2), "ok": False, "error": str(e)[:30]}

async def measure_period(session, n, label, prompt="What is 2+2?", tokens=50):
    start = time.time()
    results = await asyncio.gather(*[send(session, prompt, tokens, i) for i in range(n)])
    total = round(time.time()-start, 2)
    ok = [r for r in results if r["ok"]]
    failed = [r for r in results if not r["ok"]]
    lats = [r["latency"] for r in ok]
    errors = {}
    for r in failed:
        e = r.get("error", "unknown")
        errors[e] = errors.get(e, 0) + 1
    
    result = {
        "label": label,
        "total_requests": n,
        "success": len(ok),
        "failed": len(failed),
        "success_rate": round(len(ok)/n*100, 1),
        "total_time": total,
        "avg_latency": round(statistics.mean(lats), 2) if lats else None,
        "p95_latency": round(sorted(lats)[int(len(lats)*0.95)] if len(lats) >= 20 else max(lats) if lats else 0, 2),
        "spread": round(max(lats)-min(lats), 2) if lats else None,
        "errors": errors
    }
    
    print(f"\n{label}: {n} requests")
    print(f"  Success rate : {result['success_rate']}% ({len(ok)}/{n})")
    print(f"  Total time   : {total}s")
    print(f"  Avg latency  : {result['avg_latency']}s")
    if len(lats) >= 20:
        print(f"  P95 latency  : {result['p95_latency']}s")
    print(f"  Spread       : {result['spread']}s")
    if errors:
        print(f"  Errors       : {errors}")
    
    return result

async def main():
    print("=" * 55)
    print("Ambient Capacity Under Load — Week 25 Infra")
    print(f"Model: {MODEL}")
    print("=" * 55)

    all_results = []
    async with aiohttp.ClientSession() as session:
        # Quiet period
        r1 = await measure_period(session, 5, "Quiet period")
        all_results.append(r1)
        await asyncio.sleep(5)

        # Normal traffic
        r2 = await measure_period(session, 20, "Normal traffic")
        all_results.append(r2)
        await asyncio.sleep(5)

        # Busy period
        r3 = await measure_period(session, 100, "Busy period")
        all_results.append(r3)
        await asyncio.sleep(5)

        # Post-burst recovery
        r4 = await measure_period(session, 5, "Recovery")
        all_results.append(r4)
        await asyncio.sleep(5)

        # Sudden spike after quiet
        print("\nWaiting 10s to simulate quiet period...")
        await asyncio.sleep(10)
        r5 = await measure_period(session, 50, "Sudden spike after quiet")
        all_results.append(r5)

    print("\n" + "=" * 55)
    print("CAPACITY COMPARISON")
    print("=" * 55)
    for r in all_results:
        print(f"{r['label']:30} | {r['success_rate']}% | Avg: {r['avg_latency']}s")

    with open("capacity_results.json", "w") as f:
        json.dump(all_results, f, indent=2)
    print("\nSaved to capacity_results.json")

asyncio.run(main())

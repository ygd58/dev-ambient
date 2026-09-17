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
            timeout=aiohttp.ClientTimeout(total=45)
        ) as resp:
            latency = round(time.time() - start, 2)
            data = await resp.json()
            msg = data.get("choices", [{}])[0].get("message", {})
            content = msg.get("content") or msg.get("reasoning") or ""
            return {"id": req_id, "status": resp.status, "latency": latency, "ok": len(content.strip()) > 5, "error": data.get("error", {}).get("type", "")}
    except asyncio.TimeoutError:
        return {"id": req_id, "status": 0, "latency": 45, "ok": False, "error": "TIMEOUT"}
    except Exception as e:
        return {"id": req_id, "status": 0, "latency": round(time.time()-start, 2), "ok": False, "error": str(e)[:30]}

async def run_phase(session, n, label, prompt, max_tokens):
    start = time.time()
    results = await asyncio.gather(*[send(session, prompt, max_tokens, i) for i in range(n)])
    total = round(time.time()-start, 2)
    ok = [r for r in results if r["ok"]]
    failed = [r for r in results if not r["ok"]]
    errors = {}
    for r in failed:
        e = r.get("error", "unknown")
        errors[e] = errors.get(e, 0) + 1
    lats = [r["latency"] for r in ok]
    print(f"\n{label}: {n} requests")
    print(f"  Success  : {len(ok)}/{n}")
    print(f"  Failed   : {len(failed)}")
    if errors:
        print(f"  Errors   : {errors}")
    print(f"  Total    : {total}s")
    if lats:
        print(f"  Avg lat  : {round(statistics.mean(lats), 2)}s")
        print(f"  Max lat  : {max(lats)}s")
        print(f"  Spread   : {round(max(lats)-min(lats), 2)}s")
    return results

async def main():
    print("=" * 55)
    print("Ambient Burst Test — Week 25 Dev Loop")
    print(f"Model: {MODEL}")
    print("=" * 55)

    PROMPT_SHORT = "What is 2+2?"
    PROMPT_MED = "What are the top 3 risks of DeFi?"
    PROMPT_LONG = "Write a Python function for binary search with error handling."

    async with aiohttp.ClientSession() as session:
        # Phase 1: Quiet baseline
        await run_phase(session, 5, "Phase 1 — Quiet baseline", PROMPT_SHORT, 50)
        await asyncio.sleep(5)

        # Phase 2: Sudden burst
        await run_phase(session, 50, "Phase 2 — Sudden burst", PROMPT_SHORT, 50)
        await asyncio.sleep(3)

        # Phase 3: Recovery check
        await run_phase(session, 5, "Phase 3 — Recovery", PROMPT_SHORT, 50)
        await asyncio.sleep(5)

        # Phase 4: Mixed workload burst
        tasks = []
        for i in range(10):
            tasks.append(send(session, PROMPT_SHORT, 50, f"s{i}"))
        for i in range(10):
            tasks.append(send(session, PROMPT_MED, 200, f"m{i}"))
        for i in range(5):
            tasks.append(send(session, PROMPT_LONG, 400, f"l{i}"))
        start = time.time()
        mixed = await asyncio.gather(*tasks)
        total = round(time.time()-start, 2)
        ok = [r for r in mixed if r["ok"]]
        print(f"\nPhase 4 — Mixed burst (25 total)")
        print(f"  Success  : {len(ok)}/25 | Total: {total}s")

    print("\nDone.")

asyncio.run(main())

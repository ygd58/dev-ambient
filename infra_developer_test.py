import asyncio
import aiohttp
import time
import statistics
import json

API_KEY = "dKVk85DEx9QXUfK17ZSSpnPBAVurorCOAjz9cPCMg6PCY6FqEY"
API_URL = "https://api.ambient.xyz/v1/chat/completions"
MODEL = "ambient/large"

async def send(session, prompt, max_tokens=200, label=""):
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
            return {"label": label, "status": resp.status, "latency": latency, "ok": len(content.strip()) > 5}
    except asyncio.TimeoutError:
        return {"label": label, "status": 0, "latency": 45, "ok": False, "error": "TIMEOUT"}
    except Exception as e:
        return {"label": label, "status": 0, "latency": round(time.time()-start, 2), "ok": False, "error": str(e)[:40]}

async def test_retry_behavior(session):
    print("\nTest 1 — Retry behavior under load")
    results = await asyncio.gather(*[send(session, "What is 2+2?", 50, f"req_{i}") for i in range(20)])
    ok = [r for r in results if r["ok"]]
    failed = [r for r in results if not r["ok"]]
    lats = [r["latency"] for r in ok]
    print(f"  Success: {len(ok)}/20 | Failed: {len(failed)}")
    if lats:
        print(f"  Avg: {round(statistics.mean(lats), 2)}s | Max: {max(lats)}s | Spread: {round(max(lats)-min(lats), 2)}s")
    return results

async def test_sustained_traffic(session):
    print("\nTest 2 — Sustained traffic (5 waves of 10)")
    all_ok = 0
    all_total = 0
    wave_lats = []
    for wave in range(1, 6):
        results = await asyncio.gather(*[send(session, "What is the capital of France?", 50, f"w{wave}_r{i}") for i in range(10)])
        ok = [r for r in results if r["ok"]]
        lats = [r["latency"] for r in ok]
        all_ok += len(ok)
        all_total += 10
        if lats:
            wave_lats.append(round(statistics.mean(lats), 2))
        print(f"  Wave {wave}: {len(ok)}/10 | Avg: {round(statistics.mean(lats), 2) if lats else 'N/A'}s")
        await asyncio.sleep(3)
    print(f"  Overall: {all_ok}/{all_total} | Latency trend: {wave_lats}")
    return all_ok, all_total

async def test_routing_stability(session):
    print("\nTest 3 — Routing stability (same prompt, different complexity)")
    tests = [
        ("simple", "What is 2+2?", 50),
        ("medium", "Explain blockchain in 2 sentences.", 150),
        ("complex", "What are the top 5 risks of DeFi protocols? Be specific.", 300),
    ]
    for label, prompt, tokens in tests:
        results = await asyncio.gather(*[send(session, prompt, tokens, label) for _ in range(5)])
        ok = [r for r in results if r["ok"]]
        lats = [r["latency"] for r in ok]
        avg = round(statistics.mean(lats), 2) if lats else "N/A"
        print(f"  {label:10} | {len(ok)}/5 | Avg: {avg}s")
        await asyncio.sleep(2)

async def main():
    print("=" * 55)
    print("Ambient Infra Developer Test — Week 24")
    print(f"Model: {MODEL}")
    print("=" * 55)

    async with aiohttp.ClientSession() as session:
        await test_retry_behavior(session)
        await asyncio.sleep(5)
        await test_sustained_traffic(session)
        await asyncio.sleep(5)
        await test_routing_stability(session)

    print("\nDone.")

asyncio.run(main())

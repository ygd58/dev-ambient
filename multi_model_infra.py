import asyncio
import aiohttp
import time
import statistics
import json

API_KEY = "dKVk85DEx9QXUfK17ZSSpnPBAVurorCOAjz9cPCMg6PCY6FqEY"
API_URL = "https://api.ambient.xyz/v1/chat/completions"

MODELS = [
    "moonshotai/kimi-k2.7-code",
    "deepseek/deepseek-v4-flash-0731",
    "deepseek/deepseek-v4-flash-0731",
    "z-ai/glm-5.2",
]

async def send(session, model, req_id):
    start = time.time()
    try:
        async with session.post(
            API_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={"model": model, "messages": [{"role": "user", "content": "What are the top 3 risks of DeFi lending?"}], "max_tokens": 200},
            timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            latency = round(time.time() - start, 2)
            data = await resp.json()
            msg = data.get("choices", [{}])[0].get("message", {})
            content = msg.get("content") or msg.get("reasoning") or ""
            return {"id": req_id, "model": model.split("/")[-1], "status": resp.status, "latency": latency, "ok": len(content) > 20}
    except Exception as e:
        return {"id": req_id, "model": model.split("/")[-1], "status": 0, "latency": round(time.time()-start, 2), "ok": False}

async def main():
    print("=" * 55)
    print("Ambient Multi-Model Infra Test — Week 22")
    print("=" * 55)

    async with aiohttp.ClientSession() as session:
        print("\nTest 1 — Concurrent requests across 4 models")
        start = time.time()
        results = await asyncio.gather(*[send(session, m, i) for i, m in enumerate(MODELS)])
        total = round(time.time()-start, 2)
        for r in results:
            status = "OK" if r["ok"] else f"FAIL({r['status']})"
            print(f"  {r['model']:25} | {r['latency']}s | {status}")
        print(f"Total time: {total}s")

        await asyncio.sleep(5)

        print("\nTest 2 — 10 concurrent on best model")
        start = time.time()
        results2 = await asyncio.gather(*[send(session, "moonshotai/kimi-k2.7-code", i) for i in range(10)])
        total2 = round(time.time()-start, 2)
        ok2 = [r for r in results2 if r["ok"]]
        lats2 = [r["latency"] for r in ok2]
        avg2 = round(statistics.mean(lats2), 2) if lats2 else "N/A"
        print(f"  Success: {len(ok2)}/10 | Total: {total2}s | Avg: {avg2}s")

        await asyncio.sleep(5)

        print("\nTest 3 — Failover simulation")
        for model in MODELS:
            r = await send(session, model, 0)
            status = "OK" if r["ok"] else f"FAIL({r['status']})"
            print(f"  {r['model']:25} | {status} ({r['latency']}s)")
            if r["ok"]:
                print(f"  Selected: {r['model']}")
                break
            await asyncio.sleep(1)

    print("\nDone.")

asyncio.run(main())

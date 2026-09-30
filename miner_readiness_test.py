import asyncio
import aiohttp
import time
import statistics
import json

API_KEY = "dKVk85DEx9QXUfK17ZSSpnPBAVurorCOAjz9cPCMg6PCY6FqEY"
API_URL = "https://api.ambient.xyz/v1/chat/completions"
MODEL = "ambient/large"

async def send(session, prompt, max_tokens, timeout, label):
    start = time.time()
    try:
        async with session.post(
            API_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={"model": MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens},
            timeout=aiohttp.ClientTimeout(total=timeout)
        ) as resp:
            latency = round(time.time() - start, 2)
            data = await resp.json()
            msg = data.get("choices", [{}])[0].get("message", {})
            content = msg.get("content") or msg.get("reasoning") or ""
            finish = data.get("choices", [{}])[0].get("finish_reason", "")
            req_id = data.get("id", "unknown")
            return {"label": label, "status": resp.status, "latency": latency, "finish": finish, "content_len": len(content.strip()), "req_id": req_id, "ok": len(content.strip()) > 5}
    except asyncio.TimeoutError:
        return {"label": label, "status": 0, "latency": timeout, "finish": "CLIENT_TIMEOUT", "content_len": 0, "req_id": "", "ok": False}
    except Exception as e:
        return {"label": label, "status": 0, "latency": round(time.time()-start, 2), "finish": f"ERROR:{str(e)[:20]}", "content_len": 0, "req_id": "", "ok": False}

async def main():
    print("=" * 55)
    print("Miner Readiness Test — Week 27 Infra Loop")
    print("=" * 55)

    results = []
    async with aiohttp.ClientSession() as session:

        # Test 1: Normal operation baseline
        print("\nTest 1 — Normal operation (5 requests)")
        for i in range(5):
            r = await send(session, "What is 2+2?", 200, 30, f"normal_{i}")
            results.append(r)
            print(f"  {r['label']}: {r['latency']}s | {r['finish']} | ok:{r['ok']}")
            await asyncio.sleep(2)

        # Test 2: Slow miner simulation (very short timeout)
        print("\nTest 2 — Slow miner simulation (2s timeout)")
        for i in range(5):
            r = await send(session, "What are the top 3 risks of DeFi lending?", 300, 2, f"slow_{i}")
            results.append(r)
            print(f"  {r['label']}: {r['latency']}s | {r['finish']} | ok:{r['ok']}")
            await asyncio.sleep(1)

        # Test 3: Recovery after slow period
        print("\nTest 3 — Recovery after slow period")
        await asyncio.sleep(5)
        for i in range(5):
            r = await send(session, "What is 2+2?", 200, 30, f"recovery_{i}")
            results.append(r)
            print(f"  {r['label']}: {r['latency']}s | {r['finish']} | ok:{r['ok']}")
            await asyncio.sleep(2)

        # Test 4: Interrupted inference (disconnect mid-job)
        print("\nTest 4 — Interrupted inference (1s timeout on complex task)")
        for i in range(3):
            r = await send(session, "Write a complete Python implementation of a binary search tree with insert, delete, search, and traversal methods.", 1000, 1, f"interrupted_{i}")
            results.append(r)
            print(f"  {r['label']}: {r['latency']}s | {r['finish']} | ok:{r['ok']}")
            await asyncio.sleep(2)

    print("\n" + "=" * 55)
    print("MINER READINESS SUMMARY")
    print("=" * 55)
    for phase in ["normal", "slow", "recovery", "interrupted"]:
        phase_results = [r for r in results if r["label"].startswith(phase)]
        ok = [r for r in phase_results if r["ok"]]
        lats = [r["latency"] for r in ok]
        timeouts = [r for r in phase_results if "TIMEOUT" in r["finish"]]
        print(f"{phase:12} | Success: {len(ok)}/{len(phase_results)} | Timeouts: {len(timeouts)} | Avg lat: {round(statistics.mean(lats), 2) if lats else 'N/A'}s")

    with open("miner_readiness_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nSaved to miner_readiness_results.json")

asyncio.run(main())

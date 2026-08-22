import asyncio
import aiohttp
import time
import statistics
import json
import hashlib

API_KEY = "dKVk85DEx9QXUfK17ZSSpnPBAVurorCOAjz9cPCMg6PCY6FqEY"
API_URL = "https://api.ambient.xyz/v1/chat/completions"

MODELS = ["moonshotai/kimi-k2.7-code", "z-ai/glm-5.2", "deepseek/deepseek-v4-flash-0731"]
PROMPT = "What is 12 multiplied by 12? Answer with only the number."
EXPECTED = "144"

async def send(session, model, req_id):
    start = time.time()
    try:
        async with session.post(
            API_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={"model": model, "messages": [{"role": "user", "content": PROMPT}], "max_tokens": 100},
            timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            latency = round(time.time() - start, 2)
            data = await resp.json()
            msg = data.get("choices", [{}])[0].get("message", {})
            content = msg.get("content") or msg.get("reasoning") or ""
            correct = EXPECTED in content
            h = hashlib.md5(content.strip().encode()).hexdigest()[:8]
            return {"id": req_id, "model": model.split("/")[-1], "status": resp.status, "latency": latency, "correct": correct, "hash": h, "ok": len(content.strip()) > 0}
    except Exception as e:
        return {"id": req_id, "model": model.split("/")[-1], "status": 0, "latency": round(time.time()-start, 2), "correct": False, "hash": "", "ok": False}

async def main():
    print("=" * 55)
    print("Ambient Verification Scale Test — Week 23 Infra")
    print("=" * 55)

    all_results = []

    async with aiohttp.ClientSession() as session:
        # Test 1: 10 concurrent on each model
        for model in MODELS:
            short = model.split("/")[-1]
            print(f"\nModel: {short} — 10 concurrent")
            start = time.time()
            results = await asyncio.gather(*[send(session, model, i) for i in range(10)])
            total = round(time.time()-start, 2)
            ok = [r for r in results if r["ok"]]
            correct = [r for r in results if r["correct"]]
            hashes = [r["hash"] for r in ok]
            unique = len(set(hashes))
            lats = [r["latency"] for r in ok]
            print(f"  Success  : {len(ok)}/10")
            print(f"  Correct  : {len(correct)}/10")
            print(f"  Unique h : {unique} (1=identical)")
            if lats:
                print(f"  Avg lat  : {round(statistics.mean(lats), 2)}s")
            print(f"  Total    : {total}s")
            all_results.extend(results)
            await asyncio.sleep(5)

        # Test 2: Mixed model concurrent
        print(f"\nMixed model concurrent (30 total, 10 per model)")
        start = time.time()
        tasks = []
        for i, model in enumerate(MODELS):
            for j in range(10):
                tasks.append(send(session, model, i*10+j))
        mixed = await asyncio.gather(*tasks)
        total = round(time.time()-start, 2)
        ok_mixed = [r for r in mixed if r["ok"]]
        correct_mixed = [r for r in mixed if r["correct"]]
        print(f"  Success  : {len(ok_mixed)}/30")
        print(f"  Correct  : {len(correct_mixed)}/30")
        print(f"  Total    : {total}s")
        all_results.extend(mixed)

    print("\n" + "=" * 55)
    print("OVERALL SUMMARY")
    print("=" * 55)
    ok_all = [r for r in all_results if r["ok"]]
    correct_all = [r for r in all_results if r["correct"]]
    lats_all = [r["latency"] for r in ok_all]
    print(f"Total requests : {len(all_results)}")
    print(f"Success rate   : {len(ok_all)}/{len(all_results)}")
    print(f"Correct rate   : {len(correct_all)}/{len(all_results)}")
    if lats_all:
        print(f"Avg latency    : {round(statistics.mean(lats_all), 2)}s")

    with open("verification_scale_results.json", "w") as f:
        json.dump(all_results, f, indent=2)
    print("Saved to verification_scale_results.json")

asyncio.run(main())

import asyncio
import aiohttp
import time
import statistics
import json

API_KEY = "dKVk85DEx9QXUfK17ZSSpnPBAVurorCOAjz9cPCMg6PCY6FqEY"
API_URL = "https://api.ambient.xyz/v1/chat/completions"

MODELS = {
    "ambient/large": "ambient/large",
    "glm-5.2": "z-ai/glm-5.2",
    "qwen3.6": "qwen/qwen3.6-27b",
    "qwen3.8": "qwen/qwen3.8-27b",
}

async def health_check(session, model_id, model_name, runs=10):
    results = []
    for i in range(runs):
        start = time.time()
        try:
            async with session.post(
                API_URL,
                headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
                json={"model": model_id, "messages": [{"role": "user", "content": "What is 2+2?"}], "max_tokens": 50},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                latency = round(time.time() - start, 2)
                data = await resp.json()
                msg = data.get("choices", [{}])[0].get("message", {})
                content = msg.get("content") or msg.get("reasoning") or ""
                error = data.get("error", {}).get("type", "")
                finish = data.get("choices", [{}])[0].get("finish_reason", "")
                results.append({
                    "run": i,
                    "status": resp.status,
                    "latency": latency,
                    "ok": len(content.strip()) > 0,
                    "finish": finish,
                    "error": error
                })
        except asyncio.TimeoutError:
            results.append({"run": i, "status": 0, "latency": 30, "ok": False, "finish": "", "error": "TIMEOUT"})
        except Exception as e:
            results.append({"run": i, "status": 0, "latency": round(time.time()-start, 2), "ok": False, "finish": "", "error": str(e)[:30]})
        await asyncio.sleep(1)

    ok = [r for r in results if r["ok"]]
    failed = [r for r in results if not r["ok"]]
    lats = [r["latency"] for r in ok]
    errors = {}
    finishes = {}
    for r in results:
        if r.get("error"):
            errors[r["error"]] = errors.get(r["error"], 0) + 1
        if r.get("finish"):
            finishes[r["finish"]] = finishes.get(r["finish"], 0) + 1

    return {
        "model": model_name,
        "success_rate": round(len(ok)/runs*100, 1),
        "ok": len(ok),
        "failed": len(failed),
        "avg_latency": round(statistics.mean(lats), 2) if lats else None,
        "min_latency": min(lats) if lats else None,
        "max_latency": max(lats) if lats else None,
        "errors": errors,
        "finish_reasons": finishes
    }

async def main():
    print("=" * 60)
    print("Ambient Model Health Check — Week 26 Infra Loop")
    print("=" * 60)

    all_results = []
    async with aiohttp.ClientSession() as session:
        for model_name, model_id in MODELS.items():
            print(f"\nChecking: {model_name} (10 runs)")
            result = await health_check(session, model_id, model_name, runs=10)
            all_results.append(result)
            print(f"  Success rate : {result['success_rate']}% ({result['ok']}/10)")
            print(f"  Avg latency  : {result['avg_latency']}s")
            print(f"  Min/Max      : {result['min_latency']}s / {result['max_latency']}s")
            print(f"  Finish reasons: {result['finish_reasons']}")
            if result['errors']:
                print(f"  Errors       : {result['errors']}")
            await asyncio.sleep(5)

    print("\n" + "=" * 60)
    print("HEALTH SUMMARY")
    print("=" * 60)
    for r in all_results:
        print(f"{r['model']:15} | {r['success_rate']}% | Avg: {r['avg_latency']}s | Errors: {r['errors'] or 'none'}")

    with open("model_health_results.json", "w") as f:
        json.dump(all_results, f, indent=2)
    print("\nSaved to model_health_results.json")

asyncio.run(main())

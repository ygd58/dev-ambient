import asyncio
import aiohttp
import time
import json
import statistics
import hashlib

API_KEY = "dKVk85DEx9QXUfK17ZSSpnPBAVurorCOAjz9cPCMg6PCY6FqEY"
API_URL = "https://api.ambient.xyz/v1/chat/completions"

MODELS = {
    "ambient/large": "ambient/large",
    "glm-5.2": "z-ai/glm-5.2",
    "qwen3.6-27b": "qwen/qwen3.6-27b",
    "qwen3.8-27b": "qwen/qwen3.8-27b",
}

TASKS = [
    {"id": "coding", "prompt": "Write a Python function that checks if a number is prime. Include edge cases, docstring, and type hints.", "tokens": 500, "check": "def is_prime"},
    {"id": "math", "prompt": "What is compound interest on $10,000 at 7% annual rate for 10 years compounded monthly? Show formula and result.", "tokens": 300, "check": "20096"},
    {"id": "factual", "prompt": "What is the capital of France? One word only.", "tokens": 20, "check": "paris"},
    {"id": "reasoning", "prompt": "If all validators are honest and quorum is 2/3, is the network Byzantine fault tolerant? Answer YES or NO then explain in one sentence.", "tokens": 100, "check": "yes"},
    {"id": "structured", "prompt": "List the top 3 DeFi risks as JSON array with fields: risk, severity, mitigation.", "tokens": 300, "check": "liquidat"},
]

async def test_model(session, model_id, model_name, task):
    start = time.time()
    try:
        async with session.post(
            API_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={"model": model_id, "messages": [{"role": "user", "content": task["prompt"]}], "max_tokens": task["tokens"]},
            timeout=aiohttp.ClientTimeout(total=60)
        ) as resp:
            latency = round(time.time() - start, 2)
            data = await resp.json()
            msg = data.get("choices", [{}])[0].get("message", {})
            content = msg.get("content") or msg.get("reasoning") or ""
            correct = task["check"].lower() in content.lower()
            return {
                "model": model_name,
                "task": task["id"],
                "status": resp.status,
                "latency": latency,
                "length": len(content),
                "correct": correct,
                "ok": len(content.strip()) > 5
            }
    except Exception as e:
        return {"model": model_name, "task": task["id"], "status": 0, "latency": round(time.time()-start, 2), "length": 0, "correct": False, "ok": False}

async def main():
    print("=" * 65)
    print("Ambient Model Showdown — Week 26")
    print("=" * 65)

    all_results = []

    async with aiohttp.ClientSession() as session:
        for task in TASKS:
            print(f"\nTask: {task['id']}")
            print("-" * 50)
            for model_name, model_id in MODELS.items():
                r = await test_model(session, model_id, model_name, task)
                all_results.append(r)
                status = f"✓ {r['latency']}s {r['length']}c" if r["ok"] and r["correct"] else f"{'ok' if r['ok'] else 'FAIL'} {r['latency']}s"
                print(f"  {model_name:15} | {status}")
                await asyncio.sleep(2)
            await asyncio.sleep(3)

    print("\n" + "=" * 65)
    print("MODEL SUMMARY")
    print("=" * 65)
    for model_name in MODELS.keys():
        results = [r for r in all_results if r["model"] == model_name]
        ok = [r for r in results if r["ok"]]
        correct = [r for r in results if r["correct"]]
        lats = [r["latency"] for r in ok]
        avg_lat = round(statistics.mean(lats), 2) if lats else "N/A"
        avg_len = round(statistics.mean([r["length"] for r in ok])) if ok else 0
        print(f"{model_name:15} | Success: {len(ok)}/{len(TASKS)} | Correct: {len(correct)}/{len(TASKS)} | Avg: {avg_lat}s | Avg len: {avg_len}c")

    with open("showdown_results.json", "w") as f:
        json.dump(all_results, f, indent=2)
    print("\nSaved to showdown_results.json")

asyncio.run(main())

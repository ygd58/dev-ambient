import asyncio
import aiohttp
import time
import statistics
import json

API_KEY = "dKVk85DEx9QXUfK17ZSSpnPBAVurorCOAjz9cPCMg6PCY6FqEY"
API_URL = "https://api.ambient.xyz/v1/chat/completions"
MODEL = "ambient/large"

STABLE_PREFIX = "You are a helpful AI assistant specializing in blockchain, DeFi, and smart contract analysis. Always be concise and accurate."

TASKS = [
    {"id": "coding", "prompt": "Write a Python function that checks if a number is prime.", "tokens": 400, "check": "def is_prime"},
    {"id": "math", "prompt": "What is compound interest on $10,000 at 7% for 10 years monthly?", "tokens": 200, "check": "20096"},
    {"id": "factual", "prompt": "What is the capital of France?", "tokens": 50, "check": "paris"},
    {"id": "reasoning", "prompt": "Is Byzantine fault tolerance possible with 2/3 honest validators? YES or NO then one sentence.", "tokens": 100, "check": "yes"},
]

async def send(session, messages, tokens, label):
    start = time.time()
    try:
        async with session.post(
            API_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={"model": MODEL, "messages": messages, "max_tokens": tokens},
            timeout=aiohttp.ClientTimeout(total=45)
        ) as resp:
            latency = round(time.time() - start, 2)
            data = await resp.json()
            msg = data.get("choices", [{}])[0].get("message", {})
            content = msg.get("content") or msg.get("reasoning") or ""
            return {"label": label, "status": resp.status, "latency": latency, "content": content, "ok": len(content.strip()) > 5}
    except Exception as e:
        return {"label": label, "status": 0, "latency": round(time.time()-start, 2), "content": "", "ok": False}

async def run_benchmark(session, use_prefix, label):
    print(f"\n{'='*40}")
    print(f"{label}")
    print(f"{'='*40}")
    results = []
    for task in TASKS:
        if use_prefix:
            messages = [
                {"role": "system", "content": STABLE_PREFIX},
                {"role": "user", "content": task["prompt"]}
            ]
        else:
            messages = [{"role": "user", "content": task["prompt"]}]
        
        r = await send(session, messages, task["tokens"], task["id"])
        correct = task["check"].lower() in r["content"].lower()
        results.append({**r, "correct": correct})
        print(f"  {task['id']:12} | {r['latency']}s | correct:{correct}")
        await asyncio.sleep(2)
    
    ok = [r for r in results if r["ok"]]
    lats = [r["latency"] for r in ok]
    correct = [r for r in results if r.get("correct")]
    print(f"\nSummary: {len(ok)}/{len(TASKS)} success | {len(correct)}/{len(TASKS)} correct | Avg: {round(statistics.mean(lats), 2) if lats else 'N/A'}s")
    return results

async def main():
    print("=" * 55)
    print("Cache Prefix Test — Week 26 Dev Loop")
    print(f"Model: {MODEL}")
    print("=" * 55)

    async with aiohttp.ClientSession() as session:
        # Round 1: No prefix (cold)
        r1 = await run_benchmark(session, False, "Round 1 — No prefix (cold)")
        await asyncio.sleep(5)

        # Round 2: With stable prefix (first pass)
        r2 = await run_benchmark(session, True, "Round 2 — Stable prefix (first pass)")
        await asyncio.sleep(3)

        # Round 3: With stable prefix (cached)
        r3 = await run_benchmark(session, True, "Round 3 — Stable prefix (should be cached)")

    print("\n" + "=" * 55)
    print("CACHE EFFECT COMPARISON")
    print("=" * 55)
    
    def avg_lat(results):
        ok = [r for r in results if r["ok"]]
        lats = [r["latency"] for r in ok]
        return round(statistics.mean(lats), 2) if lats else None

    a1, a2, a3 = avg_lat(r1), avg_lat(r2), avg_lat(r3)
    print(f"No prefix      : {a1}s avg")
    print(f"Prefix round 1 : {a2}s avg")
    print(f"Prefix round 2 : {a3}s avg (cache expected)")
    if a2 and a3:
        improvement = round((a2-a3)/a2*100, 1)
        print(f"Cache improvement: {improvement}%")

    with open("cache_prefix_results.json", "w") as f:
        json.dump({"no_prefix": r1, "prefix_r1": r2, "prefix_r2": r3}, f, indent=2)
    print("Saved to cache_prefix_results.json")

asyncio.run(main())

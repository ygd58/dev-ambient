import asyncio
import aiohttp
import time
import json
import statistics
import hashlib

API_KEY = "dKVk85DEx9QXUfK17ZSSpnPBAVurorCOAjz9cPCMg6PCY6FqEY"
API_URL = "https://api.ambient.xyz/v1/chat/completions"
MODEL = "moonshotai/kimi-k2.7-code"

DETERMINISTIC_PROMPTS = [
    {
        "id": "math",
        "prompt": "What is compound interest on $10,000 at 7% annual rate for 10 years compounded monthly? Give only the final dollar amount.",
        "expected": "20096"
    },
    {
        "id": "logic",
        "prompt": "If A implies B, and B implies C, does A imply C? Answer only YES or NO.",
        "expected": "yes"
    },
    {
        "id": "factual",
        "prompt": "What is the square root of 144? Give only the number.",
        "expected": "12"
    },
]

async def run_once(session, prompt, req_id):
    start = time.time()
    try:
        async with session.post(
            API_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={"model": MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": 500},
            timeout=aiohttp.ClientTimeout(total=45)
        ) as resp:
            latency = round(time.time() - start, 2)
            data = await resp.json()
            msg = data.get("choices", [{}])[0].get("message", {})
            content = msg.get("content") or msg.get("reasoning") or ""
            content_hash = hashlib.md5(content.strip().encode()).hexdigest()[:8]
            return {"id": req_id, "status": resp.status, "latency": latency, "content": content, "hash": content_hash, "ok": len(content.strip()) > 0}
    except Exception as e:
        return {"id": req_id, "status": 0, "latency": round(time.time()-start, 2), "content": "", "hash": "", "ok": False}

async def verify_prompt(session, task, runs=5):
    print(f"\nTask: {task['id']} ({runs} runs)")
    results = []
    for i in range(runs):
        r = await run_once(session, task["prompt"], i)
        results.append(r)
        correct = task["expected"].lower() in r["content"].lower()
        print(f"  Run {i+1}: {r['latency']}s | hash:{r['hash']} | correct:{correct}")
        await asyncio.sleep(2)

    ok = [r for r in results if r["ok"]]
    hashes = [r["hash"] for r in ok]
    correct = [r for r in ok if task["expected"].lower() in r["content"].lower()]
    unique_hashes = len(set(hashes))
    lats = [r["latency"] for r in ok]

    print(f"  Success     : {len(ok)}/{runs}")
    print(f"  Correct     : {len(correct)}/{runs}")
    print(f"  Unique hashes: {unique_hashes} (1=identical outputs, {runs}=all different)")
    print(f"  Avg latency : {round(statistics.mean(lats), 2)}s" if lats else "  No latency data")
    return {
        "task": task["id"],
        "runs": runs,
        "success": len(ok),
        "correct": len(correct),
        "unique_hashes": unique_hashes,
        "consistency": "HIGH" if unique_hashes <= 2 else "MEDIUM" if unique_hashes <= 3 else "LOW"
    }

async def main():
    print("=" * 55)
    print("Ambient Verification Test — Week 23")
    print(f"Model: {MODEL}")
    print("=" * 55)

    summaries = []
    async with aiohttp.ClientSession() as session:
        for task in DETERMINISTIC_PROMPTS:
            summary = await verify_prompt(session, task, runs=5)
            summaries.append(summary)
            await asyncio.sleep(5)

    print("\n" + "=" * 55)
    print("VERIFICATION SUMMARY")
    print("=" * 55)
    for s in summaries:
        print(f"{s['task']:10} | Correct: {s['correct']}/5 | Consistency: {s['consistency']} | Unique outputs: {s['unique_hashes']}")

    with open("verification_results.json", "w") as f:
        json.dump(summaries, f, indent=2)
    print("\nSaved to verification_results.json")

asyncio.run(main())

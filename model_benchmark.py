import asyncio
import aiohttp
import time
import json
import statistics

API_KEY = "dKVk85DEx9QXUfK17ZSSpnPBAVurorCOAjz9cPCMg6PCY6FqEY"
API_URL = "https://api.ambient.xyz/v1/chat/completions"

MODELS = [
    "moonshotai/kimi-k2.7-code",
    "deepseek/deepseek-v4-flash-0731",
    "deepseek/deepseek-v4-flash-0731",
    "z-ai/glm-5.2",
]

TASKS = [
    ("reasoning", "If all validators are honest and quorum is 2/3, is the network Byzantine fault tolerant? Explain in 2 sentences."),
    ("coding", "Write a Python function that calculates compound interest. Include parameters for principal, rate, time, and compounding frequency."),
    ("research", "What are the top 3 risks of DeFi lending protocols? Be specific."),
    ("creative", "Explain blockchain to a 10-year-old in 3 sentences."),
    ("math", "What is compound interest on $10,000 at 7% annual rate for 10 years compounded monthly? Show the formula and result."),
]

async def test_model(session, model, task_name, prompt):
    start = time.time()
    try:
        async with session.post(
            API_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 500},
            timeout=aiohttp.ClientTimeout(total=45)
        ) as resp:
            latency = round(time.time() - start, 2)
            data = await resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content") or \
                      data.get("choices", [{}])[0].get("message", {}).get("reasoning_content") or ""
            return {
                "model": model,
                "task": task_name,
                "status": resp.status,
                "latency": latency,
                "length": len(content),
                "ok": len(content) > 30,
                "preview": content[:100]
            }
    except Exception as e:
        return {"model": model, "task": task_name, "status": 0, "latency": round(time.time()-start, 2), "length": 0, "ok": False, "error": str(e)[:40]}

async def main():
    print("=" * 65)
    print("Ambient Model Benchmark — Week 22")
    print("=" * 65)

    all_results = []

    async with aiohttp.ClientSession() as session:
        for task_name, prompt in TASKS:
            print(f"\nTask: {task_name}")
            print("-" * 45)
            task_results = []
            for model in MODELS:
                r = await test_model(session, model, task_name, prompt)
                task_results.append(r)
                all_results.append(r)
                status = f"OK ({r['latency']}s, {r['length']} chars)" if r["ok"] else f"FAIL ({r.get('status', 'ERR')})"
                short_model = model.split("/")[-1]
                print(f"  {short_model:25} | {status}")
                await asyncio.sleep(2)
            await asyncio.sleep(3)

    print("\n" + "=" * 65)
    print("MODEL SUMMARY")
    print("=" * 65)
    for model in MODELS:
        model_results = [r for r in all_results if r["model"] == model]
        ok = [r for r in model_results if r["ok"]]
        lats = [r["latency"] for r in ok]
        short = model.split("/")[-1]
        if ok:
            print(f"{short:25} | Success: {len(ok)}/{len(TASKS)} | Avg: {round(statistics.mean(lats), 2)}s | Avg len: {round(statistics.mean([r['length'] for r in ok]))}")
        else:
            print(f"{short:25} | Success: 0/{len(TASKS)} | All failed")

    with open("model_benchmark_results.json", "w") as f:
        json.dump(all_results, f, indent=2)
    print("\nSaved to model_benchmark_results.json")

asyncio.run(main())

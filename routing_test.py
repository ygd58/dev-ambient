import asyncio
import aiohttp
import time
import statistics
import json

API_KEY = "dKVk85DEx9QXUfK17ZSSpnPBAVurorCOAjz9cPCMg6PCY6FqEY"
API_URL = "https://api.ambient.xyz/v1/chat/completions"
MODEL = "moonshotai/kimi-k2.7-code"

PROMPT_CATEGORIES = [
    ("simple_math", "What is 2+2?", 50),
    ("simple_factual", "What is Bitcoin?", 100),
    ("medium_analysis", "What are the top 3 risks of DeFi lending?", 200),
    ("complex_research", "Analyze the complete risk profile of a $100M TVL DeFi protocol with volatile collateral, cross-chain bridges, and a 6-month governance token.", 400),
    ("code_generation", "Write a Python function that calculates compound interest with principal, rate, time, and compounding frequency as parameters.", 300),
    ("long_context", "You are analyzing a DeFi protocol. Context: $50M TVL, ETH collateral, Chainlink oracles, 48hr governance timelock, $2M bug bounty, audited by Trail of Bits. Question: Is this protocol safe to deposit $100K into?", 300),
]

async def send(session, prompt, max_tokens, label, run_num):
    start = time.time()
    try:
        async with session.post(
            API_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={"model": MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens},
            timeout=aiohttp.ClientTimeout(total=60)
        ) as resp:
            latency = round(time.time() - start, 2)
            data = await resp.json()
            content = data["choices"][0]["message"].get("content") or data["choices"][0]["message"].get("reasoning_content") or ""
            return {"label": label, "run": run_num, "status": resp.status, "latency": latency, "len": len(content), "ok": len(content) > 5}
    except Exception as e:
        return {"label": label, "run": run_num, "status": 0, "latency": round(time.time()-start, 2), "len": 0, "ok": False}

async def main():
    print("=" * 60)
    print("Ambient Routing Intelligence Test — Week 21 Dev Loop")
    print("=" * 60)

    all_results = []
    RUNS = 3

    async with aiohttp.ClientSession() as session:
        for label, prompt, max_tokens in PROMPT_CATEGORIES:
            print(f"\nCategory: {label}")
            cat_results = []
            for run in range(1, RUNS + 1):
                r = await send(session, prompt, max_tokens, label, run)
                cat_results.append(r)
                all_results.append(r)
                print(f"  Run {run}: {r['latency']}s | {'OK' if r['ok'] else 'FAIL'}")
                await asyncio.sleep(3)

            ok = [r for r in cat_results if r["ok"]]
            if ok:
                lats = [r["latency"] for r in ok]
                print(f"  Avg: {round(statistics.mean(lats), 2)}s | Spread: {round(max(lats)-min(lats), 2)}s | Success: {len(ok)}/{RUNS}")
            await asyncio.sleep(5)

    print("\n" + "=" * 60)
    print("ROUTING SUMMARY BY CATEGORY")
    print("=" * 60)
    for label, _, _ in PROMPT_CATEGORIES:
        cat = [r for r in all_results if r["label"] == label and r["ok"]]
        if cat:
            lats = [r["latency"] for r in cat]
            print(f"{label:20} | Avg: {round(statistics.mean(lats), 2):6}s | Spread: {round(max(lats)-min(lats), 2):5}s | {len(cat)}/{RUNS}")

    with open("routing_results.json", "w") as f:
        json.dump(all_results, f, indent=2)
    print("\nSaved to routing_results.json")

asyncio.run(main())

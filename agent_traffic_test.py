import asyncio
import aiohttp
import time
import statistics
import json

API_KEY = "dKVk85DEx9QXUfK17ZSSpnPBAVurorCOAjz9cPCMg6PCY6FqEY"
API_URL = "https://api.ambient.xyz/v1/chat/completions"
MODEL = "zai-org/GLM-5.1-FP8"

async def send(session, messages, max_tokens=200, label=""):
    start = time.time()
    try:
        async with session.post(
            API_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={"model": MODEL, "messages": messages, "max_tokens": max_tokens},
            timeout=aiohttp.ClientTimeout(total=45)
        ) as resp:
            latency = round(time.time() - start, 2)
            data = await resp.json()
            content = data["choices"][0]["message"].get("reasoning_content") or data["choices"][0]["message"].get("content") or ""
            return {"label": label, "status": resp.status, "latency": latency, "len": len(content), "ok": len(content) > 20}
    except Exception as e:
        return {"label": label, "status": 0, "latency": round(time.time()-start, 2), "len": 0, "ok": False, "error": str(e)[:40]}

async def simulate_agent(session, agent_id):
    steps = [
        [{"role": "user", "content": "You are a DeFi research agent. What is liquidation risk?"}],
        [{"role": "user", "content": "You are a DeFi research agent. What is liquidation risk?"}, 
         {"role": "assistant", "content": "Liquidation risk is when collateral value drops below threshold."},
         {"role": "user", "content": "Based on that, what is the safest collateral to use?"}],
        [{"role": "user", "content": "You are a DeFi research agent. What is liquidation risk?"},
         {"role": "assistant", "content": "Liquidation risk is when collateral value drops below threshold."},
         {"role": "user", "content": "Based on that, what is the safest collateral to use?"},
         {"role": "assistant", "content": "Stablecoins are the safest collateral."},
         {"role": "user", "content": "Give a final 2-sentence recommendation for a $50K DeFi allocation."}],
    ]
    results = []
    for i, messages in enumerate(steps):
        r = await send(session, messages, label=f"agent_{agent_id}_step_{i+1}")
        results.append(r)
        await asyncio.sleep(2)
    return results

async def main():
    print("=" * 55)
    print("Ambient Agent Traffic Test — Week 20 Infra")
    print("=" * 55)

    async with aiohttp.ClientSession() as session:
        # Test 1: Sequential agent (3 steps)
        print("\nTest 1 — Sequential 3-step agent")
        start = time.time()
        r1 = await simulate_agent(session, 1)
        t1 = round(time.time()-start, 2)
        ok1 = [r for r in r1 if r["ok"]]
        print(f"Steps: {len(ok1)}/{len(r1)} | Total: {t1}s | Avg: {round(statistics.mean([r['latency'] for r in ok1]), 2)}s" if ok1 else "All failed")

        await asyncio.sleep(5)

        # Test 2: 3 concurrent agents
        print("\nTest 2 — 3 concurrent agents (3 steps each)")
        start = time.time()
        r2 = await asyncio.gather(*[simulate_agent(session, i) for i in range(3)])
        t2 = round(time.time()-start, 2)
        all_r2 = [r for agent in r2 for r in agent]
        ok2 = [r for r in all_r2 if r["ok"]]
        print(f"Steps: {len(ok2)}/{len(all_r2)} | Total: {t2}s")

        await asyncio.sleep(5)

        # Test 3: Long context (growing message chain)
        print("\nTest 3 — Long context growth")
        messages = []
        lc_results = []
        topics = ["liquidation risk", "oracle manipulation", "smart contract risk", "governance risk", "bridge risk"]
        for topic in topics:
            messages.append({"role": "user", "content": f"In one sentence, what is {topic} in DeFi?"})
            r = await send(session, messages, label=f"long_context_{len(messages)}")
            if r["ok"]:
                messages.append({"role": "assistant", "content": f"Brief answer about {topic}."})
            lc_results.append(r)
            print(f"  Turn {len(lc_results)} ({len(messages)} msgs): {r['latency']}s | {'OK' if r['ok'] else 'FAIL'}")
            await asyncio.sleep(2)

    print("\n" + "=" * 55)
    print("SUMMARY")
    print("=" * 55)
    all_results = r1 + all_r2 + lc_results
    ok_all = [r for r in all_results if r["ok"]]
    lats = [r["latency"] for r in ok_all]
    print(f"Total requests : {len(all_results)}")
    print(f"Success        : {len(ok_all)}/{len(all_results)}")
    if lats:
        print(f"Avg latency    : {round(statistics.mean(lats), 2)}s")
        print(f"Max latency    : {max(lats)}s")

    with open("agent_traffic_results.json", "w") as f:
        json.dump(all_results, f, indent=2)
    print("Saved to agent_traffic_results.json")

asyncio.run(main())

import asyncio
import aiohttp
import time
import statistics

API_KEY = "dKVk85DEx9QXUfK17ZSSpnPBAVurorCOAjz9cPCMg6PCY6FqEY"
API_URL = "https://api.ambient.xyz/v1/chat/completions"
MODEL = "zai-org/GLM-5.1-FP8"

SHARED_CONTEXT = """You are analyzing a DeFi protocol with the following characteristics:
- Total Value Locked: $50M
- Collateral: ETH, BTC, and USDC
- Cross-chain bridges to Ethereum, Arbitrum, and Optimism
- Governance token launched 6 months ago
- 3 independent security audits completed
- Bug bounty program with $2M maximum payout"""

QUERIES = [
    "What is the biggest risk?",
    "What is the liquidity risk score?",
    "What governance improvements would you recommend?",
    "Is this protocol safe to deposit into?",
]

async def send(session, prompt, label):
    start = time.time()
    try:
        async with session.post(
            API_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": f"{SHARED_CONTEXT}\n\n{prompt}"}],
                "max_tokens": 150
            },
            timeout=aiohttp.ClientTimeout(total=45)
        ) as resp:
            latency = round(time.time() - start, 2)
            data = await resp.json()
            content = data["choices"][0]["message"].get("reasoning_content") or data["choices"][0]["message"].get("content") or ""
            return {"label": label, "status": resp.status, "latency": latency, "len": len(content)}
    except Exception as e:
        return {"label": label, "status": 0, "latency": round(time.time()-start, 2), "error": str(e)}

async def run_round(session, label):
    print(f"\n--- {label} ---")
    results = []
    for query in QUERIES:
        result = await send(session, query, query[:30])
        results.append(result)
        print(f"  {result['label']:30} | {result['latency']}s | {result.get('status')}")
        await asyncio.sleep(2)
    return results

async def main():
    print("=" * 55)
    print("Ambient Cache Test — Week 18 Infra Loop")
    print(f"Shared context: {len(SHARED_CONTEXT)} chars")
    print("=" * 55)

    async with aiohttp.ClientSession() as session:
        print("\nRound 1 — Cold (no cache)")
        r1 = await run_round(session, "Round 1 Cold")

        await asyncio.sleep(5)

        print("\nRound 2 — Warm (same context, cache expected)")
        r2 = await run_round(session, "Round 2 Warm")

    print("\n" + "=" * 55)
    print("CACHE PERFORMANCE COMPARISON")
    print("=" * 55)

    r1_ok = [r for r in r1 if r["status"] == 200]
    r2_ok = [r for r in r2 if r["status"] == 200]

    if r1_ok and r2_ok:
        avg1 = round(statistics.mean([r["latency"] for r in r1_ok]), 2)
        avg2 = round(statistics.mean([r["latency"] for r in r2_ok]), 2)
        improvement = round((avg1 - avg2) / avg1 * 100, 1)
        print(f"Round 1 avg latency : {avg1}s")
        print(f"Round 2 avg latency : {avg2}s")
        print(f"Improvement         : {improvement}%")
        print(f"Cache working       : {'YES' if improvement > 5 else 'NOT DETECTED'}")

asyncio.run(main())

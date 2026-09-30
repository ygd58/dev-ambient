import asyncio
import aiohttp
import time
import json

API_KEY = "dKVk85DEx9QXUfK17ZSSpnPBAVurorCOAjz9cPCMg6PCY6FqEY"
API_URL = "https://api.ambient.xyz/v1/chat/completions"
MODEL = "ambient/large"

async def send(session, prompt, max_tokens, label):
    start = time.time()
    try:
        async with session.post(
            API_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={"model": MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens},
            timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            latency = round(time.time() - start, 2)
            data = await resp.json()
            msg = data.get("choices", [{}])[0].get("message", {})
            content = msg.get("content") or ""
            reasoning = msg.get("reasoning") or ""
            finish = data.get("choices", [{}])[0].get("finish_reason", "")
            req_id = data.get("id", "unknown")
            return {
                "label": label,
                "status": resp.status,
                "latency": latency,
                "finish_reason": finish,
                "content_len": len(content.strip()),
                "reasoning_len": len(reasoning.strip()),
                "request_id": req_id,
                "valid": len(content.strip()) > 5 or (finish == "stop")
            }
    except asyncio.TimeoutError:
        return {"label": label, "status": 0, "latency": 30, "finish_reason": "TIMEOUT", "content_len": 0, "reasoning_len": 0, "request_id": "", "valid": False}

async def main():
    print("=" * 55)
    print("Valid Work Test — Week 27 Dev Loop")
    print("=" * 55)

    tests = [
        # Valid work scenarios
        ("correct_512tokens", "Write a Python function that checks if a number is prime with docstring.", 512),
        ("correct_factual", "What is the capital of France?", 200),
        # Token budget too low — likely invalid output
        ("budget_too_low", "Analyze the complete risk profile of a DeFi protocol with $100M TVL, volatile collateral, cross-chain bridges, governance token, and no insurance fund. Provide detailed assessment.", 20),
        # Duplicate work simulation
        ("duplicate_1", "What is 2+2? Answer with only the number.", 50),
        ("duplicate_2", "What is 2+2? Answer with only the number.", 50),
        # Interrupted job simulation (very short timeout handled by our code)
        ("borderline_budget", "What are the top 3 risks of DeFi?", 30),
    ]

    results = []
    async with aiohttp.ClientSession() as session:
        for label, prompt, tokens in tests:
            r = await send(session, prompt, tokens, label)
            results.append(r)
            validity = "VALID" if r["valid"] else "INVALID"
            print(f"\n{label}")
            print(f"  Status      : {r['status']}")
            print(f"  Finish      : {r['finish_reason']}")
            print(f"  Content len : {r['content_len']} chars")
            print(f"  Reasoning   : {r['reasoning_len']} chars")
            print(f"  Validity    : {validity}")
            print(f"  Request ID  : {r['request_id']}")
            await asyncio.sleep(3)

    print("\n" + "=" * 55)
    print("VALIDITY SUMMARY")
    print("=" * 55)
    for r in results:
        v = "✓ VALID" if r["valid"] else "✗ INVALID"
        print(f"{r['label']:25} | {v} | finish:{r['finish_reason']} | content:{r['content_len']}c")

    with open("valid_work_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nSaved to valid_work_results.json")

asyncio.run(main())

import asyncio
import aiohttp
import time
import json
import statistics

API_KEY = "dKVk85DEx9QXUfK17ZSSpnPBAVurorCOAjz9cPCMg6PCY6FqEY"
API_URL = "https://api.ambient.xyz/v1/chat/completions"
MODEL = "zai-org/GLM-5.1-FP8"

async def call_with_retry(session, prompt, max_retries=3, timeout=30):
    last_error = None
    for attempt in range(1, max_retries + 1):
        start = time.time()
        try:
            async with session.post(
                API_URL,
                headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
                json={"model": MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": 200},
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                latency = round(time.time() - start, 2)
                if resp.status == 429:
                    wait = 10 * attempt
                    print(f"    Rate limited (attempt {attempt}), waiting {wait}s")
                    await asyncio.sleep(wait)
                    continue
                if resp.status >= 500:
                    print(f"    Server error {resp.status} (attempt {attempt}), retrying")
                    await asyncio.sleep(5)
                    continue
                data = await resp.json()
                content = data["choices"][0]["message"].get("reasoning_content") or data["choices"][0]["message"].get("content") or ""
                if len(content) < 20:
                    print(f"    Empty output (attempt {attempt}), retrying")
                    await asyncio.sleep(3)
                    continue
                return {"status": "OK", "content": content, "latency": latency, "attempts": attempt}
        except asyncio.TimeoutError:
            latency = round(time.time() - start, 2)
            print(f"    Timeout after {latency}s (attempt {attempt})")
            last_error = "TIMEOUT"
            await asyncio.sleep(3)
        except Exception as e:
            latency = round(time.time() - start, 2)
            print(f"    Error (attempt {attempt}): {str(e)[:50]}")
            last_error = str(e)[:50]
            await asyncio.sleep(3)

    return {"status": f"FAILED:{last_error}", "content": None, "latency": 0, "attempts": max_retries}

def validate_output(content, expected_keywords=None):
    if not content or len(content) < 20:
        return False, "TOO_SHORT"
    if expected_keywords:
        found = [k for k in expected_keywords if k.lower() in content.lower()]
        if not found:
            return False, f"MISSING_KEYWORDS:{expected_keywords}"
    return True, "OK"

async def main():
    print("=" * 55)
    print("Ambient Failure Handling — Week 19 Dev Loop")
    print("=" * 55)

    tests = [
        {
            "label": "Normal request",
            "prompt": "What are the top 3 risks of DeFi lending?",
            "keywords": ["liquidat", "oracle", "smart contract"],
            "timeout": 30
        },
        {
            "label": "Short timeout (stress test)",
            "prompt": "Analyze the complete risk profile of a $100M TVL DeFi protocol with volatile collateral, cross-chain bridges, 6-month governance token, and no insurance fund.",
            "keywords": ["risk"],
            "timeout": 8
        },
        {
            "label": "Validation test",
            "prompt": "What is 2+2?",
            "keywords": ["4"],
            "timeout": 30
        },
        {
            "label": "Long chain test",
            "prompt": "List 10 DeFi protocols and for each one describe: founding year, TVL, main risk, and one notable incident.",
            "keywords": ["aave", "compound"],
            "timeout": 45
        },
    ]

    results = []
    async with aiohttp.ClientSession() as session:
        for test in tests:
            print(f"\nTest: {test['label']}")
            result = await call_with_retry(session, test["prompt"], timeout=test["timeout"])
            valid, reason = validate_output(result.get("content"), test["keywords"])

            entry = {
                "label": test["label"],
                "status": result["status"],
                "latency": result["latency"],
                "attempts": result["attempts"],
                "valid": valid,
                "validation": reason
            }
            results.append(entry)

            print(f"  Status     : {result['status']}")
            print(f"  Attempts   : {result['attempts']}")
            print(f"  Latency    : {result['latency']}s")
            print(f"  Validation : {reason}")
            await asyncio.sleep(5)

    print("\n" + "=" * 55)
    print("SUMMARY")
    print("=" * 55)
    ok = [r for r in results if r["status"] == "OK"]
    valid = [r for r in results if r["valid"]]
    retried = [r for r in results if r["attempts"] > 1]
    print(f"Success    : {len(ok)}/{len(results)}")
    print(f"Valid      : {len(valid)}/{len(results)}")
    print(f"Retried    : {len(retried)}")
    if ok:
        lats = [r["latency"] for r in ok]
        print(f"Avg latency: {round(statistics.mean(lats), 2)}s")

    with open("failure_handling_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("Saved to failure_handling_results.json")

asyncio.run(main())

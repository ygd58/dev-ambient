import asyncio
import aiohttp
import time
import json

# Ambient OpenAI-compatible endpoint
API_KEY = "dKVk85DEx9QXUfK17ZSSpnPBAVurorCOAjz9cPCMg6PCY6FqEY"
BASE_URL = "https://api.ambient.xyz/v1"
MODEL = "moonshotai/kimi-k2.7-code"

async def test_chat(session, prompt, label):
    start = time.time()
    try:
        async with session.post(
            f"{BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={"model": MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": 200},
            timeout=aiohttp.ClientTimeout(total=45)
        ) as resp:
            latency = round(time.time() - start, 2)
            data = await resp.json()
            content = data["choices"][0]["message"].get("reasoning_content") or data["choices"][0]["message"].get("content") or ""
            print(f"{label}: {resp.status} | {latency}s | {len(content)} chars")
            return {"label": label, "status": resp.status, "latency": latency, "content": content[:100]}
    except Exception as e:
        return {"label": label, "status": 0, "error": str(e)}

async def test_models(session):
    async with session.get(
        f"{BASE_URL}/models",
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=aiohttp.ClientTimeout(total=10)
    ) as resp:
        data = await resp.json()
        models = [m["id"] for m in data.get("data", [])]
        print(f"\nAvailable models: {models}")
        return models

async def main():
    print("=" * 55)
    print("Ambient OpenAI-Compatible API Test — Week 18")
    print("=" * 55)

    async with aiohttp.ClientSession() as session:
        # Test models endpoint
        print("\n1. Models endpoint:")
        await test_models(session)

        # Test various prompt types
        print("\n2. Chat completions:")
        tests = [
            ("Simple", "What is 2+2?"),
            ("Code", "Write a Python function that calculates compound interest."),
            ("Analysis", "What are the top 3 risks of DeFi lending protocols?"),
            ("Multi-turn simulation", "You are a DeFi analyst. What is your first question when auditing a new protocol?"),
        ]

        results = []
        for label, prompt in tests:
            result = await test_chat(session, prompt, label)
            results.append(result)
            await asyncio.sleep(3)

    print("\n" + "=" * 55)
    print("SUMMARY")
    print("=" * 55)
    success = [r for r in results if r.get("status") == 200]
    print(f"Success rate: {len(success)}/{len(results)}")
    if success:
        import statistics
        lats = [r["latency"] for r in success]
        print(f"Avg latency : {round(statistics.mean(lats), 2)}s")

asyncio.run(main())

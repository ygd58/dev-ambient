import asyncio
import aiohttp
import time

API_KEY = "nwxog69qsdx1Of28dzVJxaDKmT3wvvuPmK46WnzhtYH03jS6jP"
API_URL = "https://api.ambient.xyz/v1/chat/completions"

async def send(session, prompt, label):
    start = time.time()
    try:
        async with session.post(
            API_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={"model": "zai-org/GLM-5-FP8", "messages": [{"role": "user", "content": prompt}], "max_tokens": 200},
            timeout=aiohttp.ClientTimeout(total=60)
        ) as resp:
            await resp.json()
            print(f"{label}: {resp.status} in {time.time()-start:.2f}s")
    except Exception as e:
        print(f"{label}: FAILED after {time.time()-start:.2f}s")

async def main():
    print("=== Mixed Workload Test ===")
    async with aiohttp.ClientSession() as session:
        await asyncio.gather(
            send(session, "What is 2+2?", "Simple-1"),
            send(session, "What is 2+2?", "Simple-2"),
            send(session, "Analyze top 5 risks of DeFi with severity ratings", "Heavy-1"),
            send(session, "What is 2+2?", "Simple-3"),
            send(session, "Analyze top 5 risks of DeFi with severity ratings", "Heavy-2"),
            send(session, "What is 2+2?", "Simple-4"),
            send(session, "Write a 10 step security audit checklist for smart contracts", "Heavy-3"),
        )

asyncio.run(main())

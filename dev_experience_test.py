import asyncio
import aiohttp
import time
import json
import statistics

API_KEY = "dKVk85DEx9QXUfK17ZSSpnPBAVurorCOAjz9cPCMg6PCY6FqEY"
API_URL = "https://api.ambient.xyz/v1/chat/completions"
MODELS = {
    "large": "ambient/large",
    "glm": "z-ai/glm-5.2",
    "qwen": "qwen/qwen3.6-27b"
}

async def send(session, model, prompt, max_tokens=300):
    start = time.time()
    try:
        async with session.post(
            API_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens},
            timeout=aiohttp.ClientTimeout(total=45)
        ) as resp:
            latency = round(time.time() - start, 2)
            data = await resp.json()
            msg = data.get("choices", [{}])[0].get("message", {})
            content = msg.get("content") or msg.get("reasoning") or ""
            return {"status": resp.status, "latency": latency, "content": content, "ok": len(content.strip()) > 10}
    except Exception as e:
        return {"status": 0, "latency": round(time.time()-start, 2), "content": "", "ok": False, "error": str(e)[:50]}

async def test_auth(session):
    print("\nTest 1 — Authentication")
    r = await send(session, MODELS["large"], "What is 2+2?", 50)
    print(f"  Status: {r['status']} | OK: {r['ok']} | Latency: {r['latency']}s")
    return r["ok"]

async def test_model_switching(session):
    print("\nTest 2 — Model switching")
    results = []
    for name, model in MODELS.items():
        r = await send(session, model, "What is the capital of France? One word.", 50)
        correct = "paris" in r["content"].lower()
        print(f"  {name:10} | {r['latency']}s | correct:{correct} | status:{r['status']}")
        results.append({"model": name, "ok": r["ok"], "correct": correct, "latency": r["latency"]})
        await asyncio.sleep(2)
    return results

async def test_long_running(session):
    print("\nTest 3 — Long running task")
    prompt = """You are a senior developer. Analyze this code and provide:
1. Security vulnerabilities
2. Performance issues  
3. Refactoring suggestions

```python
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    result = db.execute(query)
    return result
```"""
    r = await send(session, MODELS["large"], prompt, 500)
    print(f"  Status: {r['status']} | Latency: {r['latency']}s | Length: {len(r['content'])} chars")
    print(f"  SQL injection found: {'sql' in r['content'].lower() or 'inject' in r['content'].lower()}")
    return r

async def test_concurrent_auth(session):
    print("\nTest 4 — Concurrent requests (reliability)")
    start = time.time()
    results = await asyncio.gather(*[
        send(session, MODELS["large"], "What is 2+2?", 50) for _ in range(10)
    ])
    total = round(time.time()-start, 2)
    ok = [r for r in results if r["ok"]]
    lats = [r["latency"] for r in ok]
    print(f"  Success: {len(ok)}/10 | Total: {total}s | Avg: {round(statistics.mean(lats), 2) if lats else 'N/A'}s")
    return results

async def main():
    print("=" * 55)
    print("Ambient Dev Experience Test — Week 24")
    print("=" * 55)

    async with aiohttp.ClientSession() as session:
        auth_ok = await test_auth(session)
        if not auth_ok:
            print("Auth failed, stopping")
            return

        await test_model_switching(session)
        await asyncio.sleep(3)
        await test_long_running(session)
        await asyncio.sleep(3)
        await test_concurrent_auth(session)

    print("\nDone.")

asyncio.run(main())

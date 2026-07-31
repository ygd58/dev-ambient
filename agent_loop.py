import asyncio
import aiohttp
import time
import json
import os

API_KEY = "dKVk85DEx9QXUfK17ZSSpnPBAVurorCOAjz9cPCMg6PCY6FqEY"
API_URL = "https://api.ambient.xyz/v1/chat/completions"
MODEL = "moonshotai/kimi-k2.7-code"
LOG_FILE = "agent_log.json"

GOAL = "Produce a 3-step security checklist for deploying a Solidity smart contract."

STEPS = [
    {"id": "plan",     "prompt": f"Goal: {GOAL}\nList 3 concrete steps to achieve this goal. Be specific."},
    {"id": "action",   "prompt": f"Goal: {GOAL}\nFor each step, describe one concrete action to take."},
    {"id": "evaluate", "prompt": f"Goal: {GOAL}\nEvaluate whether the steps above would actually achieve the goal. Rate confidence 1-10."},
    {"id": "repeat",   "prompt": f"Goal: {GOAL}\nBased on the evaluation, what is the most important improvement to make?"},
]

MAX_RETRIES = 3
RETRY_DELAY = 5

async def call_model(session, prompt, step_id, attempt=1):
    start = time.time()
    try:
        async with session.post(
            API_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={"model": MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": 300},
            timeout=aiohttp.ClientTimeout(total=45)
        ) as resp:
            latency = round(time.time() - start, 2)
            if resp.status == 429:
                print(f"  Rate limited on {step_id}, attempt {attempt}")
                return None, latency, "RATE_LIMITED"
            data = await resp.json()
            content = data["choices"][0]["message"].get("reasoning_content") or data["choices"][0]["message"].get("content") or ""
            if len(content) < 20:
                return None, latency, "EMPTY_OUTPUT"
            return content, latency, "OK"
    except asyncio.TimeoutError:
        return None, round(time.time()-start, 2), "TIMEOUT"
    except Exception as e:
        return None, round(time.time()-start, 2), f"ERROR: {e}"

async def run_agent():
    print("=" * 55)
    print("Ambient Agent Loop — Week 15")
    print(f"Goal: {GOAL}")
    print("=" * 55)

    log = {"goal": GOAL, "steps": []}
    context = []

    async with aiohttp.ClientSession() as session:
        for step in STEPS:
            prompt = step["prompt"]
            if context:
                prompt = "Prior context:\n" + "\n".join(context[-2:]) + "\n\n" + prompt

            print(f"\nStep: {step['id']}")
            content, latency, status = None, 0, "PENDING"

            for attempt in range(1, MAX_RETRIES + 1):
                content, latency, status = await call_model(session, prompt, step["id"], attempt)
                if status == "OK":
                    break
                print(f"  Attempt {attempt} failed: {status} — retrying in {RETRY_DELAY}s")
                await asyncio.sleep(RETRY_DELAY)

            entry = {
                "step": step["id"],
                "status": status,
                "latency": latency,
                "attempts": attempt,
                "output": content[:150] if content else None
            }
            log["steps"].append(entry)

            if status == "OK":
                context.append(f"{step['id']}: {content[:100]}")
                print(f"  Status  : OK")
                print(f"  Latency : {latency}s")
                print(f"  Attempts: {attempt}")
                print(f"  Preview : {content[:80]}...")
            else:
                print(f"  Status  : FAILED after {attempt} attempts ({status})")
                print(f"  Skipping to next step with degraded context")

            await asyncio.sleep(3)

    with open(LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)

    print("\n" + "=" * 55)
    print("AGENT LOOP SUMMARY")
    print("=" * 55)
    ok = [s for s in log["steps"] if s["status"] == "OK"]
    failed = [s for s in log["steps"] if s["status"] != "OK"]
    retried = [s for s in log["steps"] if s["attempts"] > 1]
    print(f"Steps completed : {len(ok)}/{len(STEPS)}")
    print(f"Steps failed    : {len(failed)}")
    print(f"Steps retried   : {len(retried)}")
    if ok:
        import statistics
        lats = [s["latency"] for s in ok]
        print(f"Avg latency     : {round(statistics.mean(lats), 2)}s")
    print(f"Log saved to    : {LOG_FILE}")

asyncio.run(run_agent())

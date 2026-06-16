import asyncio
import aiohttp
import time
import json

API_KEY = "dKVk85DEx9QXUfK17ZSSpnPBAVurorCOAjz9cPCMg6PCY6FqEY"
API_URL = "https://api.ambient.xyz/v1/chat/completions"
MODEL = "zai-org/GLM-5.1-FP8"
LOG_FILE = "multi_agent_log.json"

TOPIC = "Should a DeFi protocol with $50M TVL add a new volatile token as collateral?"

AGENTS = [
    {
        "id": "research_agent",
        "prompt": f"You are a DeFi research agent. List 5 key facts about this topic: {TOPIC}"
    },
    {
        "id": "analysis_agent",
        "prompt": "You are a risk analysis agent. Based on the research below, list the top 3 risks and top 2 opportunities:\n\n"
    },
    {
        "id": "decision_agent",
        "prompt": "You are a decision agent. Based on the context below, give a YES or NO answer with 3 specific conditions:\n\n"
    },
    {
        "id": "verification_agent",
        "prompt": "You are a verification agent. Rate the decision chain below 1-10 and identify the biggest gap in reasoning:\n\n"
    }
]

async def call_agent(session, prompt, retries=3):
    for attempt in range(retries):
        start = time.time()
        try:
            async with session.post(
                API_URL,
                headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
                json={"model": MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": 250},
                timeout=aiohttp.ClientTimeout(total=45)
            ) as resp:
                latency = round(time.time() - start, 2)
                if resp.status == 429:
                    print(f"  Rate limited, waiting 10s...")
                    await asyncio.sleep(10)
                    continue
                data = await resp.json()
                content = data["choices"][0]["message"].get("reasoning_content") or data["choices"][0]["message"].get("content") or ""
                if len(content) < 30:
                    print(f"  Short output on attempt {attempt+1}, retrying...")
                    await asyncio.sleep(5)
                    continue
                return {"status": "OK", "content": content, "latency": latency, "attempts": attempt+1}
        except Exception as e:
            print(f"  Attempt {attempt+1} failed: {e}")
            await asyncio.sleep(5)
    return {"status": "FAILED", "content": "", "latency": 0, "attempts": retries}

async def main():
    print("=" * 55)
    print("Ambient Multi-Agent Pipeline — Week 17")
    print(f"Topic: {TOPIC}")
    print("=" * 55)

    log = {"topic": TOPIC, "agents": []}
    context = ""
    total_start = time.time()

    async with aiohttp.ClientSession() as session:
        for i, agent in enumerate(AGENTS):
            print(f"\nAgent: {agent['id']}")
            prompt = agent["prompt"] if i == 0 else agent["prompt"] + context
            result = await call_agent(session, prompt)

            entry = {
                "agent": agent["id"],
                "status": result["status"],
                "latency": result["latency"],
                "attempts": result["attempts"],
                "output": result["content"][:200]
            }
            log["agents"].append(entry)

            if result["status"] == "OK":
                print(f"  Status   : OK ({result['latency']}s, attempt {result['attempts']})")
                print(f"  Preview  : {result['content'][:100]}...")
                context += f"\n\n[{agent['id'].upper()}]\n{result['content']}"
            else:
                print(f"  Status   : FAILED after {result['attempts']} attempts")

            await asyncio.sleep(5)

    total = round(time.time() - total_start, 2)
    log["total_time"] = total

    print(f"\n{'='*55}")
    print("SUMMARY")
    print(f"{'='*55}")
    ok = [a for a in log["agents"] if a["status"] == "OK"]
    retried = [a for a in log["agents"] if a["attempts"] > 1]
    print(f"Completed : {len(ok)}/{len(AGENTS)}")
    print(f"Retried   : {len(retried)}")
    print(f"Total time: {total}s")

    with open(LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)
    print(f"Log saved : {LOG_FILE}")

asyncio.run(main())

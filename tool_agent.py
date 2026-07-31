import asyncio
import aiohttp
import time
import json
import statistics

API_KEY = "dKVk85DEx9QXUfK17ZSSpnPBAVurorCOAjz9cPCMg6PCY6FqEY"
API_URL = "https://api.ambient.xyz/v1/chat/completions"
MODEL = "moonshotai/kimi-k2.7-code"

# Simulated tools
TOOLS = {
    "get_price": lambda asset: {"asset": asset, "price": {"ETH": 1842, "BTC": 97500, "SOL": 148}.get(asset, 0), "currency": "USD"},
    "get_risk_score": lambda protocol: {"protocol": protocol, "score": {"aave": 3.2, "compound": 3.5, "uniswap": 4.1}.get(protocol.lower(), 7.0), "max": 10},
    "calculate_position": lambda amount, pct: {"amount": amount, "allocation_pct": pct, "position_size": round(amount * pct / 100, 2)},
}

async def call_model(session, messages, max_tokens=300):
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
            return {"content": content, "latency": latency, "status": "OK"}
    except Exception as e:
        return {"content": "", "latency": round(time.time()-start, 2), "status": f"ERROR: {e}"}

def execute_tool(tool_name, **kwargs):
    if tool_name in TOOLS:
        result = TOOLS[tool_name](**kwargs)
        return json.dumps(result)
    return json.dumps({"error": f"Unknown tool: {tool_name}"})

async def run_agent(session, goal):
    print(f"\nGoal: {goal}")
    print("-" * 50)

    messages = []
    tool_results = []
    latencies = []

    # Step 1: Plan
    messages.append({"role": "user", "content": f"""You are a financial research agent with access to these tools:
- get_price(asset): Get current price of ETH, BTC, or SOL
- get_risk_score(protocol): Get risk score for aave, compound, or uniswap
- calculate_position(amount, pct): Calculate position size

Goal: {goal}

Step 1: List which tools you need to call and in what order. Be specific."""})

    plan = await call_model(session, messages)
    latencies.append(plan["latency"])
    print(f"Plan ({plan['latency']}s): {plan['content'][:150]}...")
    messages.append({"role": "assistant", "content": plan["content"]})
    await asyncio.sleep(2)

    # Step 2: Execute tools
    tools_to_run = [
        ("get_price", {"asset": "ETH"}),
        ("get_risk_score", {"protocol": "aave"}),
        ("calculate_position", {"amount": 100000, "pct": 2}),
    ]

    for tool_name, kwargs in tools_to_run:
        result = execute_tool(tool_name, **kwargs)
        tool_results.append(f"{tool_name}: {result}")
        print(f"Tool {tool_name}: {result}")

    # Step 3: Analyze with tool results
    messages.append({"role": "user", "content": f"""Tool results:
{chr(10).join(tool_results)}

Step 2: Based on these results, produce a final recommendation for the goal: {goal}
Be specific and quantitative."""})

    analysis = await call_model(session, messages, max_tokens=400)
    latencies.append(analysis["latency"])
    print(f"\nAnalysis ({analysis['latency']}s):\n{analysis['content'][:300]}...")

    # Step 4: Evaluate
    messages.append({"role": "assistant", "content": analysis["content"]})
    messages.append({"role": "user", "content": "Step 3: Rate your own recommendation 1-10 for completeness and identify the single biggest gap."})

    evaluation = await call_model(session, messages, max_tokens=200)
    latencies.append(evaluation["latency"])
    print(f"\nEvaluation ({evaluation['latency']}s):\n{evaluation['content'][:200]}...")

    return {
        "goal": goal,
        "steps": 3,
        "tool_calls": len(tools_to_run),
        "total_latency": round(sum(latencies), 2),
        "avg_latency": round(statistics.mean(latencies), 2),
        "status": "OK"
    }

async def main():
    print("=" * 55)
    print("Ambient Tool-Using Agent — Week 20 Dev Loop")
    print("=" * 55)

    goal = "I have $100,000 to allocate. Should I buy ETH and deposit it into Aave? Give me a specific recommendation with position sizing."

    async with aiohttp.ClientSession() as session:
        result = await run_agent(session, goal)

    print("\n" + "=" * 55)
    print("SUMMARY")
    print("=" * 55)
    print(f"Steps completed : {result['steps']}")
    print(f"Tool calls      : {result['tool_calls']}")
    print(f"Total latency   : {result['total_latency']}s")
    print(f"Avg per step    : {result['avg_latency']}s")

    with open("tool_agent_results.json", "w") as f:
        json.dump(result, f, indent=2)
    print("Saved to tool_agent_results.json")

asyncio.run(main())

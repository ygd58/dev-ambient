import asyncio
import aiohttp
import time
import json
import statistics
import os

API_KEY = "dKVk85DEx9QXUfK17ZSSpnPBAVurorCOAjz9cPCMg6PCY6FqEY"
API_URL = "https://api.ambient.xyz/v1/chat/completions"
MODEL = "zai-org/GLM-5.1-FP8"
MEMORY_FILE = "memory.json"

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return {"sessions": [], "context": []}

def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)

def build_prompt_with_memory(new_prompt, memory):
    if not memory["context"]:
        return new_prompt
    context = "\n".join([f"- {c}" for c in memory["context"][-3:]])
    return f"Previous context:\n{context}\n\nNew question: {new_prompt}"

async def call_model(session, prompt):
    start = time.time()
    try:
        async with session.post(
            API_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={"model": MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": 300},
            timeout=aiohttp.ClientTimeout(total=60)
        ) as resp:
            latency = time.time() - start
            data = await resp.json()
            content = data["choices"][0]["message"].get("reasoning_content") or data["choices"][0]["message"].get("content") or ""
            return {"latency": round(latency, 2), "content": content, "status": "OK"}
    except Exception as e:
        return {"latency": round(time.time()-start, 2), "content": "", "status": f"ERR: {e}"}

WORKFLOW = [
    {"id": "step1", "prompt": "A DeFi protocol has $50M TVL and uses volatile collateral. What is the top risk?", "save": "Top risk: volatile collateral liquidation cascade"},
    {"id": "step2", "prompt": "Which risk should be addressed first?", "save": "Priority: address collateral volatility first"},
    {"id": "step3", "prompt": "Propose one concrete mitigation for that risk.", "save": "Mitigation: dynamic LTV adjustment based on volatility"},
    {"id": "step4", "prompt": "Summarize our entire discussion in 2 sentences.", "save": None}
]

async def main():
    print("=" * 55)
    print("Ambient Memory Layer + SGLANG Benchmark — Week 14")
    print("=" * 55)

    memory = load_memory()
    latencies = []
    results = []

    async with aiohttp.ClientSession() as session:
        for step in WORKFLOW:
            prompt = build_prompt_with_memory(step["prompt"], memory)
            print(f"\nStep: {step['id']}")
            print(f"Context injected: {len(memory['context'])} items")

            result = await call_model(session, prompt)
            latencies.append(result["latency"])

            if step["save"]:
                memory["context"].append(step["save"])

            session_entry = {
                "step": step["id"],
                "latency": result["latency"],
                "status": result["status"],
                "context_size": len(memory["context"]),
                "output_preview": result["content"][:100]
            }
            results.append(session_entry)
            memory["sessions"].append(session_entry)

            print(f"Latency : {result['latency']}s")
            print(f"Status  : {result['status']}")
            print(f"Preview : {result['content'][:80]}...")
            await asyncio.sleep(2)

    save_memory(memory)

    print("\n" + "=" * 55)
    print("SGLANG BENCHMARK SUMMARY")
    print("=" * 55)
    print(f"Steps completed : {len(latencies)}")
    print(f"Avg latency     : {round(statistics.mean(latencies), 2)}s")
    print(f"Min latency     : {min(latencies)}s")
    print(f"Max latency     : {max(latencies)}s")
    print(f"Latency spread  : {round(max(latencies) - min(latencies), 2)}s")
    print(f"Memory entries  : {len(memory['context'])}")
    print("\nResults saved to memory.json")

asyncio.run(main())

import re
import json
import asyncio
import aiohttp
import time

API_KEY = "dKVk85DEx9QXUfK17ZSSpnPBAVurorCOAjz9cPCMg6PCY6FqEY"
API_URL = "https://api.ambient.xyz/v1/chat/completions"
MODEL = "moonshotai/kimi-k2.7-code"

DETERMINISTIC_SIGNALS = [
    "formula", "calculate", "equals", "result is", "=", "%", "$",
    "proof", "theorem", "always", "exactly", "computed", "verified"
]

PROBABILISTIC_SIGNALS = [
    "likely", "probably", "may", "might", "predict", "estimate",
    "forecast", "could", "expected", "approximately", "tends to",
    "suggests", "indicates", "analysis shows"
]

UNVERIFIABLE_SIGNALS = [
    "appears to", "seems", "looks like", "feels", "i think",
    "i believe", "arguably", "implies", "unclear", "opinion",
    "speculation", "subjective"
]

def classify(output):
    text = output.lower()
    if len(output.strip()) < 25:
        return {
            "classification": "UNVERIFIABLE",
            "confidence": 0.0,
            "reason": "Output too short or incomplete.",
            "action": "REJECT",
            "tee_required": True
        }

    d = sum(1 for s in DETERMINISTIC_SIGNALS if s in text)
    p = sum(1 for s in PROBABILISTIC_SIGNALS if s in text)
    u = sum(1 for s in UNVERIFIABLE_SIGNALS if s in text)
    total = d + p + u or 1

    scores = {"DETERMINISTIC": d, "PROBABILISTIC": p, "UNVERIFIABLE": u}
    top = max(scores, key=scores.get)
    top_score = scores[top]
    confidence = round(top_score / total, 2)

    sorted_scores = sorted(scores.values(), reverse=True)
    is_mixed = sorted_scores[0] > 0 and sorted_scores[1] > 0 and sorted_scores[0] - sorted_scores[1] <= 1

    if is_mixed:
        return {
            "classification": "MIXED",
            "confidence": confidence,
            "reason": f"Signal scores: {scores}",
            "action": "REJECT — separate categories before use",
            "tee_required": True
        }

    tee_required = top in ["UNVERIFIABLE", "PROBABILISTIC"]
    action = "ACCEPT" if top == "DETERMINISTIC" else "REVIEW"

    return {
        "classification": top,
        "confidence": confidence,
        "reason": f"Signal scores: {scores}",
        "action": action,
        "tee_required": tee_required
    }

async def fetch_and_classify(session, prompt, label):
    start = time.time()
    try:
        async with session.post(
            API_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={"model": MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": 200},
            timeout=aiohttp.ClientTimeout(total=45)
        ) as resp:
            latency = round(time.time() - start, 2)
            data = await resp.json()
            content = data["choices"][0]["message"].get("reasoning_content") or data["choices"][0]["message"].get("content") or ""
            result = classify(content)
            result["label"] = label
            result["latency"] = latency
            result["output_preview"] = content[:80]
            return result
    except Exception as e:
        return {"label": label, "classification": "ERROR", "action": "REJECT", "error": str(e), "tee_required": True}

TEST_PROMPTS = [
    ("math", "What is compound interest on $10,000 at 7% for 10 years compounded monthly?"),
    ("forecast", "Will Bitcoin reach $200,000 by end of 2025?"),
    ("opinion", "Is DeFi better than traditional finance?"),
    ("audit", "This smart contract appears to have no critical vulnerabilities"),
    ("logic", "If all validators are honest and quorum is 2/3, is the network safe?"),
]

async def main():
    print("=" * 60)
    print("Ambient Output Classifier v2 — Week 16")
    print("Verified vs Unverified Execution")
    print("=" * 60)

    results = []
    async with aiohttp.ClientSession() as session:
        for label, prompt in TEST_PROMPTS:
            print(f"\nTesting: {label}")
            result = await fetch_and_classify(session, prompt, label)
            results.append(result)
            print(f"  Classification : {result['classification']}")
            print(f"  Confidence     : {result.get('confidence', 'N/A')}")
            print(f"  Action         : {result['action']}")
            print(f"  TEE Required   : {result['tee_required']}")
            await asyncio.sleep(2)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    accept = [r for r in results if r["action"] == "ACCEPT"]
    review = [r for r in results if r["action"] == "REVIEW"]
    reject = [r for r in results if "REJECT" in r.get("action","")]
    tee = [r for r in results if r.get("tee_required")]
    print(f"ACCEPT  : {len(accept)}")
    print(f"REVIEW  : {len(review)}")
    print(f"REJECT  : {len(reject)}")
    print(f"TEE Required : {len(tee)}")

    with open("classifier_v2_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nSaved to classifier_v2_results.json")

asyncio.run(main())

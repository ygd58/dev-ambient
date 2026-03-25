DETERMINISTIC_SIGNALS = [
    "formula", "calculate", "equals", "result is", "=", "%", "$",
    "proof", "theorem", "always", "exactly", "computed"
]

PROBABILISTIC_SIGNALS = [
    "likely", "probably", "may", "might", "predict", "estimate",
    "forecast", "could", "expected", "approximately", "tends to"
]

UNVERIFIABLE_SIGNALS = [
    "appears to", "seems", "looks like", "feels", "i think",
    "i believe", "arguably", "suggests", "implies", "unclear"
]

def classify(output):
    text = output.lower()
    if len(output.strip()) < 25:
        return {"classification": "UNVERIFIABLE", "reason": "Incomplete output.", "action": "REJECT"}
    d = sum(1 for s in DETERMINISTIC_SIGNALS if s in text)
    p = sum(1 for s in PROBABILISTIC_SIGNALS if s in text)
    u = sum(1 for s in UNVERIFIABLE_SIGNALS if s in text)
    scores = {"DETERMINISTIC": d, "PROBABILISTIC": p, "UNVERIFIABLE": u}
    top = max(scores, key=scores.get)
    sorted_scores = sorted(scores.values(), reverse=True)
    if sorted_scores[0] > 0 and sorted_scores[1] > 0 and sorted_scores[0] - sorted_scores[1] <= 1:
        return {"classification": "MIXED", "reason": f"Scores: {scores}", "action": "REJECT"}
    if top == "UNVERIFIABLE":
        return {"classification": top, "reason": f"Scores: {scores}", "action": "REJECT"}
    return {"classification": top, "reason": f"Scores: {scores}", "action": "ACCEPT"}

tests = [
    "The compound interest on $10,000 at 7% for 10 years is $20,096.61",
    "Bitcoin will likely reach $150,000 by end of 2025",
    "This smart contract appears to have no critical vulnerabilities",
    "This smart contract appears to have no"
]

print("=" * 55)
print("Ambient Output Classifier — Week 9")
print("=" * 55)
for i, t in enumerate(tests, 1):
    r = classify(t)
    print(f"\nOutput {i}: \"{t[:55]}\"")
    print(f"  Class  : {r['classification']}")
    print(f"  Action : {r['action']}")

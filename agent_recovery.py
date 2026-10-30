import asyncio, aiohttp, json, os, sys, time

KEY = os.environ["AMBIENT_API_KEY"]
URL = "https://api.ambient.xyz/v1/chat/completions"
STATE = "agent_state.json"
CALLS = "agent_calls.jsonl"
CRASH_AFTER = int(os.environ.get("CRASH_AFTER", "0"))  # 0 = no crash

STEPS = [
    ("research", "List 3 key risks of DeFi lending protocols as a JSON array of strings. Return ONLY JSON."),
    ("analysis", "Given these risks: {research}\nRank them by severity. Return ONLY a JSON array of strings, most severe first."),
    ("draft", "Given this ranking: {analysis}\nWrite a 2 sentence risk summary. Return ONLY the text."),
    ("check", "Is this summary consistent with a ranking whose first item is the most severe risk?\nSummary: {draft}\nAnswer with one word: YES or NO."),
    ("final", "Summary: {draft}\nCheck result: {check}\nWrite a one line conclusion. Return ONLY the text."),
]

def load():
    if os.path.exists(STATE):
        return json.load(open(STATE))
    return {"done": {}}

def save(st):
    tmp = STATE + ".tmp"
    json.dump(st, open(tmp, "w"), indent=2)
    os.replace(tmp, STATE)

async def call(s, prompt):
    body = {"model": "ambient/large", "messages": [{"role": "user", "content": prompt}], "max_tokens": 2048}
    for attempt in range(1, 4):
        t = time.time()
        try:
            async with s.post(URL, headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
                              json=body, timeout=aiohttp.ClientTimeout(total=60)) as r:
                d = await r.json(content_type=None)
                ch = (d.get("choices") or [{}])[0]
                text = ((ch.get("message") or {}).get("content") or "").strip()
                rec = {"id": d.get("id"), "status": r.status, "attempt": attempt,
                       "lat": round(time.time()-t, 2), "finish": ch.get("finish_reason"), "empty": not text}
                open(CALLS, "a").write(json.dumps(rec) + "\n")
                if r.status == 200 and text:
                    return text
        except Exception as e:
            open(CALLS, "a").write(json.dumps({"error": str(e)[:60], "attempt": attempt}) + "\n")
        await asyncio.sleep(2 * attempt)
    raise RuntimeError("step failed after retries")

async def main():
    st = load()
    ran = 0
    async with aiohttp.ClientSession() as s:
        for name, tmpl in STEPS:
            if name in st["done"]:
                print(f"SKIP  {name} (already done)")
                continue
            prompt = tmpl.format(**st["done"])
            out = await call(s, prompt)
            st["done"][name] = out
            save(st)
            ran += 1
            print(f"RUN   {name}: {out[:60]!r}")
            if CRASH_AFTER and ran == CRASH_AFTER:
                print("\n*** deliberate interruption ***")
                sys.exit(1)
    print("\nCOMPLETE. steps run this session:", ran)

asyncio.run(main())

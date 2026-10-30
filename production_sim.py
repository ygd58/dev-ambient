import asyncio, aiohttp, json, os, time, re, statistics

API_URL = "https://api.ambient.xyz/v1/chat/completions"
MODEL = "ambient/large"
LOG_FILE = "production_sim_log.jsonl"

def log(event, **kw):
    kw.update({"ts": round(time.time(), 2), "event": event})
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(kw) + "\n")

def parse_json(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    return json.loads(text)

def valid_schema(data):
    return (isinstance(data, list) and len(data) == 5 and
            all(isinstance(x, dict) and isinstance(x.get("protocol"), str)
                and isinstance(x.get("risk"), str)
                and isinstance(x.get("severity"), int) for x in data))

async def call(session, prompt, api_key, max_tokens, timeout):
    async with session.post(API_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens},
        timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
        data = await resp.json()
        return resp.status, data

async def resilient(session, job_id, prompt, api_key, timeout=40):
    max_tokens = 2048
    for attempt in range(1, 5):
        start = time.time()
        try:
            status, data = await call(session, prompt, api_key, max_tokens, timeout)
            lat = round(time.time() - start, 2)
            if status in (401, 402, 403):
                log("fatal", job=job_id, status=status)
                return {"job": job_id, "ok": False, "reason": f"fatal_{status}", "attempts": attempt}
            if status == 429 or status >= 500:
                log("retry_http", job=job_id, status=status, attempt=attempt)
                await asyncio.sleep(2 ** attempt)
                continue
            ch = data["choices"][0]
            content = ch["message"].get("content") or ""
            finish = ch.get("finish_reason")
            if not content.strip():
                max_tokens = min(max_tokens * 2, 4096)
                log("retry_empty", job=job_id, finish=finish, new_budget=max_tokens, attempt=attempt)
                continue
            try:
                parsed = parse_json(content)
            except Exception:
                log("retry_bad_json", job=job_id, attempt=attempt)
                continue
            if not valid_schema(parsed):
                log("retry_bad_schema", job=job_id, attempt=attempt)
                continue
            log("success", job=job_id, latency=lat, attempt=attempt, req_id=data.get("id"))
            return {"job": job_id, "ok": True, "latency": lat, "attempts": attempt}
        except asyncio.TimeoutError:
            log("retry_timeout", job=job_id, attempt=attempt)
            timeout = min(timeout * 2, 120)
            await asyncio.sleep(2)
        except Exception as e:
            log("retry_exception", job=job_id, err=str(e)[:60], attempt=attempt)
            await asyncio.sleep(2)
    return {"job": job_id, "ok": False, "reason": "exhausted", "attempts": 4}

async def phase(session, name, n, api_key, timeout=40):
    prompt = ("Return ONLY a valid JSON array of 5 objects with fields: protocol (string), "
              "risk (string), severity (integer 1-10). Topic: DeFi lending risks.")
    t = time.time()
    res = await asyncio.gather(*[resilient(session, f"{name}_{i}", prompt, api_key, timeout) for i in range(n)])
    ok = [r for r in res if r["ok"]]
    lats = [r["latency"] for r in ok]
    retried = [r for r in res if r["attempts"] > 1]
    print(f"\n{name}: {len(ok)}/{n} ok | retried: {len(retried)} | wall: {round(time.time()-t,1)}s"
          + (f" | avg lat: {round(statistics.mean(lats),1)}s" if lats else ""))
    failures = [r.get("reason") for r in res if not r["ok"]]
    if failures:
        print(f"  failure reasons: {failures}")
    return res

async def main():
    key = os.environ["AMBIENT_API_KEY"]
    open(LOG_FILE, "w").close()
    async with aiohttp.ClientSession() as s:
        print("=" * 55 + "\nProduction Simulation - Week 28\n" + "=" * 55)
        await phase(s, "baseline", 5, key)
        await phase(s, "concurrent", 20, key)
        print("\n--- Deliberate break 1: invalid API key ---")
        await phase(s, "bad_key", 3, "sk-invalid")
        print("\n--- Deliberate break 2: 3s timeout ---")
        await phase(s, "short_timeout", 3, key, timeout=3)
        print("\n--- Recovery: valid key and normal timeout ---")
        await phase(s, "recovery", 5, key)
    print("\nLog written to", LOG_FILE)

asyncio.run(main())

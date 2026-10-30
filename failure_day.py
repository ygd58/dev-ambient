import asyncio, aiohttp, os, time, json, hashlib, collections, statistics

KEY = os.environ["AMBIENT_API_KEY"]
URL = "https://api.ambient.xyz/v1/chat/completions"
H = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
Q = "What is 12 multiplied by 12? Answer with only the number."
LOG = []

async def req(s, body, timeout=40, url=URL, tag=""):
    t = time.time()
    try:
        async with s.post(url, headers=H, json=body, timeout=aiohttp.ClientTimeout(total=timeout)) as r:
            d = await r.json(content_type=None)
            ch = (d.get("choices") or [{}])[0]
            out = {"tag": tag, "status": r.status, "lat": round(time.time()-t, 2),
                   "finish": ch.get("finish_reason"), "content": (ch.get("message") or {}).get("content") or "",
                   "id": d.get("id"), "err": (d.get("error") or {}).get("message", "")[:90],
                   "tokens": (d.get("usage") or {}).get("completion_tokens")}
    except asyncio.TimeoutError:
        out = {"tag": tag, "status": "TIMEOUT", "lat": round(time.time()-t, 2), "content": "", "id": None, "err": "", "finish": None, "tokens": None}
    except Exception as e:
        out = {"tag": tag, "status": "NETERR", "lat": round(time.time()-t, 2), "content": "", "id": None, "err": str(e)[:60], "finish": None, "tokens": None}
    LOG.append(out)
    return out

def body(prompt=Q, model="ambient/large", mt=1024):
    return {"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": mt, "temperature": 0}

async def main():
    async with aiohttp.ClientSession() as s:
        print("1) Baseline")
        r = await asyncio.gather(*[req(s, body(), tag="base") for _ in range(3)])
        print("  ", [(x["status"], x["finish"], x["content"].strip()[:6]) for x in r])

        print("\n2) Gateway/error clarity")
        for name, b in [("unknown_model", body(model="no/such-model")),
                        ("missing_model", {"messages": [{"role": "user", "content": "hi"}], "max_tokens": 20}),
                        ("empty_messages", {"model": "ambient/large", "messages": [], "max_tokens": 20})]:
            x = await req(s, b, tag=name)
            print(f"   {name}: {x['status']} | {x['err'] or 'no message'}")

        print("\n3) Interrupted requests (1.5s client timeout), then immediate recovery")
        long = "Write a detailed 800-word essay on the history of money."
        it = await asyncio.gather(*[req(s, body(long, mt=1500), timeout=1.5, tag="interrupt") for _ in range(3)])
        print("   interrupted:", [x["status"] for x in it])
        rec = await asyncio.gather(*[req(s, body(), tag="after_interrupt") for _ in range(3)])
        print("   recovery   :", [(x["status"], x["content"].strip()[:6]) for x in rec])

        print("\n4) Duplicate requests (same deterministic prompt x6, concurrent)")
        dup = await asyncio.gather(*[req(s, body(), tag="dup") for _ in range(6)])
        outs = [x["content"].strip() for x in dup]
        ids = [x["id"] for x in dup]
        print("   distinct outputs:", len(set(outs)), "| distinct request ids:", len(set(ids)), "/", len(ids))

        print("\n5) Capacity burst (60 concurrent) and delayed responses")
        b60 = await asyncio.gather(*[req(s, body(), tag="burst") for _ in range(60)])
        print("   status codes:", dict(collections.Counter(x["status"] for x in b60)))
        lats = [x["lat"] for x in b60 if x["status"] == 200]
        if lats:
            med = statistics.median(lats)
            print(f"   median {med}s | max {max(lats)}s | slow (>2x median): {len([l for l in lats if l > 2*med])}")
        empty = [x for x in b60 if x["status"] == 200 and not x["content"].strip()]
        print("   200 with empty content:", len(empty), "| finish reasons:", dict(collections.Counter(x["finish"] for x in b60)))

        print("\n6) Network interruption (unreachable host), then retry on real endpoint")
        bad = await req(s, body(), timeout=4, url="https://api.ambient.xyz.invalid/v1/chat/completions", tag="netdown")
        print("   unreachable host:", bad["status"], bad["err"])
        ok = await req(s, body(), tag="after_net")
        print("   after:", ok["status"], ok["content"].strip()[:6])

    json.dump(LOG, open("failure_day_log.json", "w"), indent=2)
    print("\nLogged", len(LOG), "requests to failure_day_log.json")

asyncio.run(main())

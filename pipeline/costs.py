"""Summarise runs.jsonl: calls, cache hits, failures and measured latency per stage and model.

Run: python -m pipeline.costs            (prints a Markdown table, paste into COSTS.md)
"""
import json
from collections import defaultdict

from pipeline.common import RUNS


def main():
    rows = defaultdict(lambda: {"calls": 0, "cache": 0, "fail": 0, "lat": [], "audio": 0.0, "cost": 0.0})
    for line in RUNS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("provider") == "choice":
            continue
        key = (r.get("stage", "?"), r.get("provider", "?"), r.get("model", "?"))
        row = rows[key]
        if r.get("cache_hit"):
            row["cache"] += 1
            continue
        row["calls"] += 1
        ok = r.get("status") in (200, 0) or (r.get("status") is None and not r.get("error"))
        if not ok:
            row["fail"] += 1
        if ok and r.get("latency_s") is not None:
            row["lat"].append(r["latency_s"])
        row["audio"] += r.get("audio_s") or 0.0
        row["cost"] += r.get("cost_usd") or 0.0

    print("| Stage | Provider | Model | Calls | Failed | Cache hits | Mean latency (s) | Total latency (s) | Cost (USD) |")
    print("|---|---|---|---:|---:|---:|---:|---:|---:|")
    for (stage, provider, model), r in sorted(rows.items()):
        lat = r["lat"]
        mean = f"{sum(lat) / len(lat):.2f}" if lat else "-"
        print(f"| {stage} | {provider} | {model} | {r['calls']} | {r['fail']} | {r['cache']} | {mean} | "
              f"{sum(lat):.1f} | {r['cost']:.2f} |")


if __name__ == "__main__":
    main()

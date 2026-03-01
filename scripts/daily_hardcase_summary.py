#!/usr/bin/env python3
from __future__ import annotations
import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARD = ROOT / "data" / "logs" / "hard_cases.jsonl"
OUT = ROOT / "data" / "logs" / "daily_hardcase_summary.txt"

now = datetime.now().astimezone()
since = now - timedelta(days=1)

reasons = Counter()
samples = []
count = 0
if HARD.exists():
    for line in HARD.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        ts_raw = row.get("ts")
        try:
            ts = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
        except Exception:
            ts = now
        if ts < since:
            continue
        count += 1
        for r in row.get("reasons", []):
            reasons[r] += 1
        if len(samples) < 3:
            samples.append({
                "ts": ts.isoformat(),
                "target_l5": row.get("target_l5"),
                "reasons": row.get("reasons", []),
                "raw_text": (row.get("request", {}) or {}).get("raw_text", "")[:180],
            })

lines = []
lines.append(f"[Daily Hard Cases Summary] generated_at={now.isoformat()}")
lines.append(f"window: last_24h, total_cases={count}")
lines.append(f"top_reasons: {reasons.most_common(10)}")
lines.append("samples:")
for s in samples:
    lines.append(json.dumps(s, ensure_ascii=False))

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))

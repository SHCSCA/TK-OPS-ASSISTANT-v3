"""临时脚本：检查 docs 文件分布并筛选语义抽取范围。"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

detect = json.loads(Path("graphify-out/.graphify_detect.json").read_text(encoding="utf-8"))
files = detect.get("files", {})
code = files.get("code", [])
docs = files.get("document", [])
images = files.get("image", [])

print(f"code files: {len(code)}")
print(f"all docs: {len(docs)}")
print(f"images: {len(images)} (方案C：跳过)")

buckets: Counter[str] = Counter()
for f in docs:
    p = Path(f)
    parts = list(p.parts)
    if "docs" in parts:
        idx = parts.index("docs")
        bucket = "/".join(parts[idx : idx + 2]) if len(parts) > idx + 1 else "docs/"
    elif "apps" in parts:
        bucket = "apps/*"
    else:
        bucket = parts[0] if parts else "."
    buckets[bucket] += 1

print()
print("docs 分布：")
for k, v in buckets.most_common():
    print(f"  {k}: {v}")

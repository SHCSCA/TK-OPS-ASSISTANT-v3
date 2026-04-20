"""准备重建图谱：过滤 docs 范围，跑 AST，生成 subagent 分片清单。"""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(".")
OUT = Path("graphify-out")

detect = json.loads((OUT / ".graphify_detect.json").read_text(encoding="utf-8"))
files = detect.get("files", {})

code_files = files.get("code", [])
all_docs = files.get("document", [])

# 方案C：排除 graphify-out/ 下的自生成文档
def _keep_doc(p: str) -> bool:
    norm = p.replace("\\", "/")
    if "graphify-out/" in norm:
        return False
    return True

docs_for_semantic = [p for p in all_docs if _keep_doc(p)]

# 分片，每片 22 文件
CHUNK = 22
chunks = [docs_for_semantic[i : i + CHUNK] for i in range(0, len(docs_for_semantic), CHUNK)]

OUT.mkdir(exist_ok=True)
(OUT / ".graphify_chunks.json").write_text(
    json.dumps({"chunks": chunks, "total_docs": len(docs_for_semantic)}, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

# 准备 AST 抽取（所有代码文件）
(OUT / ".graphify_code_files.json").write_text(
    json.dumps(code_files, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print(f"AST 代码文件: {len(code_files)}")
print(f"语义抽取 docs: {len(docs_for_semantic)} (排除 graphify-out)")
print(f"分片数: {len(chunks)} (每片 ≤{CHUNK} 文件)")
for i, c in enumerate(chunks):
    print(f"  chunk {i+1}: {len(c)} 文件")

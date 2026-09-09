#!/usr/bin/env python3
"""从用户本地素材目录按清单导入原图；校验内容，不联网。"""
import argparse
import hashlib
import json
import shutil
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    args = p.parse_args()
    dest = Path(__file__).resolve().parents[1] / "assets" / "references"
    entries = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))["images"]
    ready = []
    for item in entries:
        source = args.source / item["original_filename"]
        if not source.is_file():
            source = args.source / item["filename"]
        if not source.is_file():
            raise SystemExit(f"缺少图{item['id']}：{item['original_filename']}")
        if hashlib.sha256(source.read_bytes()).hexdigest() != item["sha256"]:
            raise SystemExit(f"图{item['id']}与清单内容不一致；自有替代图请另行更新清单")
        ready.append((source,dest/item["filename"]))
    for src, target in ready:
        if src.resolve() != target.resolve():
            shutil.copy2(src,target)
    print(f"已验证并导入{len(ready)}张参考图片")


if __name__ == "__main__":
    main()

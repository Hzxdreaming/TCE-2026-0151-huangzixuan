#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
课题3 原始 CSV 只读质检（2026-11-14 版）

用法：python qc_raw.py            （默认检查脚本旁的 data/raw）
      python qc_raw.py data/raw   （也可显式给路径）

只检查、不改写任何原始文件；输出 质检汇总.csv 到项目 data/ 下。
判定：
  PASS               格式合格且独立取值 >= 1000
  FLAG               格式或数值异常（常量段过长 / 削顶 / 超 15 行 / 独立值不足）
  REVIEW_来源待核     文件名含 chart/digitize/source/verify/REBUILT/TEST/INVALID 等派生线索
  DUPLICATE          与另一个文件 MD5 完全相同
"""
import csv
import hashlib
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
RAW = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "raw"
OUT = ROOT / "data" / "质检汇总.csv"

FORMAL = re.compile(r"^C([1-5])_R(\d{2})\.csv$")
DERIVED = re.compile(r"(chart|digitize|source|verify|rebuilt|test|invalid|_old)", re.I)


def md5(path):
    return hashlib.md5(path.read_bytes()).hexdigest()


def check(path):
    rec = {"文件名": path.name, "大小_B": path.stat().st_size, "MD5": md5(path)}
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.reader(f))
        header = [h.strip() for h in rows[0]]
        data = [[float(c) for c in r] for r in rows[1:] if r and len(r) == 4]
        arr = np.asarray(data, dtype=float)
        t, a = arr[:, 0], arr[:, 1:4]
    except Exception as e:
        rec.update({"表头": "读取失败", "行数": 0, "独立三轴取值": 0, "判定": "FLAG",
                    "说明": str(e)[:120]})
        return rec

    rec["表头"] = ",".join(header)
    rec["行数"] = len(data)
    dts = np.diff(t)
    rec["dt种类"] = len(set(np.round(dts, 5))) if len(dts) else 0
    rec["时长_s"] = round(float(t[-1] - t[0]), 5) if len(t) else 0.0
    triples = [tuple(np.round(row, 5)) for row in a]
    rec["独立三轴取值"] = len(set(triples))

    # 最长连续重复段
    longest, cur = 1, 1
    for i in range(1, len(triples)):
        if triples[i] == triples[i - 1]:
            cur += 1
            longest = max(longest, cur)
        else:
            cur = 1
    rec["最长重复段"] = longest
    rec["超15行数"] = int(np.count_nonzero(np.abs(a) > 15.0))

    notes = []
    verdict = "PASS"
    if header != ["time", "ax", "ay", "az"]:
        notes.append("表头不符")
        verdict = "FLAG"
    if len(data) != 2000:
        notes.append("非 2000 点")
        verdict = "FLAG"
    if rec["dt种类"] != 1 or (len(dts) and abs(float(dts[0]) - 0.01) > 1e-6):
        notes.append("Δt 非 0.01")
        verdict = "FLAG"
    if rec["独立三轴取值"] < 1000:
        notes.append("独立值不足1000（疑零阶保持）")
        verdict = "FLAG"
    if longest > 200:
        notes.append("常量段>200行")
        verdict = "FLAG"
    if rec["超15行数"]:
        notes.append("存在超15行，原样保留不剔除")
    if DERIVED.search(path.name):
        notes.append("文件名含派生线索，来源待核")
        verdict = "REVIEW_来源待核"
    if not FORMAL.match(path.name):
        notes.append("非正式组命名")
        if verdict == "PASS":
            verdict = "REVIEW_来源待核"
    rec["判定"] = verdict
    rec["说明"] = "; ".join(notes) if notes else "合格"
    return rec


def main():
    if not RAW.is_dir():
        print("未找到目录：%s。未生成质检汇总.csv。" % RAW)
        return 0
    files = sorted(RAW.glob("*.csv"))
    if not files:
        print("目录内无 CSV。未生成质检汇总.csv。")
        return 0
    records = [check(p) for p in files]
    hashes = Counter(r["MD5"] for r in records)
    for r in records:
        if hashes[r["MD5"]] > 1:
            r["判定"] = "DUPLICATE"
            r["说明"] += "; 与其他文件 MD5 相同"

    cols = ["文件名", "大小_B", "MD5", "表头", "行数", "dt种类", "时长_s",
            "独立三轴取值", "最长重复段", "超15行数", "判定", "说明"]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(records)
    for r in records:
        print("%-38s %-20s 独立值=%-5s %s" % (r["文件名"], r["判定"], r["独立三轴取值"], r["说明"]))
    print("汇总写入：%s" % OUT)
    print("注意：PASS 只代表数值格式合格，不代表来源合法；来源待核/派生文件只放 evidence/。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
课题3 特征提取（A 版改版，2026-11-14 定稿）

!! 运行时点：2026-11-16。11/14 只入仓，禁止运行、禁止据此下结论。!!

- 只读 课题3-手机声振异常诊断仪/data/raw 下形如 C{1-5}_R{01-15}.csv 的正式组
- 稳态窗 2.00-18.00 s，逐通道减均值去直流（不在文件里删任何行）
- Welch 分段周期图：nperseg=1024 / noverlap=512 / nfft=1024 / hann / fs=100
- 频带 0-1 / 1-3 / 3-6 / 6-12 / 12-25 Hz（占比按 0-50 Hz 总功率归一化）
- 4 通道 x 12 维 = 48 维；输出 60 列 data/features.csv
- 目录为空 / 无合格文件：直接退出，不生成也不覆盖 features.csv

依赖：numpy（仅此一个）。原始 CSV 一个字节都不改。
"""
import csv
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "features.csv"

PATTERN = re.compile(r"^C([1-5])_R(\d{2})\.csv$")
BANDS = [(0.0, 1.0), (1.0, 3.0), (3.0, 6.0), (6.0, 12.0), (12.0, 25.0)]
BAND_NAMES = ["b0_1", "b1_3", "b3_6", "b6_12", "b12_25"]
CHANNELS = ["ax", "ay", "az", "amag"]

FS = 100.0
STEADY = (2.00, 18.00)
NPERSEG, NOVERLAP, NFFT = 1024, 512, 1024
DF = FS / NFFT  # 0.09765625 Hz

META_COLS = [
    "file", "condition", "replicate", "n_rows", "dt_s", "duration_s",
    "unique_triples", "steady_rows", "dc_ax", "dc_ay", "dc_az", "nyq_warn",
]


def read_csv(path):
    """返回 (表头, times, ax, ay, az)；不做任何数值修正。"""
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        raise ValueError("空文件")
    header = [h.strip() for h in rows[0]]
    if header != ["time", "ax", "ay", "az"]:
        raise ValueError("表头不是 time,ax,ay,az：%r" % header)
    data = []
    for r in rows[1:]:
        if not r or all(not c.strip() for c in r):
            continue
        if len(r) != 4:
            raise ValueError("存在非 4 列数据行")
        data.append([float(c) for c in r])
    arr = np.asarray(data, dtype=float)
    return arr[:, 0], arr[:, 1], arr[:, 2], arr[:, 3]


def welch_psd(x, fs=FS, nper=NPERSEG, nov=NOVERLAP, nfft=NFFT):
    """手写 Welch：hann 窗、去均值、分段 rfft、功率谱平均。避免 scipy 依赖。"""
    x = np.asarray(x, dtype=float)
    x = x - x.mean()
    win = 0.5 - 0.5 * np.cos(2.0 * np.pi * np.arange(nper) / (nper - 1))
    scale = fs * np.sum(win ** 2)
    step = nper - nov
    acc = None
    nseg = 0
    for start in range(0, len(x) - nper + 1, step):
        seg = x[start:start + nper] * win
        spec = np.fft.rfft(seg, n=nfft)
        psd = (np.abs(spec) ** 2) / scale
        psd[1:-1] *= 2.0  # 单边谱
        acc = psd if acc is None else acc + psd
        nseg += 1
    if nseg == 0:
        return np.zeros(nfft // 2 + 1), np.arange(nfft // 2 + 1) * (fs / nfft)
    return acc / nseg, np.arange(nfft // 2 + 1) * (fs / nfft)


def channel_features(x):
    """单通道 12 维：5 频带占比 + 主导频率 + RMS/方差/峰值/峭度/峰值因子/零交叉率。"""
    n = len(x)
    dc = float(x.mean())
    v = x - dc
    rms = float(np.sqrt(np.mean(v ** 2)))
    var = float(np.mean(v ** 2))
    peak = float(np.max(np.abs(v)))
    kurt = float(np.mean(v ** 4) / (var ** 2)) if var > 0 else 0.0
    crest = float(peak / rms) if rms > 0 else 0.0
    zcr = float(np.count_nonzero(np.diff(np.sign(v)) != 0) / (n - 1) * FS) if n > 1 else 0.0

    psd, freqs = welch_psd(x)
    usable = freqs <= 50.0
    total = float(np.sum(psd[usable]))
    ratios = []
    for lo, hi in BANDS:
        m = usable & (freqs >= lo) & (freqs < hi)
        ratios.append(float(np.sum(psd[m]) / total) if total > 0 else 0.0)
    # 主导频率：排除直流，限 0-50 Hz
    cand = usable & (freqs > 0)
    idx = np.argmax(np.where(cand, psd, -np.inf))
    dom = float(freqs[idx])
    return ratios + [dom, rms, var, peak, kurt, crest, zcr], dom


def process(path):
    t, ax, ay, az = read_csv(path)
    n = len(t)
    dts = np.diff(t)
    dt = float(np.median(dts)) if len(dts) else 0.0
    unique_triples = len({(round(a, 5), round(b, 5), round(c, 5)) for a, b, c in zip(ax, ay, az)})
    if unique_triples < 1000:
        print("  [跳过] 独立三轴取值仅 %d，疑为零阶保持派生：%s" % (unique_triples, path.name))
        return None

    m = (t >= STEADY[0]) & (t <= STEADY[1])
    if int(m.sum()) < NPERSEG:
        print("  [跳过] 稳态窗不足一个 nperseg：%s" % path.name)
        return None
    w_ax, w_ay, w_az = ax[m], ay[m], az[m]
    amag = np.sqrt(w_ax ** 2 + w_ay ** 2 + w_az ** 2)

    feats, doms = [], []
    for ch in (w_ax, w_ay, w_az, amag):
        f, d = channel_features(ch)
        feats.extend(f)
        doms.append(d)
    nyq_warn = 1 if max(doms) >= 40.0 else 0

    meta = [
        path.name, "C" + PATTERN.match(path.name).group(1), int(PATTERN.match(path.name).group(2)),
        n, round(dt, 5), round(float(t[-1] - t[0]), 5),
        unique_triples, int(m.sum()),
        round(float(w_ax.mean()), 5), round(float(w_ay.mean()), 5), round(float(w_az.mean()), 5),
        nyq_warn,
    ]
    return meta + feats


def main():
    if not RAW.is_dir():
        print("未找到 data/raw/，直接退出；未生成 features.csv。")
        return 0
    files = sorted(p for p in RAW.glob("*.csv") if PATTERN.match(p.name))
    if not files:
        print("data/raw/ 下没有合格命名的正式组（C{1-5}_R{01-15}.csv），直接退出；未生成 features.csv。")
        return 0

    header = META_COLS + [
        "%s_%s" % (ch, name)
        for ch in CHANNELS
        for name in BAND_NAMES + ["dom_hz", "rms", "var", "peak", "kurt", "crest", "zcr"]
    ]
    rows = []
    for p in files:
        print("处理 %s" % p.name)
        try:
            r = process(p)
        except Exception as e:
            print("  [跳过] 读取失败：%s" % e)
            continue
        if r is not None:
            rows.append(r)
    if not rows:
        print("没有任何组通过检查，直接退出；未生成 features.csv。")
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print("完成：%d 行写入 %s（%d 列）" % (len(rows), OUT, len(header)))
    print("提醒：nyq_warn=1 的组只作标注，不得写成物理解释；报告不得宣称识别出具体叶频。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

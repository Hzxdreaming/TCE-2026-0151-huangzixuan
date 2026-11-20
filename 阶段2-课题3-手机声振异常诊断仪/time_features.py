"""Time-domain feature extraction (method demo, no physical claims)."""
import csv
import re
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "time_features.csv"
PATTERN = re.compile(r"^C([1-5])_R(\d{2})\.csv$")
W0, W1 = 2.0, 18.0
CHANNELS = ("ax", "ay", "az", "amag")
FEATURES = ("mean", "std", "rms", "pp", "crest", "kurt", "skew", "zcr", "mav")


def feats(x):
    x = np.asarray(x, dtype=float)
    n = x.size
    mu = float(np.mean(x))
    sd = float(np.std(x))
    rms = float(np.sqrt(np.mean(x ** 2)))
    pp = float(np.max(x) - np.min(x))
    crest = float(np.max(np.abs(x)) / rms) if rms > 0 else 0.0
    if sd > 0:
        z = (x - mu) / sd
        kurt = float(np.mean(z ** 4) - 3.0)
        skew = float(np.mean(z ** 3))
    else:
        kurt = skew = 0.0
    s = np.sign(x - mu)
    zcr = float(np.sum(s[1:] * s[:-1] < 0) / (n - 1)) if n > 1 else 0.0
    mav = float(np.mean(np.abs(x - mu)))
    return (mu, sd, rms, pp, crest, kurt, skew, zcr, mav)


def main():
    rows = []
    for p in sorted(RAW.glob("*.csv")):
        m = PATTERN.match(p.name)
        if not m:
            continue
        t, ax, ay, az = [], [], [], []
        with p.open("r", encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                t.append(float(r["time"]))
                ax.append(float(r["ax"]))
                ay.append(float(r["ay"]))
                az.append(float(r["az"]))
        tt = np.asarray(t)
        a = np.asarray(ax)
        b = np.asarray(ay)
        c = np.asarray(az)
        amag = np.sqrt(a * a + b * b + c * c)
        mask = (tt >= W0) & (tt <= W1)
        data = {"ax": a[mask], "ay": b[mask], "az": c[mask], "amag": amag[mask]}
        if not bool(mask.any()):
            print("skip empty window:", p.name)
            continue
        out = {
            "group": p.stem,
            "class": "C" + m.group(1),
            "rep": "R" + m.group(2),
            "n": int(mask.sum()),
        }
        for ch in CHANNELS:
            for name, val in zip(FEATURES, feats(data[ch])):
                out[ch + "_" + name] = round(val, 6)
        rows.append(out)
        print("processed", p.name)
    if not rows:
        print("no input; time_features.csv NOT written")
        return
    cols = ["group", "class", "rep", "n"] + [
        ch + "_" + f for ch in CHANNELS for f in FEATURES
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print("done:", len(rows), "rows ->", OUT)
    print("reminder: stats are method demo only; no blade-frequency / physical claims")


if __name__ == "__main__":
    main()
"""
Extract exact data points from the vector charts in Ibrahim & Mohammed (2025), Batteries 11:257.

The charts are vector drawings, so no reading-by-eye is needed:
  * each data marker is an asterisk made of short line strokes in the series colour;
  * the marker centre = mean of its stroke end-points;
  * the y value comes from a linear map fitted through the y-axis tick marks;
  * the x value is the category label directly under the marker.

Usage: python extract_curves.py <pdf>
"""
import sys
import numpy as np
import pymupdf

RED = (1.0, 0.0, 0.0)            # "Experimentation" series
NAVY = (0.0, 0.102, 0.383)       # "Analytical" series
GREEN = (0.0, 0.696, 0.277)      # "Simulation" series


def same(c1, c2, tol=0.01):
    return c1 is not None and all(abs(a - b) < tol for a, b in zip(c1, c2))


def marker_centres(page, colour, region):
    x0, y0, x1, y1 = region
    pts = []
    for d in page.get_drawings():
        if not same(d.get("color"), colour):
            continue
        for it in d["items"]:
            if it[0] != "l":
                continue
            p, q = it[1], it[2]
            if np.hypot(p.x - q.x, p.y - q.y) > 8:        # long stroke = curve segment, not a marker
                continue
            mx, my = (p.x + q.x) / 2, (p.y + q.y) / 2
            if x0 <= mx <= x1 and y0 <= my <= y1:
                pts.append((mx, my))
    pts = np.array(pts)
    # cluster strokes belonging to the same asterisk (within 4 pt)
    centres, used = [], np.zeros(len(pts), bool)
    for i in range(len(pts)):
        if used[i]:
            continue
        near = np.hypot(*(pts - pts[i]).T) < 4
        used |= near
        centres.append(pts[near].mean(axis=0))
    return sorted(centres, key=lambda c: c[0])


def axis_ticks(page, region, axis_x_max, labels):
    """y-axis: pair numeric tick labels with their vertical centres; fit value = a*y + b."""
    ys, vals = [], []
    for b in page.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            for s in l["spans"]:
                t = s["text"].strip()
                x0, y0, x1, y1 = s["bbox"]
                if t in labels and x1 <= axis_x_max and region[1] - 12 <= y0 <= region[3] + 12:
                    ys.append((y0 + y1) / 2)
                    vals.append(float(t))
    a, b = np.polyfit(ys, vals, 1)
    resid = np.max(np.abs(np.polyval([a, b], ys) - vals))
    return a, b, resid


def x_categories(page, region, labels):
    """Tick labels under the x-axis, built character by character (some labels share one text run)."""
    cats = []
    for b in page.get_text("rawdict")["blocks"]:
        for l in b.get("lines", []):
            for s in l["spans"]:
                word, boxes = "", []
                for ch in s["chars"] + [{"c": " ", "bbox": (0, 0, 0, 0)}]:
                    if ch["c"].strip():
                        word += ch["c"]
                        boxes.append(ch["bbox"])
                        continue
                    if word in labels:
                        x0 = min(bb[0] for bb in boxes); x1 = max(bb[2] for bb in boxes)
                        y0 = min(bb[1] for bb in boxes)
                        if region[3] <= y0 <= region[3] + 14:
                            cats.append(((x0 + x1) / 2, float(word)))
                    word, boxes = "", []
    return sorted(cats)


def legend_band(page, region):
    """Vertical centre of the legend text row ('Experimentation' ...), to exclude legend sample markers."""
    for b in page.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            for s in l["spans"]:
                if "Experimentation" in s["text"]:
                    y = (s["bbox"][1] + s["bbox"][3]) / 2
                    if region[1] - 10 <= y <= region[3]:
                        return y
    return None


def extract(pdf, page_no, region, ylabels, xlabels, axis_x_max, series):
    page = pymupdf.open(pdf)[page_no - 1]
    a, b, resid = axis_ticks(page, region, axis_x_max, ylabels)
    cats = x_categories(page, region, xlabels)
    assert len(cats) == len(xlabels), f"found {len(cats)} of {len(xlabels)} x labels"
    ly = legend_band(page, region)
    out = {}
    for name, col in series.items():
        rows = []
        for cx, cy in marker_centres(page, col, region):
            if ly is not None and abs(cy - ly) < 4:
                continue                                   # legend sample marker, not data
            xc = min(cats, key=lambda c: abs(c[0] - cx))
            if abs(xc[0] - cx) > 2.0:
                continue
            rows.append((xc[1], a * cy + b, abs(xc[0] - cx)))
        assert len(rows) == len(xlabels), f"{name}: {len(rows)} points for {len(xlabels)} labels"
        out[name] = rows
    return out, resid


def save_csv(path, data):
    import csv
    xs = [r[0] for r in data["measured"]]
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["x_mm", "k_measured", "k_their_analytical", "k_their_FEM"])
        for i, x in enumerate(xs):
            w.writerow([int(x)] + [f"{data[s][i][1]:.4f}" for s in ("measured", "their_analytical", "their_FEM")])


if __name__ == "__main__":
    pdf = sys.argv[1]
    # Figure 17 (page 18): k vs vertical distance, y-axis 0..0.7
    f17, r17 = extract(pdf, 18, region=(196, 600, 450, 717),
                       ylabels={"0", "0.1", "0.2", "0.3", "0.4", "0.5", "0.6", "0.7"},
                       xlabels={str(v) for v in [32, 57, 82, 107, 132, 157, 182, 192, 212, 232, 252, 272, 292, 312]},
                       axis_x_max=196, series={"measured": RED, "their_analytical": NAVY, "their_FEM": GREEN})
    # Figure 20 (page 20): k vs horizontal offset at 100 mm gap, y-axis 0.1..0.35
    f20, r20 = extract(pdf, 20, region=(198, 110, 450, 246),
                       ylabels={"0.1", "0.15", "0.2", "0.25", "0.3", "0.35"},
                       xlabels={str(v) for v in [0, 10, 20, 30, 40, 50, 70, 90, 95, 100, 110, 120, 130]},
                       axis_x_max=198, series={"measured": RED, "their_analytical": NAVY, "their_FEM": GREEN})
    import os
    outdir = sys.argv[2] if len(sys.argv) > 2 else "."
    save_csv(os.path.join(outdir, "ibrahim2025_fig17_k_vs_gap.csv"), f17)
    save_csv(os.path.join(outdir, "ibrahim2025_fig20_k_vs_offset_gap100.csv"), f20)
    for title, data, r in [("FIG17 vertical distance (mm)", f17, r17), ("FIG20 horizontal offset (mm), gap 100 mm", f20, r20)]:
        print(f"\n{title}   [y-axis fit max residual {r:.2e}]")
        for name, rows in data.items():
            print(f"  {name}: n={len(rows)}")
            for x, y, dx in rows:
                print(f"     {x:6.0f}  {y:.4f}   (x-snap {dx:.2f} pt)")

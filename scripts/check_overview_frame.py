"""Reject zoomed-in MuJoCo frames. Exit 0 only if arena overview likely visible."""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path


def load_rgb(path: Path):
    try:
        from PIL import Image
    except ImportError:
        raise SystemExit("FAIL: Pillow required (pip install pillow)")
    im = Image.open(path).convert("RGB")
    return im, im.size


def score_overview(path: Path) -> tuple[bool, str]:
    im, (w, h) = load_rgb(path)
    x0 = min(int(w * 0.18), 280)
    y0 = int(h * 0.05)
    y1 = int(h * 0.92)
    view = im.crop((x0, y0, w, y1))
    vw, vh = view.size
    if vh < 200 or vw < 200:
        return False, "viewport too small"

    # Downsample for edge/color stats (stdlib-friendly).
    small = view.resize((max(40, vw // 8), max(40, vh // 8)))
    px = list(small.getdata())
    sw, sh = small.size

    # Edge energy from luminance diffs.
    def lum(p):
        return (p[0] * 299 + p[1] * 587 + p[2] * 114) / 1000.0

    edge_sum = 0.0
    edge_n = 0
    for y in range(sh):
        for x in range(sw):
            i = y * sw + x
            v = lum(px[i])
            if x + 1 < sw:
                edge_sum += abs(v - lum(px[i + 1]))
                edge_n += 1
            if y + 1 < sh:
                edge_sum += abs(v - lum(px[i + sw]))
                edge_n += 1
    edge = edge_sum / max(1, edge_n)

    # Quantized color diversity.
    keys = [((r // 32) << 10) | ((g // 32) << 5) | (b // 32) for r, g, b in px]
    n_colors = len(set(keys))

    # Zoomed frames: huge single-color dominance.
    top = Counter(keys).most_common(1)[0][1] / max(1, len(keys))

    ok = edge >= 6.0 and n_colors >= 18 and top <= 0.72
    detail = f"edge={edge:.2f} colors={n_colors} top={top:.2f} size={vw}x{vh}"
    return ok, detail


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: check_overview_frame.py <png> [png...]")
        return 2
    all_ok = True
    for arg in sys.argv[1:]:
        path = Path(arg)
        if not path.is_file():
            print(f"FAIL missing {path}")
            all_ok = False
            continue
        ok, detail = score_overview(path)
        print(f"{'PASS' if ok else 'FAIL'} {path.name} {detail}")
        all_ok = all_ok and ok
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

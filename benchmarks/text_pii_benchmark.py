# Copyright 2026 Ritesh Ambastha
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Synthetic on-screen text PII benchmark for RedactGuard (frame-level + end-to-end).

Usage (from the repo root, with packages/core installed):
    python benchmarks/text_pii_benchmark.py            # 100 frames + 30-scene video
    SEED=11 N=150 E2E=0 python benchmarks/text_pii_benchmark.py

Env vars: SEED, N (frames), E2E (1/0), E2E_N (scenes in the video), POLICY, OUT.
On Python 3.13+, pydub also needs `pip install audioop-lts`.

Generates frames with PII strings at known positions, runs RedactGuard's real
OCR and MSER detectors plus its ensemble vote, and measures per-instance recall
and false-positive spans. Then runs the full Orchestrator on a synthetic video
and independently checks how much PII is still readable after redaction.
"""
import json, os, random, re, string, sys, tempfile, time, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from redactguard_core.pipeline.ingest import Frame, DecodedMedia
from redactguard_core.detectors.text.ocr_detector import TesseractOcrDetector
from redactguard_core.detectors.text.mser_text_region_detector import MserTextRegionDetector
from redactguard_core.ensemble.voting import vote
from redactguard_core.detectors.common.pii_patterns import find_pattern_matches

SEED = int(os.environ.get("SEED", 7))
random.seed(SEED); np.random.seed(SEED)
W, H = 1280, 720
FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
FONTS = [f for f in FONTS if os.path.exists(f)]
DISTRACTORS = ["Weekly specials", "Aisle 7 - Snacks", "Store #42", "Buy 2 get 1 free",
               "Quarterly review", "Meeting notes", "Fresh produce", "Exit", "Open 24 hours",
               "Product roadmap", "Thank you for shopping", "Sale ends Sunday"]
FIRST = ["john", "maria", "li", "priya", "sam", "olga", "ahmed", "kate", "diego", "nina"]
DOMS = ["gmail.com", "example.com", "acme.org", "mail.net", "shop.io"]

def rnd_pii():
    t = random.choice(["email", "phone", "ssn", "credit_card"])
    d = lambda n: "".join(random.choice(string.digits) for _ in range(n))
    if t == "email":
        s = f"{random.choice(FIRST)}.{random.choice(FIRST)}{d(2)}@{random.choice(DOMS)}"
    elif t == "phone":
        s = random.choice([f"({d(3)}) {d(3)}-{d(4)}", f"{d(3)}-{d(3)}-{d(4)}", f"{d(3)}.{d(3)}.{d(4)}"])
    elif t == "ssn":
        s = f"{d(3)}-{d(2)}-{d(4)}"
    else:
        s = " ".join(d(4) for _ in range(4))
    return t, s

def background(kind):
    if kind == "solid":
        c = tuple(int(x) for x in np.random.randint(0, 256, 3))
        return Image.new("RGB", (W, H), c)
    if kind == "gradient":
        a, b = np.random.randint(0, 256, 3), np.random.randint(0, 256, 3)
        t = np.linspace(0, 1, W)[None, :, None]
        arr = (a * (1 - t) + b * t).repeat(H, 0).astype(np.uint8)
        return Image.fromarray(arr)
    # cluttered: blurred random blocks + noise, a rough stand-in for real footage
    img = Image.new("RGB", (W, H), tuple(int(x) for x in np.random.randint(60, 200, 3)))
    dr = ImageDraw.Draw(img)
    for _ in range(40):
        x, y = random.randint(0, W), random.randint(0, H)
        dr.rectangle([x, y, x + random.randint(30, 300), y + random.randint(30, 200)],
                     fill=tuple(int(v) for v in np.random.randint(0, 256, 3)))
    img = img.filter(ImageFilter.GaussianBlur(3))
    arr = np.array(img).astype(np.int16) + np.random.normal(0, 12, (H, W, 3)).astype(np.int16)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

def contrast_color(bg_px, low):
    lum = 0.299 * bg_px[0] + 0.587 * bg_px[1] + 0.114 * bg_px[2]
    if low:
        delta = 70
        v = int(lum + delta if lum < 128 else lum - delta)
        return (v, v, v)
    return (0, 0, 0) if lum > 128 else (255, 255, 255)

def place(dr, occupied, text, font):
    l, t, r, b = dr.textbbox((0, 0), text, font=font)
    tw, th = r - l, b - t
    for _ in range(50):
        x, y = random.randint(20, max(21, W - tw - 20)), random.randint(20, max(21, H - th - 20))
        box = (x, y, x + tw, y + th)
        if all(box[2] + 20 < o[0] or box[0] > o[2] + 20 or box[3] + 15 < o[1] or box[1] > o[3] + 15 for o in occupied):
            occupied.append(box)
            return x - l, y - t, box
    return None

def make_frame(n_pii, n_dist):
    kind = random.choice(["solid", "gradient", "cluttered"])
    img = background(kind)
    dr = ImageDraw.Draw(img)
    occupied, gts = [], []
    items = [("pii",) + rnd_pii() for _ in range(n_pii)] + [("dist", None, random.choice(DISTRACTORS)) for _ in range(n_dist)]
    random.shuffle(items)
    low = random.random() < 0.2
    for role, ptype, text in items:
        font = ImageFont.truetype(random.choice(FONTS), random.randint(22, 48))
        p = place(dr, occupied, text, font)
        if not p:
            continue
        x, y, box = p
        cx, cy = min(W - 1, (box[0] + box[2]) // 2), min(H - 1, (box[1] + box[3]) // 2)
        col = contrast_color(img.getpixel((cx, cy)), low)
        dr.text((x, y), text, fill=col, font=font)
        if role == "pii":
            gts.append({"type": ptype, "text": text, "box": [box[0] / W, box[1] / H, (box[2] - box[0]) / W, (box[3] - box[1]) / H]})
    return img, gts, kind, low

def overlap(a, b):
    ax0, ay0, aw, ah = a; bx0, by0, bw, bh = b
    ix = max(0, min(ax0 + aw, bx0 + bw) - max(ax0, bx0)); iy = max(0, min(ay0 + ah, by0 + bh) - max(ay0, by0))
    return ix * iy

def frame_bench(n_frames):
    ocr, mser = TesseractOcrDetector(), MserTextRegionDetector()
    stats = {k: 0 for k in ["gt", "ocr", "mser", "vote1", "vote2", "fp_vote1", "fp_vote2", "fp_mser", "fp_ocr",
                            "clean_frames", "clean_fp_vote1", "clean_fp_vote2"]}
    by_type = {}
    frames = []
    for i in range(n_frames):
        clean = i % 5 == 4  # every 5th frame has no PII at all, only ordinary text
        img, gts, kind, low = make_frame(0 if clean else random.randint(1, 3), random.randint(1, 3))
        frames.append((img, gts))
        media = DecodedMedia(source_file="synthetic", frames=[Frame(timestamp_s=float(i), image=img)])
        r_ocr, r_mser = ocr.detect(media), mser.detect(media)
        v1, v2 = vote(r_ocr + r_mser, 1), vote(r_ocr + r_mser, 2)
        boxes = lambda rs: [r.bbox for r in rs if r.bbox is not None]
        for g in gts:
            stats["gt"] += 1
            bt = by_type.setdefault(g["type"], {"gt": 0, "ocr": 0, "mser": 0, "vote2": 0})
            bt["gt"] += 1
            for name, bs in [("ocr", boxes(r_ocr)), ("mser", boxes(r_mser)), ("vote1", boxes(v1)), ("vote2", boxes(v2))]:
                if any(overlap(b, g["box"]) > 0 for b in bs):
                    stats[name] += 1
                    if name in bt:
                        bt[name] += 1
        def fp(bs):
            return sum(1 for b in bs if not any(overlap(b, g["box"]) > 0 for g in gts))
        stats["fp_vote1"] += fp(boxes(v1)); stats["fp_vote2"] += fp(boxes(v2))
        stats["fp_mser"] += fp(boxes(r_mser)); stats["fp_ocr"] += fp(boxes(r_ocr))
        if clean:
            stats["clean_frames"] += 1
            stats["clean_fp_vote1"] += 1 if v1 else 0
            stats["clean_fp_vote2"] += 1 if v2 else 0
        print(f"frame {i+1}/{n_frames}", file=sys.stderr, flush=True)
    return stats, by_type, frames

def e2e(frames, outdir):
    """Full Orchestrator.run on a video built from the frames (2 s each, 2 fps)."""
    from redactguard_core.pipeline.policy import load_policy
    from redactguard_core.pipeline.orchestrator import Orchestrator
    fdir = os.path.join(outdir, "frames"); os.makedirs(fdir, exist_ok=True)
    k = 0
    for img, _ in frames:
        for _ in range(4):  # 2 seconds at 2 fps
            img.save(os.path.join(fdir, f"{k:05d}.png")); k += 1
    src = os.path.join(outdir, "synthetic.mp4"); out = os.path.join(outdir, "redacted.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "2", "-i", os.path.join(fdir, "%05d.png"),
                    "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", src], check=True)
    default_policy = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "policies", "ccpa_v1.yaml")
    policy = load_policy(os.environ.get("POLICY", default_policy))
    policy.pii_types["face"].enabled = False
    policy.pii_types["audio"].enabled = False
    t0 = time.time()
    report = Orchestrator(policy, sample_fps=0.5).run(src, out)
    dt = time.time() - t0
    # independent residual check: OCR each redacted frame, look for the exact PII strings
    rdir = os.path.join(outdir, "redacted_frames"); os.makedirs(rdir, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", out, "-vf", "fps=0.5", os.path.join(rdir, "%05d.png")], check=True)
    import pytesseract
    norm = lambda s: re.sub(r"[^0-9a-z@.]", "", s.lower())
    total = readable_before = readable_after = 0
    rfiles = sorted(os.listdir(rdir))
    for idx, (img, gts) in enumerate(frames):
        if idx >= len(rfiles):
            break
        before = norm(pytesseract.image_to_string(img))
        after = norm(pytesseract.image_to_string(Image.open(os.path.join(rdir, rfiles[idx]))))
        for g in gts:
            total += 1
            readable_before += norm(g["text"]) in before
            readable_after += norm(g["text"]) in after
    return {
        "seconds": round(dt, 1),
        "unresolved": report.unresolved,
        "passes": [p.model_dump() if hasattr(p, "model_dump") else dict(p) for p in report.verification_passes],
        "pii_instances": total,
        "ocr_readable_before": readable_before,
        "ocr_readable_after": readable_after,
    }

if __name__ == "__main__":
    n = int(os.environ.get("N", 100))
    outdir = os.environ.get("OUT", tempfile.mkdtemp())
    stats, by_type, frames = frame_bench(n)
    res = {"seed": SEED, "frames": n, "frame_level": stats, "by_type": by_type}
    if os.environ.get("E2E", "1") == "1":
        res["end_to_end"] = e2e(frames[: int(os.environ.get("E2E_N", 30))], outdir)
    print(json.dumps(res, indent=2))

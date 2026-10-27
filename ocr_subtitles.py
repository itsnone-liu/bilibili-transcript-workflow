#!/usr/bin/env python3
"""本地零token硬字幕OCR：mp4 → 底部条带抽帧 → dhash去重 → RapidOCR → SRT
用法: python3 ocr_subtitles.py <video.mp4> <out.srt> [底部比例=0.2] [fps=2]
"""
import sys, os, subprocess, glob, hashlib, json, re, shutil
from PIL import Image
import numpy as np
from rapidocr_onnxruntime import RapidOCR
import os

VIDEO, OUT_SRT = sys.argv[1], sys.argv[2]
BOTTOM = float(sys.argv[3]) if len(sys.argv) > 3 else 0.12
FPS = float(sys.argv[4]) if len(sys.argv) > 4 else 1.5

# 广告/引流水印黑名单（识别到即丢弃）
AD_PAT = re.compile(r'扫码|威信|微信|头像|敲重点|包村|投降|拥|关注|订阅|点赞|收藏|转发|简介|私聊|领取|资料|教程同款|抖音|快手|口令')

FDIR = OUT_SRT + '.frames'
if os.path.exists(FDIR): shutil.rmtree(FDIR)
os.makedirs(FDIR)

# 1) 教程录屏的文字可能位于画面中央，因此保留主要内容区，裁掉播放器/软件外框。
vf = "crop=iw*0.82:ih*0.78:iw*0.09:ih*0.10,scale=960:540:flags=bicubic"
r = subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', VIDEO,
                    '-vf', vf, '-r', str(FPS), '-q:v', '5',
                    os.path.join(FDIR, 'f_%06d.jpg')], capture_output=True, text=True)
if r.returncode != 0:
    print('ffmpeg err:', r.stderr[-300:]); sys.exit(1)
frames = sorted(glob.glob(os.path.join(FDIR, 'f_*.jpg')))
print(f'抽帧 {len(frames)} 张 @ {FPS}fps 底部{int(BOTTOM*100)}%')

def dhash(path, size=16):
    im = Image.open(path).convert('L').resize((size+1, size), Image.LANCZOS)
    a = np.asarray(im, dtype=np.int16)
    return (a[:, 1:] > a[:, :-1])

def ham(h1, h2): return int((h1 ^ h2).sum())

# 2) 相邻去重（hamming 阈值）选关键帧
last = None; keys = []
for f in frames:
    h = dhash(f)
    if last is None or ham(last, h) > 14:
        keys.append(f); last = h
print(f'去重后待OCR: {len(keys)} 帧')

# 3) RapidOCR
ocr = RapidOCR(det_use_cuda=False, intra_op_num_threads=max(1,(os.cpu_count() or 4)//4), inter_op_num_threads=1)
entries = []  # (t, text)
for i, f in enumerate(keys):
    n = int(os.path.basename(f)[2:-4])
    t = (n - 1) / FPS
    res, _ = ocr(f)
    if not res: continue
    lines = []
    for box, txt, conf in res:
        if conf < 0.6: continue
        txt = txt.strip()
        if not txt or len(txt) < 2: continue
        # 仅保留字幕区域中心横向范围，排除录屏软件左右侧边栏/UI
        xcenter = sum(pt[0] for pt in box) / len(box)
        if xcenter < 80 or xcenter > 640: continue
        if AD_PAT.search(txt): continue
        lines.append(txt)
    if lines:
        entries.append((t, ' '.join(lines)))
    if (i+1) % 50 == 0: print(f'  OCR进度 {i+1}/{len(keys)}')

# 4) 合并相邻同文 → SRT条目
merged = []
for t, txt in entries:
    norm = re.sub(r'\W+', '', txt)
    if merged and norm == merged[-1]['norm'] and t - merged[-1]['to'] < 1.6:
        merged[-1]['to'] = t + 1.0 / FPS + 0.3
    else:
        merged.append({'from': t, 'to': t + 1.0 / FPS + 0.5, 'norm': norm, 'text': txt})

def ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = int(t % 60); ms = int(round((t - int(t)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

with open(OUT_SRT, 'w', encoding='utf-8') as fp:
    for i, e in enumerate(merged, 1):
        if e['to'] - e['from'] < 0.4: e['to'] = e['from'] + 0.8
        fp.write(f"{i}\n{ts(e['from'])} --> {ts(e['to'])}\n{e['text']}\n\n")

json.dump(merged, open(OUT_SRT + '.json', 'w'), ensure_ascii=False)
print(f'完成: {len(merged)} 条字幕 → {OUT_SRT}')
shutil.rmtree(FDIR)

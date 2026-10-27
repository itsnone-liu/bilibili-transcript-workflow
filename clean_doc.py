#!/usr/bin/env python3
"""字幕 → 书面阅读文档：去广告水印、去片头曲、去语气词、折叠重复、按停顿分段"""
import json, re, sys

AD_PAT = re.compile(r'扫码|威信|微信|头像|敲重点|包村|投降|关注我|点个关注|一键三连|同款教程|领取资料|私聊我')
LYRIC_PAT = re.compile(r'有谁懂得|迷迷糊糊|天地初开|爱是|神仙也| euler|回首|今生今世|皆缘|沦海|沧海一声笑')
FILL_ONLY = re.compile(r'^(呃+|啊+|嗯+|哦+|噢+|哈+|嘛+|呢+|吧+|啦+|呀+|欸+|诶+|对+|是+|好+的*|行+|OK|ok|emm+|em+|mm+|嘿+|喂+[，。!！~～ ]*)+$')
STRIP_END = re.compile(r'[，,。.！!？?~～\s]*(啊|呀|嘛|呢|吧|啦|哦|噢|嗯|哈|对吧|是吧|好吧|对了对了)([，,。.！!？?\s]*)$')
PARA_MARK = re.compile(r'^(首先|然后|接下来|下面|最后|第[一二三四五六七八九十\d]+[步、章课]|我们(现在|先|再)|那么现在|好的那|大家好)')

TITLES = {
    1: 'AI短剧制作基础思路', 2: 'AI短剧剧本脚本创作', 3: 'AI人物造型设计',
    4: '真人短剧分镜头图片制作', 5: '真人短剧视频生成', 6: '使用Seedance 2.0模型制作短剧视频',
    7: '真人短剧视频配音配乐', 8: '真人短剧视频剪辑成片',
}

def norm(s): return re.sub(r'[\W_]+', '', s)

def clean_lines(entries, head_guard=60.0):
    """entries: [{from,to,content/text}] -> 清洗后的 [{from,to,text}]"""
    out = []
    for e in entries:
        t = (e.get('content') or e.get('text') or '').strip()
        t = re.sub(r'\s*\n\s*', ' ', t)
        if not t: continue
        if AD_PAT.search(t): continue
        if e.get('from', 0) < head_guard and LYRIC_PAT.search(t): continue
        if FILL_ONLY.match(t): continue
        # 句中纯语气词塌缩
        t = re.sub(r'(呃+|嗯+|emm+)', '', t)
        t = re.sub(r'([，,。.!！?？\s])(啊|呀|嘛|呢|吧|啦|哦|噢|嗯|哈)(?=[，,。.!！?？\s]|$)', r'\1', t)
        m = STRIP_END.search(t)
        if m: t = t[:m.start()].rstrip('，,。.！!？? ') 
        t = re.sub(r'[，,]{2,}', '，', t).strip(' ，,。.!！?？')
        if len(t) < 2: continue
        if out and norm(t) == out[-1]['norm']:
            out[-1]['to'] = e.get('to', out[-1]['to']); continue
        out.append({'from': e.get('from', 0), 'to': e.get('to', 0), 'norm': norm(t), 'text': t})
    return out



def _lev(a, b, cap=3):
    if abs(len(a)-len(b)) > cap: return cap+1
    prev = list(range(len(b)+1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j]+1, cur[j-1]+1, prev[j-1]+(ca != cb)))
        if min(cur) > cap: return cap+1
        prev = cur
    return prev[-1]

def fuzzy_merge(lines, cap=2):
    out = []
    for ln in lines:
        if out:
            a, b = out[-1], ln
            d = _lev(a['norm'], b['norm'])
            if d <= cap and (b['from'] - a['to']) < 2.0:
                keep = a['text'] if len(a['text']) >= len(b['text']) else b['text']
                a['text'], a['to'] = keep, max(a['to'], b['to'])
                if len(b['text']) > len(a['text']): a['text'] = b['text']
                continue
        out.append(dict(ln))
    return out

def drop_ui_noise(lines, min_rep=6):
    from collections import Counter
    c = Counter(l['norm'] for l in lines if len(l['text']) <= 20)
    bad = {k for k, v in c.items() if v >= min_rep}
    return [l for l in lines if l['norm'] not in bad], len(bad)

def to_paragraphs(lines, gap=3.0):
    paras, cur = [], []
    for ln in lines:
        if cur and (ln['from'] - cur[-1]['to'] > gap or (len(cur) > 2 and PARA_MARK.match(ln['text']))):
            paras.append(cur); cur = []
        cur.append(ln)
    if cur: paras.append(cur)
    out = []
    for p in paras:
        s = ''
        for ln in p:
            t = ln['text']
            s = (s + t) if s.endswith(('：', ':', '、')) or not s else (s + ('' if s.endswith(('。', '！', '？', '.', '!', '?')) else '。') + t)
        out.append(s + '。' if not s.endswith(('。', '！', '？')) else s)
    return out

def main():
    pages = {p['page']: p for p in json.load(open('pages.json'))}
    md = ['# 《神雕侠侣》AI真人短剧制作教程', '',
          '> 全 8 集文字整理版 · 来源：哔哩哔哩 BV1mJMC6oEXC',
          '> 全文由视频画面硬字幕本地 OCR 提取（不调用云端模型）；已去除片头曲、广告水印、重复字幕和口头填充词，并按时间间隔分段。OCR 个别错字可能存在，疑难处请对照视频。', '']
    stats = []
    for pc in range(1, 9):
        raw = json.load(open(f'P{pc}_ocr.srt.json'))
        src = '本地OCR'
        lines = clean_lines(raw)
        lines = fuzzy_merge(lines)
        lines, nbad = drop_ui_noise(lines)
        paras = to_paragraphs(lines)
        dur = pages[pc]['duration']
        md += [f'## 第{pc}集　{TITLES[pc]}', '', f'*（时长 {dur//60} 分 {dur%60} 秒 · {src} · 原文 {len(raw)} 行 → 整理后 {len(paras)} 段）*', '']
        md += [p + '\n' for p in paras]
        stats.append((pc, src, len(raw), len(paras)))
    open('教程整理版.md', 'w', encoding='utf-8').write('\n'.join(md))
    for pc, src, a, b in stats: print(f'P{pc} [{src}] {a}行 → {b}段')
    with open('教程整理版.md', encoding='utf-8') as f:
        nlines = sum(1 for _ in f)
    print('文档: 教程整理版.md,', nlines, '行')

if __name__ == '__main__':
    main()

# bilibili-transcript-workflow

可复用的 B 站字幕获取与整理 Agent Skill：先检查 B 站原生字幕并校验完整性；有可用原生字幕时直接整理，跳过 OCR；仅在缺字幕/字幕不可得/不完整的分P使用本地硬字幕 OCR。

## 安装

将 `SKILL.md` 放入支持 Agent Skills 规范的技能目录，例如：

```bash
mkdir -p ~/.agents/skills/bilibili-transcript-workflow
cp SKILL.md ~/.agents/skills/bilibili-transcript-workflow/SKILL.md
```

部分 Harness 需要重启或重新扫描 skills。

## 处理原则

1. 查询真实分P/合集清单，按分P处理；
2. 优先获取、验证原生人工/AI字幕轨；
3. 只有特定分P缺少可用原生字幕时才本地 OCR；
4. 将字幕校订为书面稿，保留内容、不确定处标注待核；
5. 导出 Markdown/DOCX/SRT，并标明每集来源。

详见 [SKILL.md](SKILL.md)。

## 安全

不要将 SESSDATA、Cookie、API 密钥、用户下载的视频或私人字幕内容提交 Git。曾在聊天中暴露的登录 Cookie 应注销/刷新。

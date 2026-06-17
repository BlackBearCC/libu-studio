# Prompts Log — 强制落地约定

每次 generation 跑完（不管走 Playwright path-a / path-a.alt / path-a.pre 还是 libtv CLI path），**必须**把这次的 prompt + 源 URL + 状态追加到对应 series 的 `_prompts_log.md`。**不要等用户提醒**——用户原话"这样我就不用每次手动提醒你了"，把这件事内化成 skill 默认行为。

## 文件位置

按 series 分目录，落在 `~/Documents/leo/libu-studio/work/<series>/_prompts_log.md`。`<series>` = 角色 slug + 用途，例：

- `poka-anim` — Poka 桌宠所有动画素材
- `marvin-anim` — Marvin 桌宠所有动画
- `<slug>-icons` — 某角色的 UI icon
- `<slug>-portrait` — 立绘 / 头像

如果对应目录不存在就先 `mkdir -p`。这与 `libu-studio/lab.db` 的 `characters.slug` 字段对齐。

## Schema（按 phase 分段）

每个 phase 是一个二级标题 `## Phase N: <用途> <动画名> (<风格/动作>)`。例：

```markdown
## Phase 4: 挂边 idle attached_idle_left / attached_idle_right (chibi 探头偷看)

桌宠走到屏幕左 / 右边缘自动 attach、或拖动到边缘 < 120px 释放磁吸吸附时播放的 loop 动画。...

**通用规格**: LibTV (Seedance 2.0, 后端 agent 编排) / 5s @24fps / 834×1112 / 智能比例 / 无配音 / 纯绿色背景 / image2image i2v
**参考图**: `/path/to/poka_real_standing.png`（说明来源），OSS `https://libtv-res.liblib.art/claw/.../xxx.png`
```

每个具体动画作品是三级标题 `### <动画名> (<可选: 弃用版本说明>)`：

```markdown
### 最终版 attached_idle_right (i2v 一次出, 直接喂参考图)
- **prompt**:
  > <prompt 全文，开头用 > 起 quote block 折行可读>
- **源 mp4 URL**: `https://libtv-res.liblib.art/.../xxx.mp4`
- **后处理**: <抽帧 / 抠绿参数 / wall kill 列号 / 输出 webp 张数等关键决策>
- **lab 母本**: `libu-studio/work/<series>/<name>/` 或"暂未留 mp4 母本"
- **Godot 注入**: `apps/godot-pet/assets/character-design/<slug>/anim/<name>/` (N 帧)
- **状态**: ✅ 完工 / ⚠️ 试错弃用 / 🔄 重生中
```

弃用版本也要记，配 reason，避免下次回头踩坑。例如：

```markdown
### 弃用版本 (不要回退)
- v1 「侧身扶虚空墙」(右手向身后伸出五指撑墙) — 被用户否决 "设计的动作也不好,不可爱,不像二次元", 太成熟不萌
- nebula t2i 先出参考图再 i2v 路线 — 被用户否决 "不要参考图了直接动画"
- prompt 含 "偶尔嘴角轻微上扬" — 模型过度演绎成嘴巴持续闪动
```

## 什么必须记，什么不要记

✅ **必须记**：
- prompt 全文（包括给后端 Agent 的"imageList 必须包含 URL"那种修饰语，未来翻账要用）
- 源 mp4 / 图片 URL（防 CDN 失效前能再下一次）
- 关键后处理参数（chromakey HSV 范围、wall kill 列号、抽帧 drop 数）
- 用户的"否决理由"原话（如 "嘴巴一动一动"、"不像二次元"、"露出来太多"）——这是下次写 prompt 的最重要锚点
- 最终落地路径（Godot anim 目录、frame_count、fps）
- 状态 emoji（✅ / ⚠️ / 🔄）

❌ **不要记**：
- 积分消耗 / 限免剩余次数（[[feedback_dont_fuss_credits]]）
- 时间戳 / 哪天跑的（lab.db 有 created_at；git log 有提交时间）
- 调试中的中间产物（v2 v3 v4 chromakey 调参）—— 只留最终版参数，过程注释折在文末"复盘"段
- 用户的私聊原话（除了否决理由这种"决策记录"）

## 触发时机

把 append 这件事做成**生成流水线的内置最后一步**，不依赖用户提醒：

```
1. 上传 / 传话                                  done
2. 等结果 → 拿 mp4 URL                          done
3. 抽帧 / 抠绿 / despill / WebP                  done
4. Godot / target 项目注入                       done
5. ★ append prompts log（本步） ★                ← 这里
6. （optional）lab.py gen 入 db
7. 报告用户
```

如果步骤 5 漏了，等于这次的 prompt 工程经验丢了，下次又得从零试错。

## 多人协作场景

libu-studio 不在 git 里（`work/` 是 gitignore），所以这是单机 / 单 contributor 的笔记本。如果你是别的 contributor、想跨机同步，就把 `~/Documents/leo/libu-studio/work/<series>/_prompts_log.md` 单独同步（rsync / 私有 git repo），不要靠 libu-studio。

## 相关

- 角色 slug 列表：`sqlite3 ~/Documents/leo/libu-studio/lab.db "SELECT slug FROM characters;"`
- 历史成功 prompt 查询（结构化版本，给 SQL 同学）：
  ```sql
  SELECT t.name, g.prompt FROM generations g
  JOIN anim_tasks t ON g.task_id=t.id
  WHERE t.character_slug='<slug>' AND g.chosen=1
  ORDER BY t.id;
  ```
- 历史 prompts 笔记本（给"翻最近的"看体感的）：`~/Documents/leo/libu-studio/work/<series>/_prompts_log.md`

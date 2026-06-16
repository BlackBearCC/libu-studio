# 阶段 A.libtv — LibTV CLI（官方 `libtv` 命令行）

> ⚠️ **2026-06 起**：旧的 agent-im OpenAPI（`/openapi/session` + `LIBTV_ACCESS_KEY`）**已被官方下线**，
> 调用只返回 `{code:0, message:"LibTV Skill 已升级为 LibTV CLI"}`。本路径已迁移到官方 `libtv` CLI，
> 旧的 `scripts/libtv/*.py` 客户端已删除，**不要再用**。

适用：容器 / headless / 后台 / 想全后台不抢焦点（[[feedback_no_focus_steal]]）/ 复杂编排。
官方 `libtv` 二进制直接操作 LibTV 画布（项目 / 节点 / 模型 / 工作流 DAG），出片同样得 mp4，下游 B/C/D 流水线不变。

## 安装

```bash
curl -sSL https://liblibai-web-static.liblib.cloud/cli/latest/install-libtv-cli.sh | bash
# 二进制落在 ~/.libtv/libtv（Windows ~/.libtv/libtv.exe）；不想改 PATH 加 LIBTV_CLI_SKIP_PROFILE=1，自己用全路径调
```

完整命令手册（`commands/` `node-types/` `examples/`）在官方 libtv-cli skill 包里：
`https://liblibai-web-static.liblib.cloud/cli/<version>/libtv-cli-skill.zip`。子命令以 `libtv <cmd> --help` 实际输出为准。

## 登录（凭据，不再是 access key）

新版凭据 = 浏览器 `usertoken` 同源，存 `~/.libtv/credentials.json`。

```bash
libtv login web                          # 起本机服务 + 打开/打印登录链接，浏览器登录后回调本机写凭据
libtv login phone -p <手机号>            # 发短信
libtv login phone -p <手机号> -c <验证码> # 带验证码完成
libtv account info                       # 验证已登录
```

**远程机（容器 / Windows GPU 机）没有桌面浏览器**：在有登录态的机器（如本人 Mac）跑 `libtv login web --open`
生成 `~/.libtv/credentials.json`，再把这个文件**拷到远程机的 `~/.libtv/credentials.json`**（同一人账号通用）。
旧的 `sk-libtv-...` access key 新版直接 401，别再试。

## 标准工作流（i2v 图生视频）

绑定项目 → 上传参考图建资源节点 → 建 video 节点连参考图 → 触发生成 → 轮询取 mp4。

```bash
cd <工作目录>                            # .libtv/project.json 落在这里
libtv project list                       # 看现有项目 UUID
libtv project use <项目UUID>             # 绑定项目

# 上传绿幕参考图（建 image 资源节点）。偶发 "fetch failed" = 网络抖动，重试 1-3 次即可
libtv upload standing_ref -t image --resource ./poka_greenscreen.png

# 建 video 节点 + 连参考图(--left) + 触发生成(--run)，一条搞定
libtv node create poka_sit -t video \
  --set model=star-video2 \
  --set modeType=singleImage2video \
  --set ratio=3:4 --set duration=5 --set enableSound=off \
  --prompt "参考图首帧站立 → 自然瘫坐到地上 → 保持瘫坐做小幅 idle …" \
  --left standing_ref --run

libtv node poka_sit                      # 轮询：节点 data.url 出现 .mp4 即完成
```

- **模型**：`libtv model search --type video`（如 `star-video2` = Seedance 2.0）；某模型支持哪些
  `modeType` / 字段见 `libtv model <modelKey>`。
- **i2v 单图模式用 `singleImage2video`**：锁定首帧=参考图、模型自演动作。比旧的 `frames2video`（首尾帧）
  **更不容易出现"整体缩放"**——首尾帧若两张图角色尺寸不一致，模型会退化成整体缩放（人变小）而非演出姿态变化。
- prompt 三铁律继承 [path-a-alt-text-to-video.md](path-a-alt-text-to-video.md)：不写时间戳、**不描述外观/五官/服装**
  （靠参考图锚定）、不描述次级部件运动；嘴不动要显式写"嘴巴始终闭合不动"；要锁大小写"全程角色大小和镜头距离不变，不要缩小或拉远"。

## 下载 mp4（必带 Referer 防盗链）

```bash
# curl（确定可用）：CDN 用 Tengine 反盗链，不带 Referer 必 403
curl -sSL -H "Referer: https://www.liblib.art/" -o out.mp4 "<mp4 URL>"
# 或 libtv download（参数以 libtv download --help 为准，-n 传节点 id/显示名）
```
[[reference 见 feedback_liblib_cdn_referer]]

## 落地 prompts log（强制）

每次 gen 跑完立刻 append `work/<series>/_prompts_log.md`，schema 见 [prompts-log.md](prompts-log.md)。

## 常见坑

- **fetch failed**：上传 / 生成偶发网络抖动，循环重试 1-3 次即可（见上面脚本思路）。
- **未登录 / 401**：旧 `sk-libtv-...` 新版不认；用 `libtv login` 或拷 `credentials.json`。
- **CDN 403**：下载忘带 `Referer: https://www.liblib.art/`。
- **i2v 整体缩放 / 没演动作**：用 `singleImage2video` 锁首帧，别用首尾帧；prompt 写明"全程角色大小不变、不要缩小或拉远"。

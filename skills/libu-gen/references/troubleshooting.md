# 常见坑 + 成本速查

## 常见坑

| 症状 | 原因 | 对策 |
|------|------|------|
| 抠图后白色区域消失 | chromakey 颜色取错 | 改用 Vision（bgrm.swift），不要 chromakey |
| 头发丝 / 脚底 / 轮廓带绿晕 | Vision 只改 alpha，原始绿幕色残留在半透明 RGB | 必做 despill（[pipeline-mask-despill-webp.md](pipeline-mask-despill-webp.md) 第 5 步） |
| 呆毛尖 / 炸毛 / 飞散发丝整条不见 | Vision 把细丝当噪声 drop 掉了 | 用 **阶段 B.1 的 hybrid 脚本**替换 despill，加 chroma rescue 把细丝捞回来 |
| 视频有黑边 | 选了"智能比例"，参考图不是 16:9 | 规格里手动选 3:4 或 9:16 匹配参考图比例 |
| 角色呼吸 + 已有 breathing 动画重叠抖动 | prompt 写了"呼吸感晃动" | prompt 明确"身体整体保持静止不晃动" |
| 中段镜头莫名其妙拉近成特写、画面中央出现云团/气泡框 | prompt 写了"第 X 秒"时间戳，模型把它当镜头切换点处理 | 不要写时间戳，改用"起初 / 接着 / 然后 / 最后"自然顺序词。见 [path-a-alt-text-to-video.md](path-a-alt-text-to-video.md) 铁律 1 |
| 中段角色突然变成另一个完全不同的人（发色/服装全错） | prompt 描述了角色外观，模型把"参考图脸"和"prompt 字面"插值，重绘时脱锚 | prompt 里只描述动作和气质副词，**不要描述任何外观/五官/服装**。见铁律 2 |
| 头发被拉成白色长拖影直冲天顶、甚至蜷成奇怪形状 | prompt 描述了头发/呆毛的主动运动 | 不写头发动作。只描述主体（头/手/脖子）动作，头发跟着主体被动联动就够了。见铁律 3 |
| Mac 上抽帧/抠尾帧时 `imageio_ffmpeg` 报 "could not find codec parameters" | 那个 ffmpeg 是 `--disable-everything` stripped 构建，只支持 webm/mjpeg，碰到 liblib 输出的 mp4 直接挂 | `brew install ffmpeg` 装通用版本；临时 fallback 走 chrome canvas 抠帧（见 [state-triggered.md](state-triggered.md)） |
| exit 视频和 enter 收尾位置/姿态对不上、切换瞬间闪一下 | exit 没用 enter 末帧作首帧 | 必须先从 enter mp4 抽尾帧 png，再喂给 exit 的首帧槽 |
| canvas `toDataURL` 抛 SecurityError | 跨域 mp4 让 canvas 染污 | mp4 先读 Buffer → base64 → 页内 atob → Blob → object URL，video src 同源后再画 canvas |
| 自由生成连续崩三次 prompt 救不回来 | 该动作不适合自由生成 | **回头去找/录一段动作参考，改走 [path-a-action-mimic.md](path-a-action-mimic.md)** |
| 动作模仿出来的角色脸跑偏 | 角色参考图本身不行（角度奇怪/表情极端） | 先走 [path-a-pre-image-refine.md](path-a-pre-image-refine.md) 洗一张更标准的参考图，再喂动作模仿 |
| 循环回不到原位 | 没加尾帧 | 尾帧选同一张参考图 |
| Godot console "Failed to load" | 帧编号/扩展名错 | 检查从 0000 起、.webp 扩展 |
| 图片选择器点击 / 确定按钮无效，`role="dialog"` 有多个 | antd Modal 关闭后 DOM 残留幽灵副本，JS selector 选到不可见那个 | **直接 `browser_navigate` 重新打开页面**比死磕 selector 快 10 倍；真要用 JS 就 `document.querySelectorAll('[role="dialog"]').find(d => d.offsetParent)` 只认可见副本 |
| LibTV 会员促销 modal 挡住生成器面板 | 平台 banner 弹窗 | JS 移除 `div[class*=mantine-Modal-overlay]:has(text=五一/LibTV/会员2.0)`，或点 X 关掉 |
| 历史条目的"再次生成"按钮触发重复扣费 | 不是继承配置的快捷方式，是直接重复提交 | 不要点历史条目的"再次生成"；用 `browser_navigate` 重载页面或手动重配 |
| curl 下载 liblib mp4 返回 403 Tengine | images-wm.liblib.cloud 防盗链 | `curl -sSL -H "Referer: https://www.liblib.art/" ...` 带 Referer |
| 等生成超时 / 抓到几个月前的 mp4 | history 是 oldest-at-top，`querySelectorAll('video')` 顺序也不可靠 | 用 baseline-diff（跑前 snapshot mp4 URL set，跑完取新增），见 [path-a-alt 第 8 步](path-a-alt-text-to-video.md) |
| `isInProgress` 永远 true，生成早完了还在等 | `[class*="loading"]` 选到了 captcha / 平台菜单的 loading 而非生成进度条 | 别只看 loading class，叠加 `textContent.includes("生成中")` 或 `/0\/1/` 文字判定；或干脆只信 baseline-diff，不查 in-progress |
| `尾帧` 按钮 click 命中错误目标 | `textContent.includes('帧')` 太宽，会撞到"首帧"/"上传尾帧参考"等 | 首帧用 `includes('首帧')` 没问题；**尾帧必须 `textContent.trim()==='尾帧'` 精确匹配** |
| 弹窗里点参考图 img 没反应 | click 落在 `<img>` 上不触发选中，真目标是外层卡片 | 从 `img.editor-upload_customImage__kXa_6` 向上爬 ≤4 层到 `[class*="imgWrap"]` 那张卡片再 `.click()` |
| 生成按钮文字一直变（限免/创作/生成/点数/**光秃秃的积分数字 "55"** 都见过） | 余额/活动/限免次数会换底栏文字甚至只剩纯数字 | **完全不靠文字**，按坐标+宽度过滤：`y∈[920,960] && x>1000 && width>50` —— 底栏唯一这么大的可点按钮就是生成按钮 |
| 自动填 prompt 后点生成提交了空字符串 | `textarea.value = prompt` 绕过 React 受控 input 的 setState | 用 native setter：`Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set.call(tgt, prompt)` 然后 dispatch `input` + `change` 事件 |

## 成本 & 时间

- **生成**：按所选模型 + 分辨率算（典型：Seedance 1.5 Pro 视频 ~20/次，可灵 3.0 ~30-80/次（**新账户限免 4 次**），Seedream 5.0 Lite 图 ~4/张，Seedance 2.0 Fast VIP 视频更贵，动作模仿单次按平台显示）；UI 底部那个数字为准。1-3 分钟出片。
- **抠图 + 转码**：~30 秒 / 120 帧（M1/M2）
- **压缩 (阶段 D)**：~10 秒 / 120 帧 (Pillow resize + libwebp 重新编码)
- **Godot 改动**：~10 行代码 (新动画) / ~120 行 (新 director)

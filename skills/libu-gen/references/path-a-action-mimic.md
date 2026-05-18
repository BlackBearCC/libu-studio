# 阶段 A — 动作模仿（推荐主路径）

适用：有一段任意动作 demo（自拍 / 找的视频片段 / 平台预设动作库），想让角色原样复刻。

**为什么这是主路径**：不用赌 prompt — 外观由角色图锁脸，动作由参考视频 ground truth 锁住，一次成功率远高于自由生成。三条 prompt 铁律（见 [path-a-alt-text-to-video.md](path-a-alt-text-to-video.md)）本质上就是在对抗自由生成的不稳定；动作模仿绕过这层。

1. `browser_navigate("https://www.liblib.art/ai-tool/image-generator")`
2. 底部 segmented tab 选 **「动作模仿」**
3. 左侧"**角色**"槽：上传角色绿幕参考图（阶段 A.pre 洗过的或原始绿幕图）
4. 中间"**动作**"槽：上传动作参考视频；或点 **「参考动作」** 下拉，从平台预设动作库选
5. 模式：默认 **「标准模式」**
6. **把 "参考动作 / 模式 / 积分" 三项贴给用户确认**，等"go"才点生成
7. 监控生成进度 → 完成后取视频 URL：
   ```js
   Array.from(document.querySelectorAll('video')).map(v => v.src || v.querySelector('source')?.src).filter(Boolean)
   ```
   新增的是列表末尾那条
8. 下载 mp4（必带 Referer 防盗链）：
   ```bash
   curl -sSL -H "Referer: https://www.liblib.art/" -o ~/Downloads/<slug>-<name>.mp4 "<url>"
   ```

动作模仿不需要写 prompt，跳过 [path-a-alt-text-to-video.md](path-a-alt-text-to-video.md) 的 prompt 写法节，直接进 [pipeline-mask-despill-webp.md](pipeline-mask-despill-webp.md)。

# Nana AI Video Packaging

娜乌斯嘉AI《我只骂了AI一句丑》这期视频的全部过程日志、提示词模板和包装代码。

这条视频从口播到包装、剪辑、配乐，全程由 AI（Claude Opus 5.5 指挥）完成，博主只负责定方向和吐槽。这里把过程全摊开：卡在哪、怎么解决的，都在。

## 这里有什么

| 目录 | 内容 |
| --- | --- |
| `docs/过程日志.md` | 每个案例的骂之前、原话吐槽、AI 诊断、骂之后，以及十几个真实难点和解法 |
| `skills/nana-video-packaging/` | 可以直接装进 Claude 的 skill：完整制作流程 + 品牌规范 + 说话习惯 + 提示词模板 + 踩坑清单 |
| `tools/scenes/` | 三个案例的骂之前/骂之后源码（HTML 写动画）和音效合成脚本、片尾动画 |
| `tools/pack/` | 包装合成：字幕、贴纸、印章、清单卡、小头像、吉祥物、全屏看片、拼接、配乐 |
| `tools/asr.py` | 离线中文语音识别（Paraformer ONNX），带句子时间轴，用来回听校对口播 |
| `assets/` | 片尾“娜乌斯嘉 · 恭喜发现宝藏”透明素材 |

> 不包含任何人脸视频。口播片段请用你自己的素材，放在 `clips/`。

## 原理
网页代码画动画 → 无头浏览器逐帧截图 → 代码合成音乐音效 → ffmpeg 合成视频。

## 运行
需要 Python 3.10+、ffmpeg、Playwright（Chromium）。

```bash
pip install numpy scipy onnxruntime playwright
playwright install chromium

# 语音识别模型（约 1GB，来自 sherpa-onnx 开源发布页）
curl -L -o pz.tar.bz2 https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-paraformer-zh-2024-03-09.tar.bz2
tar xjf pz.tar.bz2 && mv sherpa-onnx-paraformer-zh-2024-03-09 asr_model

# 单独渲染一个动画
python3 tools/render.py tools/scenes/案例二_原理图_骂之后.html out.mp4

# 整期包装：先改 tools/pack/segments.py 里的分段配置，再
cd tools/pack && python3 build.py && python3 assemble.py 成片.mp4
```

## 许可
混合许可，详见 [LICENSE](LICENSE)：
- **代码**（脚本、动画源码、流程 skill、提示词模板、踩坑清单、过程日志）：MIT，随便用、随便改、可商用，保留署名即可。
- **品牌素材**（片尾“娜乌斯嘉 · 恭喜发现宝藏”成品、品牌规范、说话习惯、名称与形象）：仅供学习参考，请勿直接用于你的内容或冒充娜乌斯嘉AI。想要同款片尾，用代码换成你自己的名字和配色就好。

## 三条方法
1. 别接受第一版。
2. 告诉 AI 你是谁。
3. 做对一次，就让它记下来。

关注小红书 **娜乌斯嘉AI**，恭喜发现宝藏。

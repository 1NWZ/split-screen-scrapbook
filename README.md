# 上下屏复古手账拼贴 Skill

中文编写的 AI 图像制作 Skill：用户照片的一屏人像＋一屏纯色肌理与英文材质字。四个参考分支、身份保留、受控变化、AI资产与代码合成。

## 使用

把整个 `split-screen-scrapbook` 文件夹放进支持本地 Skill 的宿主技能目录。Codex 的用户技能目录可使用 `~/.codex/skills/`；也可把 `SKILL.md` 和相关文件加载到支持文件型指令的其他代理中，实际自动发现方式以宿主为准。

上传一张自己的照片，然后输入：

> 使用 $split-screen-scrapbook，把这张照片做成上下屏复古手账拼贴。尽量保留我的五官，由照片决定配色，标题用 Blue Hour。

> 沿用刚才的人像，换成图4的洋红蕾丝风格。保持身份，改变排版和点缀。

照片是必需输入。其余可选：英文标题、参考分支、上下位置、色彩、随机种子。照片分析和语义选择由执行 Skill 的代理完成，Python脚本不自动猜测照片含义，也不内置图像模型。

## 仓库内容与安装

本仓库包含中文指令、风格图谱、可运行脚本、示例配方、两张无人像AI材质底板，以及十张可随 Skill 分发的原创素材母版。公开素材位于 `assets/library/`：一张装订分界、一张宝石星贴、五张独立材质字、三张独立蕾丝。原始15张参考图片未提供公开再分发许可，因此不包含在公开仓库；它们只保留清单与文字分析。个人照片与私人测试成片不上传。

```bash
git clone https://github.com/1NWZ/split-screen-scrapbook.git
```

将下载的整个文件夹放到宿主的技能目录中，保持脚本与引用文件的相对路径。若使用Codex个人技能目录，可以把它放到 `~/.codex/skills/split-screen-scrapbook/`。上传照片后调用 `$split-screen-scrapbook`。

只有代码环境时可以制作基础合成；参考级蕾丝、材质字、实体装订由可用图像模型与代码共同完成。两张测试底板仅用于演示，实际生成应响应照片变化。

## 本地合成

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/import_references.py --source /path/to/my/reference-folder
python scripts/compose.py --photo /path/to/photo.jpg --recipe recipe.example.json --out rendered/result.png
```

**先修改示例配方中的 `faces` 与 `crop`，示例脸框不适用于你的照片。** 脸框坐标相对EXIF方向纠正后的整张照片；框住额头至下巴、左右脸轮廓。群像列出所有脸。程序检查二次裁切和装饰相交，不能验证你是否漏标了一张脸。

`style` 可为 `pink-blue-binder`、`hot-pink-wave`、`ice-blue-binder`、`magenta-lace`。默认3:4；`photo_fraction`是照片占整张高度的比例。`photo_position`控制上下。

`font` 可填写配方目录下的自备字体路径。不提供时使用默认字，仅用于底稿。复杂标题先用AI制作核验过的透明PNG，加入配方：

```json
{"layers":[
  {"path":"assets/my-lace.png","role":"decoration","box":[0.05,0.75,0.27,0.95]},
  {"path":"assets/my-title.png","role":"title","box":[0.10,0.64,0.90,0.85]}
]}
```

上面的蕾丝坐标仅为左侧位置示例；实际先选下屏版式，再在有效留白区选择位置，不固定任何角落。图4跨界大花体、错行标题、斜向与左右锚点等结构见 `references/eccentric-collage.md`。

`box`为最终画布上的[x0,y0,x1,y1]，0–1归一化；素材等比放入框内。所有素材路径相对配方所在目录。`role: title`会替代默认文字标题。图层按数组顺序从下往上绘制。不要放入带伪透明棋盘背景的图片。

输出为图片与同名 `.recipe.json`，记录种子、源图与素材校验和。精确重现还需要相同资产与依赖环境，建议保存环境版本。种子不控制外部AI生成模型。

## 验证

```bash
python scripts/test_compose.py
```

这组工程测试覆盖四种分支、相同种子复现、不同种子变化、遮脸拒绝、裁脸拒绝、EXIF、透明图层和长标题。只验证合成行为；真实人像与风格效果须按照 `references/quality.md` 看图验收。

## 内容位置

- `SKILL.md`：代理入口与工作流。
- `references/style-atlas.md`：15张参考图的版式、色彩、材料与变体规则。
- `references/production.md`：AI素材提示词和分层制作。
- `references/quality.md`：身份、排版、材质与英文的验收。
- `scripts/compose.py`：可复现基础合成器。
- `references/eccentric-collage.md`：实体装订、位置可变的单个干净蕾丝与古怪小众下屏的具体构成。
- `scripts/merge_edit.py`：局部AI编辑后恢复已认可的上屏原像素。
- `assets/references/manifest.json`：原图编号、名称、哈希及用途。
- `assets/library/`：公开版实际读取的原创素材效果库。
- `references/open-source-assets.md`：原创素材的选择、裁切和使用规则。

代码与本项目编写的文字按 MIT 开源；原始参考图片及外部字体/资产按其各自许可处理，见 `THIRD_PARTY_ASSETS.md`。

默认照片效果已固定为适中的淡粉高光、冷青蓝暗部和非均匀局部闪光过曝，换版式也保留；用户指定自然或弱化时才调整。新版已加入实作修正：荧光标签、局部过曝、下屏内受控随机放置一个蕾丝贴片（三种形态择一），无毛边、毛须和散线、珠链串联与不对称复印拼贴。用户的私人照片与成片不包含在开源包内。`assets/generated/`中的两张无人像AI底板可用于测试素材流程，实际输出应按照片改文字、布局和元素，不能所有用户都套同一张底板。


最新强度：偏色保留强粉紫/青蓝版本约40%的视觉强度，肤色自然、暗部适度偏冷；局部闪光过曝和奶白光晕独立保留。详见 references/production.md 的偏色强度校准。

照片效果交付前逐项核验：适中偏色、局部过曝、亮点柔光与中性肤色；缺项局部修正。Skill约束制作与验收流程，不保证图像模型每次首轮成功；基础脚本也不内置局部过曝或光晕。

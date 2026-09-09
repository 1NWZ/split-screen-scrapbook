#!/usr/bin/env python3
"""中文上下屏 Skill 基础合成器：原像素人像、确定性纹理、PNG资产图层。"""
import argparse
import hashlib
import json
import math
import os
import secrets
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

STYLES = {
    "pink-blue-binder": ("#F3C8DB", "top", .52, "binder"),
    "hot-pink-wave": ("#F242A7", "bottom", .49, "wave"),
    "ice-blue-binder": ("#56AFE0", "top", .55, "binder"),
    "magenta-lace": ("#F337B4", "top", .57, "plain"),
}


def boxcheck(box):
    if len(box) != 4 or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in box):
        raise ValueError("box必须为四个有限数值")
    x0, y0, x1, y1 = box
    if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
        raise ValueError(f"box必须位于0–1且有正面积：{box}")
    return box


def hit(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rgb(color):
    from PIL import ImageColor
    return ImageColor.getrgb(color)


def texture(size, color, rng, amplitude=2.6):
    w, h = size
    coarse = Image.fromarray(rng.integers(110, 146, (max(2, h // 60), max(2, w // 60)), dtype=np.uint8))
    coarse = np.asarray(coarse.resize(size, Image.Resampling.BICUBIC), dtype=float) - 128
    noise = rng.normal(0, amplitude, (h, w)) + coarse * .23
    noise += np.sin(np.arange(h)[:, None] * 2.2) * .55
    arr = np.array(rgb(color), dtype=float)[None, None, :] + noise[:, :, None]
    return Image.fromarray(np.uint8(np.clip(arr, 0, 255))).convert("RGBA")


def photo_crop(source, crop, faces, target):
    sw, sh = source.size
    x0, y0, x1, y1 = boxcheck(crop)
    raw = (round(x0 * sw), round(y0 * sh), round(x1 * sw), round(y1 * sh))
    cw, ch = raw[2] - raw[0], raw[3] - raw[1]
    tw, th = target
    if cw < 2 or ch < 2:
        raise ValueError("裁切区域太小")
    scale = max(tw / cw, th / ch)
    visible_w, visible_h = tw / scale, th / scale
    left = raw[0] + (cw - visible_w) / 2
    top = raw[1] + (ch - visible_h) / 2
    right, bottom = left + visible_w, top + visible_h
    mapped = []
    for f in faces:
        a, b, c, d = boxcheck(f)
        a, b, c, d = a * sw, b * sh, c * sw, d * sh
        if a < left or b < top or c > right or d > bottom:
            raise ValueError("当前比例/cover裁切会裁掉脸，请调整crop或photo_fraction")
        mapped.append(((a-left)*scale, (b-top)*scale, (c-left)*scale, (d-top)*scale))
    # 浮点采样框避免EXIF/cover多次舍入偏移。
    out = source.resize(target, Image.Resampling.LANCZOS, box=(left, top, right, bottom))
    return out, mapped


def grade(im, rng, strength):
    if not 0 <= strength <= 1:
        raise ValueError("filter_strength范围0–1")
    arr = np.asarray(im.convert("RGB"), dtype=float)
    blur = np.asarray(im.filter(ImageFilter.GaussianBlur(.65 * im.width / 1536)).convert("RGB"), dtype=float)
    arr = arr * (1 - .38 * strength) + blur * .38 * strength
    arr = arr * (1 - .06 * strength) + np.array([8, 5, 10]) * strength
    arr += rng.normal(0, 1.8 * strength, arr.shape[:2])[:, :, None]
    return Image.fromarray(np.uint8(np.clip(arr, 0, 255))).convert("RGBA")


def safe(box, protected):
    return not any(hit(box, f) for f in protected)


def fit_font(text, path, width, height):
    if not text or not text.isascii():
        raise ValueError("画面文字请使用非空英文/ASCII文本")
    for size in range(max(8, int(height)), 7, -1):
        font = ImageFont.truetype(str(path), size) if path else ImageFont.load_default(size=size)
        b = font.getbbox(text)
        if b[2] - b[0] <= width and b[3] - b[1] <= height:
            return font, b
    raise ValueError("文字过长，请缩短或扩大标题框")


def text_layer(canvas, text, box, font_path, protected, label=False):
    if not safe(box, protected):
        raise ValueError("文字区域与脸部保护区相交")
    x0, y0, x1, y1 = box
    font, b = fit_font(text, font_path, x1-x0-12, y1-y0-8)
    draw = ImageDraw.Draw(canvas)
    if label:
        draw.rectangle(box, fill=(249, 245, 237, 255))
    x = (x0+x1-(b[2]-b[0]))/2-b[0]
    y = (y0+y1-(b[3]-b[1]))/2-b[1]
    if not label:
        draw.text((x+1, y+2), text, font=font, fill=(55, 40, 55, 150))
    draw.text((x, y), text, font=font, fill=(32, 29, 36, 255) if label else (248, 237, 244, 255))


def gem(canvas, x, y, r, mode):
    draw = ImageDraw.Draw(canvas)
    if mode == "star":
        pts = [(x+math.cos(-math.pi/2+i*math.pi/5)*r*(1 if i%2==0 else .43),
                y+math.sin(-math.pi/2+i*math.pi/5)*r*(1 if i%2==0 else .43)) for i in range(10)]
    else:
        pts = [(x+math.cos(i*math.pi/4)*r, y+math.sin(i*math.pi/4)*r) for i in range(8)]
    draw.polygon([(a+2, b+3) for a,b in pts], fill=(72, 62, 80, 120))
    draw.polygon(pts, fill=(204, 207, 219), outline=(85, 85, 103))
    for i in range(len(pts)):
        draw.polygon([pts[i], pts[(i+1)%len(pts)], (x-r*.12,y-r*.15)],
                     fill=[(238,238,245),(150,168,183),(215,195,221),(178,190,202)][i%4])
    draw.line((x-r*.4, y-r*.3, x+r*.13, y-r*.3), fill="white", width=max(1,int(r*.09)))


def separator(canvas, y, kind, protected):
    w, h = canvas.size
    s = w / 1536
    d = ImageDraw.Draw(canvas)
    region = (0, y-45*s, w, y+45*s)
    if kind == "plain":
        return
    if not safe(region, protected):
        raise ValueError("分界装饰与脸部保护区相交，请调整构图")
    if kind == "binder":
        for dy in range(-13, 14):
            value = int(65 + 155 * math.exp(-((dy+4)/7)**2))
            d.line((0,y+dy*s,w,y+dy*s), fill=(value, value, max(0,value-8)), width=max(1,round(s)))
        for x in np.linspace(.065*w,.935*w,7):
            d.ellipse((x-13*s,y-42*s,x+13*s,y-18*s), fill=(34,30,34))
            d.ellipse((x-13*s,y+18*s,x+13*s,y+42*s), fill=(34,30,34))
            for width, color in [(12,(47,43,45)),(8,(174,174,166)),(3,(241,237,223))]:
                d.arc((x-11*s,y-37*s,x+11*s,y+37*s), 65, 295, fill=color, width=max(1,round(width*s)))
    elif kind == "wave":
        pts = [(x,y+math.sin(x/w*math.pi*20)*8*s) for x in range(w)]
        d.line(pts, fill=(255,246,238), width=max(2,round(4*s)))
        for x in range(0,w,max(1,round(18*s))):
            yy = y+math.sin(x/w*math.pi*20)*8*s
            d.ellipse((x-2*s,yy-2*s,x+2*s,yy+2*s),fill="white")
    else:
        raise ValueError("separator仅支持plain/binder/wave；真实蕾丝请用PNG图层")


def render(photo_path, recipe, out, base=Path(".")):
    cfg = dict(recipe)
    style = cfg.get("style", "ice-blue-binder")
    color, position, fraction, sep = STYLES[style]
    w, h = cfg.get("size", [1536,2048])
    if not (isinstance(w,int) and isinstance(h,int) and 256 <= w <= 4096 and w < h <= 6144):
        raise ValueError("尺寸必须为竖幅，宽256–4096，高不超过6144")
    position = cfg.get("photo_position", position)
    fraction = cfg.get("photo_fraction", fraction)
    if position not in ("top","bottom") or not .46 <= fraction <= .59:
        raise ValueError("photo_position应为top/bottom，photo_fraction范围.46–.59")
    seed = cfg.get("seed", secrets.randbits(32))
    rng = np.random.default_rng(seed)
    ph = round(h*fraction)
    py = 0 if position == "top" else h-ph
    split = ph if position == "top" else py
    bg_y0, bg_y1 = (ph,h) if position == "top" else (0,py)
    faces = cfg.get("faces", [])
    if not faces:
        raise ValueError("请填写faces中所有人脸的归一化边界框；此工具不自动检测人脸")
    with Image.open(photo_path) as opened:
        source = ImageOps.exif_transpose(opened).convert("RGB")
    photo, mapped = photo_crop(source, cfg.get("crop",[0,0,1,1]), faces, (w,ph))
    margin = w*.02
    protected = [(a-margin,b+py-margin,c+margin,d+py+margin) for a,b,c,d in mapped]
    canvas = texture((w,h), cfg.get("color",color), rng)
    canvas.alpha_composite(grade(photo,rng,cfg.get("filter_strength",.65)),(0,py))
    panel_path = (base/cfg["paper_panel"]).resolve() if cfg.get("paper_panel") else None
    if panel_path:
        with Image.open(panel_path) as opened:
            panel = opened.convert("RGBA")
        # 等比contain保留字形和蕾丝边；空余处沿面板边缘颜色延展，避免裁字。
        panel = ImageOps.contain(panel,(w,bg_y1-bg_y0),Image.Resampling.LANCZOS)
        px, pyy = (w-panel.width)//2, bg_y0+(bg_y1-bg_y0-panel.height)//2
        pads = ((pyy-bg_y0,bg_y1-pyy-panel.height),(px,w-px-panel.width),(0,0))
        backing = Image.fromarray(np.pad(np.asarray(panel),pads,mode="edge"))
        canvas.alpha_composite(backing,(0,bg_y0))
        canvas.alpha_composite(panel,(px,pyy))
    font_path = (base / cfg["font"]).resolve() if cfg.get("font") else None
    layers = cfg.get("layers",[])
    title_box = cfg.get("title_box",[.10,(bg_y0+(bg_y1-bg_y0)*.24)/h,.90,(bg_y0+(bg_y1-bg_y0)*.63)/h])
    def pixels(b):
        a,c,e,f = boxcheck(b)
        return (round(a*w),round(c*h),round(e*w),round(f*h))
    # 先给主标题与用户资产预留空间，基础装饰不可抢占。
    reserved = [pixels(title_box)] + [pixels(item["box"]) for item in layers]
    if panel_path:
        reserved.append((0,bg_y0,w,bg_y1))
    labels = cfg.get("labels", [])
    reserved += [pixels(item["box"]) for item in labels]
    count = cfg.get("ornament_count",8)
    if not isinstance(count,int) or not 0 <= count <= 15:
        raise ValueError("ornament_count范围0–15")
    placed = 0
    for _ in range(250):
        if placed >= count:
            break
        r = rng.uniform(.012,.026)*w
        x,y = rng.uniform(.04,.96)*w,rng.uniform(.035,.965)*h
        bb = (x-r-4,y-r-4,x+r+4,y+r+4)
        if abs(y-split) < 55*w/1536 or not safe(bb,protected+reserved):
            continue
        gem(canvas,x,y,r,"star" if "binder" in style else "diamond")
        reserved.append(bb)
        placed += 1
    separator(canvas,split,cfg.get("separator",sep),protected)
    if not cfg.get("panel_has_title",False) and not any(item.get("role") == "title" for item in layers):
        text_layer(canvas,cfg.get("title","Daydream"),pixels(title_box),font_path,protected)
    asset_hashes = {}
    for item in layers:
        path = (base/item["path"]).resolve()
        with Image.open(path) as opened:
            layer = opened.copy()
        if "A" not in layer.getbands():
            raise ValueError(f"图层需要真实透明通道：{path.name}")
        bounds = pixels(item["box"])
        if not safe(bounds,protected):
            raise ValueError(f"图层覆盖脸部保护区：{path.name}")
        a,b,c,d = bounds
        layer = ImageOps.contain(layer.convert("RGBA"),(c-a,d-b),Image.Resampling.LANCZOS)
        opacity = item.get("opacity",1)
        if not 0 <= opacity <= 1:
            raise ValueError("opacity范围0–1")
        layer.putalpha(layer.getchannel("A").point(lambda n: round(n*opacity)))
        canvas.alpha_composite(layer,(a+(c-a-layer.width)//2,b+(d-b-layer.height)//2))
        asset_hashes[item["path"]] = sha(path)
    for item in labels:
        text_layer(canvas,item["text"],pixels(item["box"]),font_path,protected,True)
    # 统一弱扫描纹理，不改几何；不保留输入元数据。
    arr = np.asarray(canvas.convert("RGB"),dtype=float)
    arr += rng.normal(0,.55,(h,w))[:,:,None]
    result = Image.fromarray(np.uint8(np.clip(arr,0,255)))
    out = Path(out)
    out.parent.mkdir(parents=True,exist_ok=True)
    result.save(out)
    # 配方移到输出目录后，重定位资产路径，保证保存的配方仍能重新运行。
    cfg["layers"] = [dict(item, path=os.path.relpath((base/item["path"]).resolve(),out.resolve().parent))
                     for item in layers]
    if font_path:
        cfg["font"] = os.path.relpath(font_path,out.resolve().parent)
    if panel_path:
        cfg["paper_panel"] = os.path.relpath(panel_path,out.resolve().parent)
        cfg["paper_panel_sha256"] = sha(panel_path)
    cfg.update(seed=seed,style=style,size=[w,h],photo_position=position,photo_fraction=fraction,
               color=cfg.get("color",color),separator=cfg.get("separator",sep),
               title_box=title_box,source_sha256=sha(photo_path),asset_sha256=asset_hashes,
               placed_ornaments=placed,quality_stage="基础合成，须人工视觉验收")
    out.with_suffix(".recipe.json").write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding="utf-8")
    return cfg


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--photo",type=Path,required=True)
    p.add_argument("--recipe",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args = p.parse_args()
    cfg = json.loads(args.recipe.read_text(encoding="utf-8"))
    render(args.photo,cfg,args.out,args.recipe.resolve().parent)
    print(str(args.out.resolve()))


if __name__ == "__main__":
    main()

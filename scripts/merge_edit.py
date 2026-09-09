#!/usr/bin/env python3
"""合并上下屏局部编辑：顶部像素锁定，渐变仅发生在其下方非人脸区域。"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps


def merge(original, edited, output, lock_top=.49, blend=.02):
    if not (0 < lock_top < 1 and 0 <= blend and lock_top+blend < 1):
        raise ValueError("lock_top与blend必须为合法的归一化高度")
    if Path(output).resolve() in (Path(original).resolve(),Path(edited).resolve()):
        raise ValueError("请使用新输出路径，保留修改前的图片")
    with Image.open(original) as im:
        source=ImageOps.exif_transpose(im).convert("RGB")
    with Image.open(edited) as im:
        generated=ImageOps.exif_transpose(im).convert("RGB")
    w,h=source.size
    if abs((generated.width/generated.height)/(w/h)-1) > .02:
        raise ValueError("新旧图比例差异超过2%，先重新对齐版式")
    generated=ImageOps.fit(generated,source.size,Image.Resampling.LANCZOS)
    keep=round(h*lock_top)
    end=round(h*(lock_top+blend))
    a=np.asarray(source,dtype=float)
    b=np.asarray(generated,dtype=float)
    weight=np.ones((h,1,1))
    weight[:keep]=0
    if end>keep:
        weight[keep:end,0,0]=np.linspace(0,1,end-keep)
    result=np.uint8(np.clip(np.round(a*(1-weight)+b*weight),0,255))
    assert np.array_equal(result[:keep],np.asarray(source)[:keep])
    output=Path(output)
    output.parent.mkdir(parents=True,exist_ok=True)
    Image.fromarray(result).save(output)
    report={"locked_top_rows":keep,"blend_end_row":end,"top_pixels_exact":True,
            "original_sha256":hashlib.sha256(Path(original).read_bytes()).hexdigest(),
            "edited_sha256":hashlib.sha256(Path(edited).read_bytes()).hexdigest(),
            "output_size":[w,h],"note":"需人工确认混合带不经过人脸且与装订位置吻合"}
    output.with_suffix(".merge.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    return report


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original",type=Path,required=True)
    p.add_argument("--edited",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--lock-top",type=float,default=.49)
    p.add_argument("--blend",type=float,default=.02)
    args=p.parse_args()
    print(json.dumps(merge(args.original,args.edited,args.out,args.lock_top,args.blend),ensure_ascii=False))

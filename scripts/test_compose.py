"""使用合成几何图验证工程行为，不冒充真人效果评估。"""
import tempfile
import json
import unittest
from pathlib import Path
from PIL import Image, ImageDraw
from compose import render, STYLES


class ComposeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.photo = self.root / "source.png"
        im = Image.new("RGB",(600,450),(80,105,120))
        d = ImageDraw.Draw(im)
        d.ellipse((240,100,340,220),fill=(205,155,138))
        im.save(self.photo)
        self.cfg = dict(size=[384,512],seed=5,faces=[[.4,.23,.56,.48]],title="Blue Hour")

    def run_image(self,cfg,name="out.png"):
        out = self.root/name
        render(self.photo,cfg,out,self.root)
        return out

    def test_four_styles(self):
        for style in STYLES:
            cfg = dict(self.cfg,style=style)
            out = self.run_image(cfg,style+".png")
            with Image.open(out) as im:
                self.assertEqual(im.size,(384,512))
            self.assertTrue(out.with_suffix(".recipe.json").exists())

    def test_seed(self):
        a = self.run_image(self.cfg,"a.png").read_bytes()
        b = self.run_image(self.cfg,"b.png").read_bytes()
        c = self.run_image(dict(self.cfg,seed=12),"c.png").read_bytes()
        self.assertEqual(a,b)
        self.assertNotEqual(a,c)

    def test_crop_rejects_clipped_face(self):
        with self.assertRaisesRegex(ValueError,"裁掉脸"):
            self.run_image(dict(self.cfg,crop=[.6,0,1,1]))

    def test_cover_rejects_edge_face(self):
        with self.assertRaisesRegex(ValueError,"裁掉脸"):
            self.run_image(dict(self.cfg,faces=[[0,0,.3,.15]],photo_fraction=.46))

    def test_missing_faces(self):
        with self.assertRaisesRegex(ValueError,"faces"):
            self.run_image(dict(self.cfg,faces=[]))

    def test_multiple_faces(self):
        self.run_image(dict(self.cfg,faces=[[.2,.23,.35,.48],[.6,.23,.75,.48]]))

    def test_label_collision(self):
        with self.assertRaisesRegex(ValueError,"文字区域"):
            self.run_image(dict(self.cfg,labels=[dict(text="oops",box=[.3,.05,.7,.3])]))

    def test_asset_collision(self):
        Image.new("RGBA",(30,30),(255,0,0,160)).save(self.root/"asset.png")
        with self.assertRaisesRegex(ValueError,"图层覆盖"):
            self.run_image(dict(self.cfg,layers=[dict(path="asset.png",box=[.3,.05,.7,.3])]))

    def test_transparent_title(self):
        Image.new("RGBA",(120,30),(220,40,180,160)).save(self.root/"asset.png")
        self.run_image(dict(self.cfg,layers=[dict(path="asset.png",role="title",box=[.1,.7,.9,.8])]))

    def test_saved_recipe_asset_paths(self):
        Image.new("RGBA",(120,30),(220,40,180,160)).save(self.root/"asset.png")
        cfg = dict(self.cfg,layers=[dict(path="asset.png",role="title",box=[.1,.7,.9,.8])])
        out = self.run_image(cfg,"nested/a.png")
        saved = json.loads(out.with_suffix(".recipe.json").read_text())
        render(self.photo,saved,out.parent/"b.png",out.parent)
        self.assertEqual(out.read_bytes(),(out.parent/"b.png").read_bytes())

    def test_long_text(self):
        with self.assertRaisesRegex(ValueError,"文字过长"):
            self.run_image(dict(self.cfg,title="word "*1000))

    def test_exif(self):
        im = Image.new("RGB",(450,600),(80,100,120))
        exif = Image.Exif()
        exif[274] = 6
        self.photo = self.root/"rotate.jpg"
        im.save(self.photo,exif=exif)
        self.run_image(self.cfg)


if __name__ == "__main__":
    unittest.main()

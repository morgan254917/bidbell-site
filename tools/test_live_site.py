import importlib.util,io,unittest
from pathlib import Path
try:
 from PIL import Image
except ImportError:
 Image=None
path=Path(__file__).resolve().parent/'check_live_site.py'
spec=importlib.util.spec_from_file_location('live_check',path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def png(image,level):
 stream=io.BytesIO();image.save(stream,format='PNG',compress_level=level);return stream.getvalue()

@unittest.skipIf(Image is None,'Optional operator CDN verification requires Pillow.')
class ReleaseImageChecks(unittest.TestCase):
 def test_lossless_recompression_matches_the_same_logo(self):
  self.assertTrue(callable(getattr(module,'asset_matches',None)),'Release checker must verify transformed image pixels.')
  image=Image.new('RGBA',(4,4),(24,24,44,255));original=png(image,0);optimized=png(image,9)
  self.assertNotEqual(original,optimized)
  self.assertTrue(module.asset_matches(optimized,original,'brand-icon.png'))
 def test_changed_pixels_cannot_pass_as_a_logo_optimization(self):
  self.assertTrue(callable(getattr(module,'asset_matches',None)))
  original=Image.new('RGBA',(4,4),(24,24,44,255));changed=original.copy();changed.putpixel((0,0),(240,10,10,255))
  self.assertFalse(module.asset_matches(png(changed,9),png(original,0),'brand-icon.png'))
 def test_changed_html_requires_exact_bytes(self):
  self.assertTrue(callable(getattr(module,'asset_matches',None)))
  self.assertFalse(module.asset_matches(b'<p>wrong</p>',b'<p>right</p>','index.html'))
 def test_jpeg_recompression_does_not_allow_a_different_image(self):
  def jpeg(color,quality):
   stream=io.BytesIO();Image.new('RGB',(32,32),color).save(stream,format='JPEG',quality=quality);return stream.getvalue()
  original=jpeg((24,24,44),95)
  self.assertTrue(module.asset_matches(jpeg((24,24,44),85),original,'brand.jpg'))
  self.assertFalse(module.asset_matches(jpeg((240,40,10),85),original,'brand.jpg'))

if __name__=='__main__':unittest.main()

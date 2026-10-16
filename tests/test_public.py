import unittest,tempfile,sys
from pathlib import Path
from unittest.mock import patch
import numpy as np,pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from grid_data import coordinates,save_grid,read_grid,get_grid,region_values
from raster_map import raster_rgba,make_map,SETTINGS,bounds_for
from air_data import VARIABLES
class PublicTests(unittest.TestCase):
 def fixture(self):
  from datetime import datetime,timezone
  return {'times':np.array(['2026-10-16T00:00','2026-10-16T01:00']),
   'lats':np.array([-1.,1.]),'lons':np.array([100.,102.]),'grid_lats':np.array([0]),'grid_lons':np.array([0]),
   'meta':{'fetched_at':datetime.now(timezone.utc).isoformat(),'sampling_step':2.,'schema_version':1},
   **{v:np.array([[[0,5],[10,15]],[[1,6],[11,16]]],dtype='float32') for v in VARIABLES}}
 def test_actual_grid(self):
  y,x=coordinates();self.assertEqual(len(y)*len(x),656)
  np.testing.assert_allclose(np.diff(y),1.2)
 def test_rgba_missing(self):
  a=raster_rgba(np.array([[0,150],[np.nan,75]]),0,150,['#ffffff','#000000'],scale=8)
  self.assertEqual(a.shape,(16,16,4));self.assertEqual(a[0,0,0],255)
  self.assertEqual(a[-1,0,3],0);self.assertEqual(a[0,-1,0],0)
 def test_atomic_cache(self):
  with tempfile.TemporaryDirectory() as td:
   path=Path(td)/'data.npz';b=self.fixture();save_grid(b,path)
   r=read_grid(path);np.testing.assert_array_equal(r['pm2_5'],b['pm2_5'])
   with patch('grid_data.fetch_grid',side_effect=AssertionError('fresh cache must not request API')):
    data,warn=get_grid(path);self.assertIsNone(warn)
 def test_stale_fallback(self):
  with tempfile.TemporaryDirectory() as td:
   from air_data import DataError
   path=Path(td)/'data.npz';b=self.fixture();b['meta']['fetched_at']='2020-01-01T00:00:00+00:00';save_grid(b,path)
   with patch('grid_data.fetch_grid',side_effect=DataError('offline')):
    data,warn=get_grid(path);self.assertIsNotNone(warn);self.assertEqual(data['meta']['fetched_at'],b['meta']['fetched_at'])
 def test_regional_values(self):
  r=pd.DataFrame([{'wilayah':'A','lokasi':'A','pulau':'A','latitude':.9,'longitude':101.9}])
  d=region_values(self.fixture(),r);self.assertEqual(d.pm2_5.tolist(),[15.,16.])
 def test_map_layer(self):
  b=self.fixture();text=make_map(b,0);self.assertIn('data:image/png;base64,',text)
  self.assertIn('imageOverlay',text)
  self.assertIn('https://tile.openstreetmap.org/{z}/{x}/{y}.png',text)
  self.assertNotIn('basemaps.cartocdn.com',text)
  self.assertIn('grid sampel terdekat',text)
  import re
  script=re.findall(r'<script[^>]*>(.*?)</script>',text,re.S)[-1]
  self.assertNotIn('L.circleMarker(',script)
  self.assertLess(script.index('L.map('),script.index(".on('click'"))
  self.assertNotRegex(text,r'<script[^>]+src=')
 def test_no_public_setup(self):
  app=(Path(__file__).parents[1]/'app.py').read_text()
  self.assertNotIn('st.text_input',app);self.assertNotIn('st.file_uploader',app)
  self.assertNotIn('API key OpenAQ',app);self.assertIn('made by ali',app)
if __name__=='__main__':unittest.main()

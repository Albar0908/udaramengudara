"""Regression: the public map must not print a DeltaGenerator help panel."""
import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from streamlit.testing.v1 import AppTest
from grid_data import read_grid
class PublicRenderTests(unittest.TestCase):
 def test_map_has_no_internal_documentation(self):
  bundle=read_grid()
  with patch('grid_data.get_grid',return_value=(bundle,None)):
   app=AppTest.from_file(str(Path(__file__).parents[1]/'app.py'),default_timeout=30).run()
  self.assertFalse(app.exception)
  self.assertFalse(app.get('doc_string'))
  self.assertFalse(app.code)
  self.assertTrue(app.get('iframe') or app.get('component_instance'))
if __name__=='__main__':unittest.main()

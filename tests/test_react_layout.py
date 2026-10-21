"""Static contract checks for React-rendered sections."""
import json
import unittest
from pathlib import Path

SCHEMA = Path(__file__).resolve().parent.parent/'frontend/src/view-schema.json'

class ReactLayoutTest(unittest.TestCase):
    def test_sections_and_protected_session(self):
        doc = json.loads(SCHEMA.read_text(encoding='utf-8'))
        self.assertEqual({k for k in doc if k.startswith('Panel')},
            {'PanelCalc','PanelDiscounts','PanelRegion','PanelMethod','PanelHelp'})
        names = set()
        def collect(node):
            if isinstance(node, str): return
            tag, props, children = node
            if 'id' in props:
                self.assertNotIn(props['id'],names)
                names.add(props['id'])
            for child in children: collect(child)
        for v in doc.values(): collect(v)
        for marker in ('discountInputs','cards','editorTable','modeSelector','helpSearch','printHead','react-session-control'):
            self.assertIn(marker,names)
    def test_no_obsolete_banners(self):
        doc = SCHEMA.read_text(encoding='utf-8')
        self.assertNotIn('Descuentos del cuadro del 15 de octubre',doc)
        self.assertNotIn('Valores base del cuadro',doc)

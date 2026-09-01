import sys
import os
sys.stderr = os.fdopen(2, 'w')  # redirect stderr

def test_dynamic_renderer_loads():
    from config import Config
    c = Config()
    assert c.get("character_mode") == "dynamic_pack"
    assert c.get("selected_character_id") == "default_dynamic_ghost"

def test_dynamic_renderer_real(qapp):
    from character_v4.renderer import DynamicPackRenderer
    from pathlib import Path
    r = DynamicPackRenderer(Path("D:/pet-desktop/assets/default_dynamic_ghost"))
    assert r.load()
    assert r.is_loaded
    assert r.size() == (576, 624)  # 192*3, 208*3 at default scale

def test_pet_window_init():
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    from config import Config
    c = Config()
    from pet_window import PetWindow
    w = PetWindow(c)
    assert w.dynamic_renderer is not None
    assert w.dynamic_renderer.is_loaded
    print(f"Dynamic renderer loaded: {w.dynamic_renderer.display_name}")
    print(f"Window size: {w._pet_w}x{w._pet_h}")
    print(f"Dynamic size: {w.dynamic_renderer.size()}")
    w.close()

import sys
sys.stderr = sys.stdout
try:
    from config import Config
    c = Config()
    print("Config OK, mode:", c.get("character_mode"), "id:", c.get("selected_character_id"))
    
    from character_v4.renderer import DynamicPackRenderer
    from pathlib import Path
    r = DynamicPackRenderer(Path("D:/pet-desktop/assets/default_dynamic_ghost"))
    print("load:", r.load())
    print("is_loaded:", r.is_loaded)
    if r.is_loaded:
        print("size:", r.size())
except Exception as e:
    import traceback
    traceback.print_exc()

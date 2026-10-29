import json
from pathlib import Path

import pygame
import pytest

from ai_gym_td.ui_assets import AssetBank, ASSET_ROOT
from ai_gym_td.ui_layout import GameLayout


@pytest.fixture
def display():
    pygame.init();pygame.display.set_mode((1280,720))
    yield
    pygame.quit()


@pytest.mark.parametrize("size",[(1280,720),(1024,576),(1100,800)])
def test_grid_pointer_roundtrip_and_excluded_panels(size):
    layout=GameLayout()
    view=layout.viewport(size)
    for cell in [(0,0),(19,0),(0,11),(19,11),(7,5)]:
        x,y=layout.center(*cell)
        screen=(view.x+x*view.width/1280,view.y+y*view.height/720)
        assert layout.grid_at(layout.to_logical(screen,size))==cell
    assert layout.grid_at((1100,300)) is None
    assert layout.grid_at((100,40)) is None
    assert layout.grid_at((976,88)) is None
    if view.y: assert layout.to_logical((20,0),size) is None


def test_all_manifest_assets_load_and_are_cached(display):
    bank=AssetBank()
    manifest=json.loads((ASSET_ROOT/"manifest.json").read_text())
    for key,entry in manifest.items():
        assert (ASSET_ROOT/entry["file"]).is_file()
        first=bank.image(key,48)
        assert bank.image(key,48) is first
    assert not bank.missing
    for angle in range(360):bank.image("archer",40,angle)
    assert len([k for k in bank.cache if k[0]=="archer" and k[1]==(40,40)])==32


def test_missing_resources_have_safe_fallback(display,tmp_path):
    bank=AssetBank(tmp_path)
    assert bank.image("absent",48).get_size()==(48,48)
    assert "absent" in bank.missing

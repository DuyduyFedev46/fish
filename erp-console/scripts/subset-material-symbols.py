#!/usr/bin/env python3
"""Sinh tập con Material Symbols Outlined cho erp-console (public/fonts/ms/).

Tự host font icon (C.6/K8): chỉ giữ glyph của các icon đang dùng + chữ cái/chữ số/gạch dưới
(nguồn ligature) + feature 'liga'. Full font ~4 MB → tập con ~70 KB.

KHI THÊM ICON MỚI: bổ sung tên vào ICONS dưới đây rồi chạy:
    python3 scripts/subset-material-symbols.py
(cần pip install fonttools brotli; có mạng để tải full font từ fonts.gstatic.com)
"""
import subprocess
import sys
import urllib.request

FULL_URL = "https://fonts.gstatic.com/s/materialsymbolsoutlined/v374/kJEhBvYX7BgnkSrUwT8OhrdQw4oELdPIeeII9v6oFsLjBuVY.woff2"
OUT = "public/fonts/ms/material-symbols-outlined.woff2"

# Thu thập: grep -rhoE '<Icon name="[a-z0-9_]+"|icon="[a-z0-9_]+"|icon: "[a-z0-9_]+"' shared features app --include="*.tsx" --include="*.ts"
# (bỏ kết quả dương giả của name="..." của ô nhập) + các nhánh động <Icon name={...}>.
ICONS = sorted(set("""
add_circle add_photo_alternate arrow_forward auto_awesome badge block broken_image call cancel casino check
check_circle close cloud_done currency_exchange dashboard dark_mode delete description done_all edit edit_note error
event_busy expand_more fact_check filter_alt_off flag group groups help history inbox info inventory inventory_2 key
light_mode link link_off local_shipping lock logout manage_accounts menu monitoring more_horiz note package_2 payments
pending person_add person_check person_off photo_camera price_check progress_activity radio_button_checked radio_button_unchecked
receipt_long refresh replay report rule schedule search search_off sell send set_meal shield_person shopping_bag
shopping_cart sync sync_alt sync_problem task_alt timer timer_off two_wheeler undo visibility visibility_off
warning wifi_off chat forward_to_inbox
add calendar_today admin_panel_settings arrow_back article assignment_return category content_copy delete_forever done handshake insights left_panel_close left_panel_open north_east person phone_in_talk play_arrow policy receipt remove_moderator request_quote smart_toy south_west storefront swap_vert
""".split()))

from fontTools.ttLib import TTFont

urllib.request.urlretrieve(FULL_URL, "/tmp/ms-full.woff2")
font = TTFont("/tmp/ms-full.woff2")
cmap = font.getBestCmap()

def gname_cp(gname):
    if gname.startswith("uni") and len(gname) == 7:
        try:
            return int(gname[3:], 16)
        except ValueError:
            pass
    for cp, gn in cmap.items():
        if gn == gname:
            return cp
    return None

cp_of_gname = {gn: gname_cp(gn) for gn in font.getGlyphOrder()}

name_to_glyph = {}
for lookup in font["GSUB"].table.LookupList.Lookup:
    if lookup.LookupType != 4:
        continue
    for st in lookup.SubTable:
        for first, ligs in st.ligatures.items():
            for lig in ligs:
                cps = [cp_of_gname.get(first)]
                for c in lig.Component:
                    cps.append(cp_of_gname.get(c))
                if all(c is not None for c in cps):
                    name_to_glyph["".join(chr(c) for c in cps)] = lig.LigGlyph

codepoints = set()
missing = []
for icon in ICONS:
    gname = name_to_glyph.get(icon)
    if gname is None and icon in font.getGlyphOrder():
        gname = icon
    cp = cp_of_gname.get(gname) if gname else None
    if cp is None:
        missing.append(icon)
        continue
    codepoints.add(cp)

codepoints.update(range(0x61, 0x7B))
codepoints.update(range(0x30, 0x3A))
codepoints.add(0x5F)

print(f"icons ok: {len(ICONS) - len(missing)}/{len(ICONS)}")
if missing:
    print("MISSING (không có trong font — kiểm tra lại tên):", " ".join(missing))

unicodes = ",".join(f"U+{cp:04X}" for cp in sorted(codepoints))
args = [
    sys.executable, "-m", "fontTools.subset", "/tmp/ms-full.woff2",
    "--unicodes=" + unicodes,
    "--layout-features=liga,rlig,rclt",
    "--no-layout-closure",
    "--flavor=woff2",
    "--name-IDs=1,2,3,4,6",
    "--notdef-outline",
    "--output-file=" + OUT,
]
raise SystemExit(subprocess.call(args))

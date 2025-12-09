# -*- coding: utf-8 -*-
"""
Created on Tue Mar 16 15:08:31 2021

@author: yosis
"""

import datetime as dt

import dash
import dash_leaflet as dl

# =============== APP ===============
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "SISTEM MONITORING LONGSOR"
server = app.server  # untuk deployment (gunicorn/uwsgi)

# =============== KONFIG / KONSTANTA ===============
UTC = getattr(dt, "UTC", dt.timezone.utc)

# Ganti jika API/WS di host lain:
API_BASE = "https://websocket-server-v2.onrender.com"
# Kamu sudah set ini di filemu:
WS_URL   = "wss://websocket-server-v2.onrender.com/ws?days=30"

# Tile layers
OSM = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
ESRI_WORLD_IMAGERY = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
ESRI_WORLD_STREET  = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}"
ESRI_NATGEO        = "https://server.arcgisonline.com/ArcGIS/rest/services/NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}"
ESRI_WORLD_TOPO    = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}"
ATTR_OSM  = "© OpenStreetMap"
ATTR_ESRI = "Tiles © Esri"

# Sensor metadata (ADEL 1 & 2)
def mk_sensor(site, sid, lat, lon):
    return {"site": site, "sid": sid, "id": f"{site.upper()}-{sid}",
            "name": f"{site.replace('_',' ').upper()} • {sid}",
            "lat": lat, "lon": lon}

SENSORS = [
    # Adel 1
    #mk_sensor("adel_01", "001", -7.182945, 107.423266),
    #mk_sensor("adel_01", "002", -7.182901, 107.423262),
    #mk_sensor("adel_01", "003", -7.185076, 107.422732),
    #mk_sensor("adel_01", "004", -7.185120, 107.422790),
    #mk_sensor("adel_01", "005", -7.185219, 107.423187),
    #mk_sensor("adel_01", "007", -7.185186, 107.423130),
    # Adel 2
    #mk_sensor("adel_02", "001", -7.173495, 107.435926),
    #mk_sensor("adel_02", "002", -7.173514, 107.435931),
    #mk_sensor("adel_02", "003", -7.173323, 107.435929),
    #mk_sensor("adel_02", "004", -7.173091, 107.435755),
    # Adel 3
    #mk_sensor("adel_03", "001", -7.167185076832787, 107.41598156819852),
    #mk_sensor("adel_03", "002", -7.171742335327068, 107.4197581754299),
    # Adel ITS 1
    mk_sensor("adel_its_01", "1", -7.986852, 111.710213),
    mk_sensor("adel_its_01", "2", -7.986938, 111.710331),
    mk_sensor("adel_its_01", "3", -7.986995, 111.710469),
    mk_sensor("adel_its_01", "4", -7.986949, 111.709909),
    mk_sensor("adel_its_01", "5", -7.987028, 111.710118),
    mk_sensor("adel_its_01", "6", -7.987231, 111.710224),
]

# Status & ikon
STATUS_STYLE = {
    "CEK": {"label": "Alat Normal", "color": "#16a34a"},
    "ON":  {"label": "Peringatan Longsor", "color":"#dc2626"},
    "OFF": {"label": "Alat Off", "color":"#6b7280"},
}
ICON_SIZE   = [30, 30]
ICON_ANCHOR = [ICON_SIZE[0] // 2, ICON_SIZE[1]]
ICON_MAP = {
    "CEK": dict(url="normal.png",  size=ICON_SIZE, anchor=ICON_ANCHOR),
    "OFF": dict(url="offline.png", size=ICON_SIZE, anchor=ICON_ANCHOR),
    "ON":  dict(url="warning.gif", size=ICON_SIZE, anchor=ICON_ANCHOR),
}

# Feature ketersediaan MeasureControl
HAS_MEASURE = hasattr(dl, "MeasureControl")

# =============== UTIL FUNCS (dipakai layouts & callbacks) ===============
def normalize_sid(x):
    if x is None:
        return None
    s = str(x).strip()
    return s.zfill(3) if s.isdigit() else s

def fmt_time_utc(ts: dt.datetime | None) -> str:
    return "—" if not ts else ts.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")

def decide_status_from_now(last_seen: dt.datetime | None,
                           has_threshold_breach: bool,
                           last_status_txt: str | None,
                           stale_hours=3) -> str:
    """OFF jika last_seen >= 3 jam; jika tidak, ON bila teks ON atau ada breach; else CEK."""
    if last_seen is None:
        return "OFF"
    now = dt.datetime.now(dt.timezone.utc)
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=UTC)
    if (now - last_seen) >= dt.timedelta(hours=stale_hours):
        return "OFF"
    if (last_status_txt or "").upper() == "ON":
        return "ON"
    if has_threshold_breach:
        return "ON"
    return "CEK"

def parse_time_fields(item: dict) -> dt.datetime | None:
    """Prioritas 'direkam'; fallback gabungan 'tanggal' + 'jam' (UTC)."""
    import pandas as pd
    t = item.get("direkam")
    if t:
        ts = pd.to_datetime(t, utc=True, errors="coerce")
        return None if ts is None or str(ts) == "NaT" else ts.to_pydatetime()
    tanggal, jam = item.get("tanggal"), item.get("jam")
    if tanggal and jam:
        ts = pd.to_datetime(f"{tanggal} {jam}", utc=True, errors="coerce")
        return None if ts is None or str(ts) == "NaT" else ts.to_pydatetime()
    return None

def get_site_from_table(tb: str) -> str | None:
    tb = (tb or "").lower()
    if "adel_01" in tb: return "adel_01"
    if "adel_02" in tb: return "adel_02"
    if "adel_03" in tb: return "adel_03"
    if "adel_its_01" in tb: return "adel_its_01"
    return None

def to_float(x):
    try:
        return float(x)
    except Exception:
        return None








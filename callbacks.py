# callbacks.py
import json
import numpy as np
import pandas as pd
import plotly.graph_objs as go
from dash import Output, Input, State, no_update, ALL, html, dcc
import dash_leaflet as dl

from app import (
    app, UTC,
    SENSORS, STATUS_STYLE, ICON_MAP,
    fmt_time_utc, decide_status_from_now, to_float, parse_time_fields, get_site_from_table
)
from layouts import graphs_layout, render_drawer_children

# ====================== WS -> STORE PARSER ======================
@app.callback(
    Output("ws-parsed", "data"),
    Input("ws", "message"),
    prevent_initial_call=True
)
def on_ws_message(message):
    if not message:
        return no_update
    raw = message.get("data", message)
    try:
        payload = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return no_update

    out = {"updated_at": payload.get("timestamp"), "sensors": {}}
    tables = payload.get("tables", {})
    cache = {}
    for tb, content in tables.items():
        site = get_site_from_table(tb)
        items = (content or {}).get("items", [])
        for it in items:
            sid = (str(it.get("ID") or "").strip()).zfill(3)
            if not site or not sid:
                continue
            cache.setdefault(f"{site}:{sid}", {"items": []})["items"].append(it)

    for key, bundle in cache.items():
        rows = []
        for it in bundle["items"]:
            ts = parse_time_fields(it)
            if ts is None:
                continue
            rows.append({
                "time": ts,
                "X": to_float(it.get("delta_x")),
                "Y": to_float(it.get("delta_y")),
                "Z": to_float(it.get("delta_z") if ("delta_z" in it) else it.get("delya_z")),
                "status": (it.get("status") or "").upper(),
            })
        if not rows:
            continue
        rows.sort(key=lambda r: r["time"])
        out["sensors"][key] = {
            "time": [r["time"].astimezone(UTC).isoformat() for r in rows],
            "X": [r["X"] for r in rows],
            "Y": [r["Y"] for r in rows],
            "Z": [r["Z"] for r in rows],
            "last_seen": rows[-1]["time"].astimezone(UTC).isoformat(),
            "last_status": rows[-1]["status"],
        }
    return out

# ====================== MARKERS (real-time) ======================
def make_marker_component(meta: dict, dyn: dict | None):
    last_seen_dt, last_status_txt, has_breach = None, None, False
    if dyn:
        if dyn.get("last_seen"):
            try:
                last_seen_dt = pd.to_datetime(dyn["last_seen"], utc=True).to_pydatetime()
            except Exception:
                last_seen_dt = None
        last_status_txt = dyn.get("last_status")
        try:
            arr_x = np.array([v for v in (dyn.get("X") or []) if v is not None], dtype=float)
            arr_y = np.array([v for v in (dyn.get("Y") or []) if v is not None], dtype=float)
            arr_z = np.array([v for v in (dyn.get("Z") or []) if v is not None], dtype=float)
            has_breach = (np.any(np.abs(arr_x) > 1.0) or
                          np.any(np.abs(arr_y) > 1.0) or
                          np.any(np.abs(arr_z) > 1.0))
        except Exception:
            has_breach = False

    status_now = decide_status_from_now(last_seen_dt, has_breach, last_status_txt, stale_hours=3)
    cfg = STATUS_STYLE[status_now]
    icon_cfg = ICON_MAP[status_now]
    last_txt = fmt_time_utc(last_seen_dt)

    tip = dl.Tooltip(f"{meta['name']} • {cfg['label']}")
    pop = dl.Popup(children=html.Div(
        [
            html.Div(meta["name"], style={"fontWeight": 700, "marginBottom": "4px"}),
            html.Div(
                [
                    html.Span("Status: ", style={"fontWeight": 500}),
                    html.Span(
                        cfg["label"],
                        style={"backgroundColor": cfg["color"], "color": "white",
                               "padding": "2px 6px", "borderRadius": "6px",
                               "fontSize": "11px", "marginLeft": "4px"}
                    ),
                ]
            ),
            html.Div(["Terakhir diterima: ", html.Strong(last_txt)],
                     style={"marginTop": "4px", "color": "#444"}),
            html.Div(f"ID: {meta['sid']} • Site: {meta['site']}",
                     style={"marginTop": "2px", "color": "#666", "fontSize": "12px"}),
            html.Div(f"Koordinat: {meta['lat']:.6f}, {meta['lon']:.6f}",
                     style={"marginTop": "2px", "color": "#555", "fontSize": "12px"}),
        ],
        style={"minWidth": "240px"}
    ))

    return dl.Marker(
        id={"type": "sensor-marker", "sensor_id": meta["id"]},
        position=[meta["lat"], meta["lon"]],
        icon=dict(
            iconUrl=app.get_asset_url(icon_cfg["url"]),
            iconSize=icon_cfg["size"],
            iconAnchor=icon_cfg["anchor"],
            popupAnchor=[0, -icon_cfg["anchor"][1] + 6],
            tooltipAnchor=[0, -icon_cfg["anchor"][1] + 6],
        ),
        children=[tip, pop]
    )

@app.callback(
    Output("marker-layer", "children"),
    Input("ws-parsed", "data"),
    Input("status-interval", "n_intervals"),
)
def refresh_markers(ws_data, _tick):
    sensor_map = (ws_data or {}).get("sensors", {}) if ws_data else {}
    children = []
    for meta in SENSORS:
        key = f"{meta['site']}:{meta['sid']}"
        dyn = sensor_map.get(key)
        children.append(make_marker_component(meta, dyn))
    return children

# ====================== DRAWER EVENTS ======================
@app.callback(
    Output("drawer-open", "data"),
    Output("selected-sensor", "data"),
    Input({"type": "sensor-marker", "sensor_id": ALL}, "n_clicks"),
    prevent_initial_call=True
)
def on_marker_click(n_clicks_list):
    if not n_clicks_list:
        return no_update, no_update
    idx, max_clicks = None, 0
    for i, v in enumerate(n_clicks_list):
        if v and v > max_clicks:
            max_clicks, idx = v, i
    if idx is None:
        return no_update, no_update
    meta = SENSORS[idx]
    return True, {"site": meta["site"], "sid": meta["sid"], "name": meta["name"]}

@app.callback(
    Output("drawer", "children"),
    Output("drawer", "style"),
    Input("drawer-open", "data"),
    Input("selected-sensor", "data"),
    State("drawer", "style"),
    State("xrange-store", "data"),
    State("ws-parsed", "data"),
    prevent_initial_call=True
)
def update_drawer(is_open, selected, style, x_range, ws_data):
    style = style or {}
    if is_open and selected:
        df, last_seen, last_status_txt = df_from_ws(ws_data, selected["site"], selected["sid"])
        has_breach = False
        if not df.empty and (df[["X","Y","Z"]].abs() > 1.0).any(axis=1).tail(50).any():
            has_breach = True
        status = decide_status_from_now(last_seen, has_breach, last_status_txt, stale_hours=3)
        last_txt = fmt_time_utc(last_seen)
        initial_content = graphs_layout(selected["name"], df, x_range=x_range,
                                        status_text=status, last_seen_text=last_txt)
        style.update({
            "width": "420px",
            "borderLeft": "1px solid #e5e7eb",
            "boxShadow": "-6px 0 12px rgba(0,0,0,0.06)",
        })
        children = render_drawer_children(selected["name"], initial_content=initial_content)
    else:
        style.update({"width": "0px", "borderLeft": "none", "boxShadow": "none"})
        children = []
    return children, style

# tombol ✕ untuk tutup drawer (clientside)
app.clientside_callback(
    """
    function(n, open_state){
        if (typeof n === 'number' && n > 0) {
            return false;
        }
        return open_state;
    }
    """,
    Output("drawer-open", "data", allow_duplicate=True),
    Input("drawer-close", "n_clicks"),
    State("drawer-open", "data"),
    prevent_initial_call=True
)

# ====================== SHARED X-RANGE ======================
@app.callback(
    Output("xrange-store", "data"),
    Input({"type": "sensor-graph", "axis": ALL}, "relayoutData"),
    State({"type": "sensor-graph", "axis": ALL}, "id"),
    State("xrange-store", "data"),
    prevent_initial_call=True
)
def update_xrange(relayout_list, graph_ids, current):
    if not relayout_list or not graph_ids:
        return no_update
    for rel in relayout_list:
        if not rel:
            continue
        if rel.get("xaxis.autorange"):
            return None  # reset shared range
        r0 = rel.get("xaxis.range[0]")
        r1 = rel.get("xaxis.range[1]")
        if r0 is None or r1 is None:
            rng = rel.get("xaxis.range")
            if isinstance(rng, list) and len(rng) == 2:
                r0, r1 = rng[0], rng[1]
        if r0 is not None and r1 is not None:
            return {"start": r0, "end": r1}
    return no_update

@app.callback(
    Output({"type": "sensor-graph", "axis": ALL}, "figure"),
    Input("xrange-store", "data"),
    State({"type": "sensor-graph", "axis": ALL}, "figure"),
    prevent_initial_call=True
)
def apply_shared_range(x_range, figures):
    if not figures:
        return no_update
    out = []
    for fig in figures:
        if "layout" not in fig:
            fig["layout"] = {}
        fig["layout"]["xaxis"] = fig["layout"].get("xaxis", {})
        if x_range is None:
            fig["layout"]["xaxis"]["autorange"] = True
            fig["layout"]["xaxis"].pop("range", None)
        else:
            fig["layout"]["xaxis"]["range"] = [x_range["start"], x_range["end"]]
            fig["layout"]["xaxis"]["autorange"] = False
        out.append(fig)
    return out

# ====================== TAB CONTENT ======================
def df_from_ws(ws_data: dict | None, site: str, sid: str):
    if not ws_data:
        return pd.DataFrame(columns=["time","X","Y","Z"]), None, None
    s = (ws_data.get("sensors") or {}).get(f"{site}:{sid}")
    if not s:
        return pd.DataFrame(columns=["time","X","Y","Z"]), None, None
    t = pd.to_datetime(s.get("time") or [], utc=True, errors="coerce")
    df = pd.DataFrame({"time": t,
                       "X": pd.to_numeric(s.get("X") or [], errors="coerce"),
                       "Y": pd.to_numeric(s.get("Y") or [], errors="coerce"),
                       "Z": pd.to_numeric(s.get("Z") or [], errors="coerce")}).dropna(subset=["time"]).sort_values("time")
    last_seen = None
    if s.get("last_seen"):
        try:
            last_seen = pd.to_datetime(s["last_seen"], utc=True).to_pydatetime()
        except Exception:
            last_seen = None
    return df, last_seen, s.get("last_status")

@app.callback(
    Output("tab-content", "children"),
    Input("sensor-tabs", "value"),
    Input("ws-parsed", "data"),
    Input("status-interval", "n_intervals"),
    State("selected-sensor", "data"),
    State("xrange-store", "data"),
    prevent_initial_call=True
)
def render_tab(active_tab, ws_data, _tick, selected, x_range):
    if not selected:
        return html.Div()
    df, last_seen, last_status_txt = df_from_ws(ws_data, selected["site"], selected["sid"])
    has_breach = (not df.empty) and (df[["X","Y","Z"]].abs() > 1.0).any(axis=1).tail(50).any()
    status = decide_status_from_now(last_seen, has_breach, last_status_txt, stale_hours=3)
    last_txt = fmt_time_utc(last_seen)

    if active_tab == "tab-graph":
        return graphs_layout(selected["name"], df, x_range=x_range, status_text=status, last_seen_text=last_txt)
    elif active_tab == "tab-table":
        if df.empty:
            return html.Div("Tidak ada data untuk ditampilkan.", style={"padding":"8px","color":"#555"})
        tail = df.tail(50).copy()
        tail["time"] = tail["time"].dt.strftime("%Y-%m-%d %H:%M")
        fig = go.Figure(
            data=[go.Table(
                header=dict(values=list(tail.columns), fill_color="lightgrey", align="left"),
                cells=dict(values=[tail[c] for c in tail.columns], align="left")
            )],
            layout=go.Layout(margin=dict(l=0, r=0, t=10, b=0), height=360)
        )
        return html.Div(dcc.Graph(figure=fig), style={"height": "100%", "overflow": "auto"})
    elif active_tab == "tab-log":
        if df.empty:
            return html.Div("Tidak ada data.", style={"padding":"8px","color":"#555"})
        THRESH = 1.0
        m = (df[["X","Y","Z"]].abs() > THRESH)
        rows = []
        for comp in ["X","Y","Z"]:
            above = m[comp].values
            start = None
            for i, flag in enumerate(above):
                if flag and start is None:
                    start = df.iloc[i]["time"]
                if (not flag and start is not None) or (flag and i == len(above)-1):
                    end = df.iloc[i]["time"]
                    rows.append([comp, start.strftime("%Y-%m-%d %H:%M"), end.strftime("%Y-%m-%d %H:%M")])
                    start = None
        if not rows:
            rows = [["-", "-", "-"]]
        fig = go.Figure(
            data=[go.Table(
                header=dict(values=["Komponen", "Mulai (UTC)", "Selesai (UTC)"], fill_color="lightgrey", align="left"),
                cells=dict(values=[[r[0] for r in rows],[r[1] for r in rows],[r[2] for r in rows]], align="left")
            )],
            layout=go.Layout(margin=dict(l=0,r=0,t=10,b=0), height=360)
        )
        return html.Div(dcc.Graph(figure=fig), style={"height": "100%", "overflow": "auto"})
    return html.Div()

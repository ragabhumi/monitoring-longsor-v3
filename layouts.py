import plotly.graph_objs as go
import pandas as pd
import numpy as np
import dash_leaflet as dl
from dash_extensions import WebSocket
from dash_extensions.javascript import arrow_function
from dash import html, dcc

from app import (
    app, WS_URL, HAS_MEASURE,
    OSM, ESRI_WORLD_IMAGERY, ESRI_WORLD_STREET, ESRI_NATGEO, ESRI_WORLD_TOPO,
    ATTR_OSM, ATTR_ESRI, ICON_SIZE, ICON_MAP
)

# =============== HEADER & FOOTER ===============
header = html.Div(
    [
        html.Img(src="/assets/its.png", style={"height": "48px", "marginRight": "12px"}),
        html.Div("SISTEM MONITORING LONGSOR",
                 style={"fontWeight": 700, "fontSize": "20px", "color": "#000"})
    ],
    style={
        "display": "flex", "alignItems": "center", "gap": "8px",
        "padding": "12px 16px", "backgroundColor": "#e5e7eb",
        "borderBottom": "1px solid #d1d5db", "height": "64px",
    },
)

footer = html.Div(
    "© 2025 ProTech Engineering",
    style={
        "textAlign": "center", "padding": "8px 0",
        "backgroundColor": "#f3f4f6", "borderTop": "1px solid #d1d5db",
        "fontSize": "13px", "fontWeight": "400", "color": "#555",
        "letterSpacing": "0.3px", "height": "36px"
    }
)

# =============== FAULT OVERLAYS & LEGEND ===============
def popup_on_each_feature(default_text: str):
    return arrow_function(
        f"""
        function(feature, layer){{
            var props = feature && feature.properties ? feature.properties : {{}};
            var name = props.name || props.Nama || props.label || "{default_text}";
            layer.bindPopup(String(name));
        }}
        """
    )

def make_fault_overlay(filename: str, layer_id: str, display_name: str,
                       color: str, dashed: bool = False, checked: bool = True):
    style = {"color": color, "weight": 2.5, "opacity": 1.0}
    if dashed:
        style["dashArray"] = "6 4"
    return dl.Overlay(
        name=display_name,
        checked=checked,
        children=dl.GeoJSON(
            id=layer_id,
            url=app.get_asset_url(f'faults/{filename}'),
            options=dict(style=style, onEachFeature=popup_on_each_feature(display_name)),
            hoverStyle={"weight": 4, "opacity": 1.0},
        )
    )

def legend_item_line(label: str, color: str, dashed: bool = False):
    return html.Div(
        [
            html.Span(style={
                "display": "inline-block", "width": "26px", "height": "0px",
                "borderTop": f"3px {'dashed' if dashed else 'solid'} {color}",
                "marginRight": "8px",
            }),
            html.Span(label)
        ],
        style={"display": "flex", "alignItems": "center", "gap": "6px", "marginBottom": "6px"}
    )

def legend_control():
    def icon_img(filename):
        return html.Img(
            src=app.get_asset_url(filename),
            style={"width": f"{ICON_SIZE[0]}px", "height": f"{ICON_SIZE[1]}px", "marginRight": "6px"}
        )
    return html.Div(
        [
            html.Div("Status Sensor", style={"fontWeight":700,"marginBottom":"6px","fontSize":"12px"}),
            html.Div([icon_img(ICON_MAP["CEK"]["url"]), html.Span("Alat Normal")],
                     style={"display":"flex","alignItems":"center","marginBottom":"4px"}),
            html.Div([icon_img(ICON_MAP["OFF"]["url"]), html.Span("Alat Off")],
                     style={"display":"flex","alignItems":"center","marginBottom":"4px"}),
            html.Div([icon_img(ICON_MAP["ON"]["url"]),  html.Span("Peringatan Longsor")],
                     style={"display":"flex","alignItems":"center","marginBottom":"8px"}),
            html.Hr(style={"border":"none","borderTop":"1px solid #e5e7eb","margin":"6px 0"}),
            html.Div("Legenda Patahan", style={"fontWeight":700,"marginBottom":"6px","fontSize":"12px"}),
            legend_item_line("Confirmed Fault",        "#e11d48"),
            legend_item_line("Confirmed Fold",         "#8b5cf6"),
            legend_item_line("Confirmed Normal Fault", "#2563eb"),
            legend_item_line("Confirmed Thrust Fault", "#16a34a"),
            legend_item_line("Inferred Fault",         "#6b7280", dashed=True),
            legend_item_line("Inferred Normal Fault",  "#60a5fa", dashed=True),
            legend_item_line("Inferred Thrust Fault",  "#34d399", dashed=True),
        ],
        id="map-legend",
        style={
            "position": "absolute",
            "left": "12px",
            "bottom": "56px",
            "zIndex": 1000,
            "backgroundColor": "rgba(255,255,255,0.92)",
            "padding": "10px 12px",
            "border": "1px solid #e5e7eb",
            "borderRadius": "8px",
            "boxShadow": "0 2px 6px rgba(0,0,0,0.08)",
            "fontSize": "12px",
            "color": "#111",
            "pointerEvents": "auto",
            "minWidth": "220px"
        }
    )

# =============== MAP ===============
layers_control = dl.LayersControl(position="topright", children=[
    dl.BaseLayer(name="ESRI World Imagery (default)", checked=True, children=[
        dl.TileLayer(url=ESRI_WORLD_IMAGERY, attribution=ATTR_ESRI)
    ]),
    dl.BaseLayer(name="ESRI World Street Map", children=[
        dl.TileLayer(url=ESRI_WORLD_STREET, attribution=ATTR_ESRI)
    ]),
    dl.BaseLayer(name="ESRI NatGeo World Map", children=[
        dl.TileLayer(url=ESRI_NATGEO, attribution=ATTR_ESRI)
    ]),
    dl.BaseLayer(name="ESRI World Topo Map", children=[
        dl.TileLayer(url=ESRI_WORLD_TOPO, attribution=ATTR_ESRI)
    ]),
    dl.BaseLayer(name="OpenStreetMap", children=[
        dl.TileLayer(url=OSM, attribution=ATTR_OSM)
    ]),

    # Fault overlays
    make_fault_overlay("confirmed_fault.geojson",   "confirmed_fault",  "Confirmed Fault",         "#e11d48"),
    make_fault_overlay("confirmed_fold.geojson",    "confirmed_fold",   "Confirmed Fold",          "#8b5cf6"),
    make_fault_overlay("confirmed_normal.geojson",  "confirmed_normal", "Confirmed Normal Fault",  "#2563eb"),
    make_fault_overlay("confirmed_thrust.geojson",  "confirmed_thrust", "Confirmed Thrust Fault",  "#16a34a"),
    make_fault_overlay("inferred_fault.geojson",    "inferred_fault",   "Inferred Fault",          "#6b7280", dashed=True),
    make_fault_overlay("inferred_normal.geojson",   "inferred_normal",  "Inferred Normal Fault",   "#60a5fa", dashed=True),
    make_fault_overlay("inferred_thrust.geojson",   "inferred_thrust",  "Inferred Thrust Fault",   "#34d399", dashed=True),
])

scale = dl.ScaleControl(position="bottomleft", imperial=False, maxWidth=200)

map_children = [layers_control, scale]
if HAS_MEASURE:
    map_children.insert(1, dl.MeasureControl(
        position="topleft",
        primaryLengthUnit="kilometers",
        secondaryLengthUnit="meters",
        primaryAreaUnit="hectares",
        secondaryAreaUnit="sqmeters",
        activeColor="#2563eb",
        completedColor="#1f2937"
    ))

marker_layer = dl.LayerGroup(id="marker-layer", children=[])

marker_layer2 = dl.Marker(
            position=[-7.991325, 111.738081],
            icon=dict(
                iconUrl=app.get_asset_url("its.png"),
                iconSize=[30, 30],
                iconAnchor=[15, 30]),
            children=[
                dl.Tooltip("ADEL Host Sooko")
            ]
        )

the_map = dl.Map(
    id="map",
    center=[-7.990376583513643, 111.72472656353057],
    zoom=15,
    style={"width": "100%", "height": "calc(100vh - 64px - 36px)", "margin": "0", "display": "block"},
    children=map_children + [marker_layer, marker_layer2]
)

# =============== DRAWER & GRAFIK ===============
def graphs_layout(sensor_name, df, x_range=None, status_text="", last_seen_text=""):
    header_box = html.Div(
        [html.Div([html.Span("Status: ", style={"fontWeight": 600}),
                   html.Span(status_text or "-"),
                   html.Span(" • ", style={"padding":"0 6px","color":"#999"}),
                   html.Span("Terakhir: ", style={"fontWeight": 600}),
                   html.Span(last_seen_text or "-")],
                  style={"fontSize":"12px"})],
        style={"padding":"6px 8px","background":"#f8fafc","border":"1px solid #e5e7eb",
               "borderRadius":"8px","marginBottom":"8px"}
    )

    def make_fig(col):
        fig = go.Figure()
        if not df.empty:
            fig.add_trace(go.Scatter(x=df["time"], y=df[col], mode="lines", name="Nilai"))
            fig.add_trace(go.Scatter(x=[df["time"].min(), df["time"].max()],
                                     y=[1.0, 1.0], mode="lines",
                                     name="Threshold = 1", line=dict(dash="dash")))
        else:
            fig.add_trace(go.Scatter(x=[], y=[], mode="lines", name="Nilai"))
        if x_range and x_range.get("start") and x_range.get("end"):
            fig.update_xaxes(range=[x_range["start"], x_range["end"]])
        else:
            fig.update_xaxes(autorange=True)
        fig.update_layout(
            title=dict(text=f"{sensor_name}", font=dict(size=12)),
            margin=dict(l=40, r=10, t=24, b=18),
            xaxis_title=dict(text="Waktu (UTC)", font=dict(size=12)), yaxis_title=dict(text=f"Nilai {col}", font=dict(size=12)),
            uirevision="keep",
            legend=dict(
                x=0.99, y=0.99, xanchor="right", yanchor="top",
                bgcolor="rgba(255,255,255,0.6)",
                bordercolor="rgba(0,0,0,0.15)", borderwidth=1,
                font=dict(size=10), orientation="v"
            )
        )
        return fig

    graphs = html.Div(
        [dcc.Graph(id={"type": "sensor-graph", "axis": "X"},
                   figure=make_fig("X"),
                   style={"height": "33.333%", "flex": "1 1 0", "minHeight": 0},
                   config={"responsive": True}),
         dcc.Graph(id={"type": "sensor-graph", "axis": "Y"},
                   figure=make_fig("Y"),
                   style={"height": "33.333%", "flex": "1 1 0", "minHeight": 0},
                   config={"responsive": True}),
         dcc.Graph(id={"type": "sensor-graph", "axis": "Z"},
                   figure=make_fig("Z"),
                   style={"height": "33.333%", "flex": "1 1 0", "minHeight": 0},
                   config={"responsive": True})],
        style={"display": "flex", "flexDirection": "column", "gap": "8px", "height": "85%"}
    )

    if df.empty:
        empty = html.Div("Data tidak ditemukan dari API untuk sensor ini.",
                         style={"color":"#b45309","background":"#fff7ed","border":"1px solid #fde68a",
                                "padding":"8px","borderRadius":"8px","marginBottom":"8px","fontSize":"12px"})
        return html.Div([header_box, empty, graphs], style={"height":"100%"})
    return html.Div([header_box, graphs], style={"height":"100%"})

def render_drawer_children(sensor_name: str, initial_content):
    return [
        html.Div(
            [html.Div(sensor_name, style={"fontWeight": 700, "fontSize": "16px"}),
             html.Button("✕", id="drawer-close", n_clicks=0,
                         style={"border": "1px solid #e5e7eb", "background": "#fff",
                                "borderRadius": "8px", "padding": "2px 8px", "cursor": "pointer"})],
            style={"display": "flex", "justifyContent": "space-between", "alignItems": "center",
                   "padding": "10px 12px", "borderBottom": "1px solid #e5e7eb",
                   "backgroundColor": "#f9fafb"}
        ),
        html.Div(
            [dcc.Tabs(id="sensor-tabs", value="tab-graph",
                      children=[dcc.Tab(label="Grafik X/Y/Z", value="tab-graph"),
                                dcc.Tab(label="Tabel Nilai", value="tab-table"),
                                dcc.Tab(label="Log > Threshold", value="tab-log")],
                      style={"fontSize":"13px"}),
             html.Div(id="tab-content", style={"padding":"10px","height":"calc(100% - 44px)","overflow":"hidden"},
                      children=initial_content)],
            style={"height": "calc(100% - 48px)", "overflow": "hidden"}
        ),
    ]

def drawer_container(open_: bool, children=None):
    return html.Div(
        id="drawer",
        style={
            "position": "absolute","top": "0","right": "0","height": "100%",
            "width": "420px" if open_ else "0px","backgroundColor": "#ffffff",
            "borderLeft": "1px solid #e5e7eb" if open_ else "none",
            "boxShadow": "-6px 0 12px rgba(0,0,0,0.06)" if open_ else "none",
            "transition": "width 0.25s ease-in-out","overflow": "hidden","zIndex": 1100,
        },
        children=(children or []) if open_ else []
    )

# =============== ROOT LAYOUT ===============
def build_layout():
    return html.Div(
        [
            header,
            WebSocket(id="ws", url=WS_URL),
            dcc.Store(id="ws-parsed", data=None),
            dcc.Interval(id="status-interval", interval=60_000, n_intervals=0),
            html.Div(
                [
                    html.Div([the_map], style={"position": "relative", "height": "100%"}),
                    legend_control(),
                    drawer_container(open_=False),
                    dcc.Store(id="drawer-open", data=False),
                    dcc.Store(id="selected-sensor", data=None),
                    dcc.Store(id="xrange-store", data=None),
                ],
                style={"position": "relative", "flex": "1 1 auto"}
            ),
            footer
        ],
        style={"margin": 0, "padding": 0, "height": "100vh",
               "overflow": "hidden", "display": "flex", "flexDirection": "column"}
    )







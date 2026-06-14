"""
Create Kibana dashboards for ELK SIEM lab.
Run:  python create_dashboards.py
"""
import json, io, requests

BASE  = "http://localhost:5602"
AUTH  = ("elastic", "ElkLab@2024")

# Data view IDs
DV_WIN = "dde2a714-4299-455c-a08a-7ad0dc4c7172"
DV_WEB = "b8610632-2c3c-4455-b773-01a3ca9b4e0b"
DV_MSC = "900a6ba7-8757-449e-8b42-65f55152aa12"

# Fixed IDs so re-running overwrites instead of duplicating
ID = {
    # Windows vizs
    "w_time":     "elk-lab-w01-events-time",
    "w_evtid":    "elk-lab-w02-top-eventids",
    "w_channel":  "elk-lab-w03-by-channel",
    "w_level":    "elk-lab-w04-log-level",
    "w_logins":   "elk-lab-w05-login-success",
    "w_fails":    "elk-lab-w06-login-failure",
    "w_provider": "elk-lab-w07-event-provider",
    "w_tags":     "elk-lab-w08-security-tags",
    "dash_win":   "elk-lab-dash-windows-security",
    # Webapp vizs
    "a_time":     "elk-lab-a01-requests-time",
    "a_type":     "elk-lab-a02-log-type",
    "a_tags":     "elk-lab-a03-tags",
    "a_total":    "elk-lab-a04-total",
    "a_logins":   "elk-lab-a05-login-events",
    "a_agents":   "elk-lab-a06-agents",
    "dash_web":   "elk-lab-dash-webapp",
    # Overview vizs
    "o_misc_time":"elk-lab-o01-misc-time",
    "o_misc_tot": "elk-lab-o02-misc-total",
    "o_win_tot":  "elk-lab-o03-win-total",
    "o_web_tot":  "elk-lab-o04-web-total",
    "dash_over":  "elk-lab-dash-overview",
}

# ── Lens column builders ──────────────────────────────────────────────────────

def _count():
    return {
        "dataType": "number", "isBucketed": False,
        "label": "Count of records", "operationType": "count",
        "scale": "ratio", "sourceField": "___records___"
    }

def _date_histo():
    return {
        "dataType": "date", "isBucketed": True,
        "label": "@timestamp", "operationType": "date_histogram",
        "params": {"interval": "auto", "includeEmptyRows": True},
        "scale": "interval", "sourceField": "@timestamp"
    }

def _terms(field, size=10):
    return {
        "dataType": "string", "isBucketed": True,
        "label": f"Top {field}", "operationType": "terms",
        "params": {
            "orderBy": {"columnId": "col_c", "type": "column"},
            "orderDirection": "desc", "size": size,
            "missingBucket": False, "otherBucket": True,
            "parentFormat": {"id": "terms"}
        },
        "scale": "ordinal", "sourceField": field
    }

def _dv_ref(dv_id, layer="l1"):
    return [{"type": "index-pattern", "id": dv_id,
             "name": f"indexpattern-datasource-layer-{layer}"}]

# ── Lens visualization builders ───────────────────────────────────────────────

def xy_time(obj_id, dv_id, title, kql=""):
    return {
        "id": obj_id, "type": "lens",
        "attributes": {
            "title": title, "description": "",
            "visualizationType": "lnsXY",
            "state": {
                "datasourceStates": {
                    "formBased": {"layers": {"l1": {
                        "columnOrder": ["col_t", "col_c"],
                        "columns": {"col_t": _date_histo(), "col_c": _count()}
                    }}}
                },
                "visualization": {
                    "layers": [{
                        "accessors": ["col_c"], "layerId": "l1",
                        "layerType": "data", "seriesType": "bar_stacked",
                        "xAccessor": "col_t"
                    }],
                    "legend": {"isVisible": True, "position": "right"},
                    "preferredSeriesType": "bar_stacked",
                    "valueLabels": "hide", "fittingFunction": "None"
                },
                "filters": [],
                "query": {"language": "kuery", "query": kql}
            }
        },
        "references": _dv_ref(dv_id)
    }


def xy_terms(obj_id, dv_id, title, field, kql="", size=10):
    return {
        "id": obj_id, "type": "lens",
        "attributes": {
            "title": title, "description": "",
            "visualizationType": "lnsXY",
            "state": {
                "datasourceStates": {
                    "formBased": {"layers": {"l1": {
                        "columnOrder": ["col_k", "col_c"],
                        "columns": {"col_k": _terms(field, size), "col_c": _count()}
                    }}}
                },
                "visualization": {
                    "layers": [{
                        "accessors": ["col_c"], "layerId": "l1",
                        "layerType": "data", "seriesType": "bar",
                        "xAccessor": "col_k"
                    }],
                    "legend": {"isVisible": True, "position": "right"},
                    "preferredSeriesType": "bar",
                    "valueLabels": "hide"
                },
                "filters": [],
                "query": {"language": "kuery", "query": kql}
            }
        },
        "references": _dv_ref(dv_id)
    }


def pie(obj_id, dv_id, title, field, kql="", size=8, shape="donut"):
    return {
        "id": obj_id, "type": "lens",
        "attributes": {
            "title": title, "description": "",
            "visualizationType": "lnsPie",
            "state": {
                "datasourceStates": {
                    "formBased": {"layers": {"l1": {
                        "columnOrder": ["col_k", "col_c"],
                        "columns": {"col_k": _terms(field, size), "col_c": _count()}
                    }}}
                },
                "visualization": {
                    "layers": [{
                        "categoryDisplay": "default", "layerId": "l1",
                        "layerType": "data", "legendDisplay": "default",
                        "metrics": ["col_c"], "nestedLegend": False,
                        "numberDisplay": "percent", "primaryGroups": ["col_k"]
                    }],
                    "shape": shape
                },
                "filters": [],
                "query": {"language": "kuery", "query": kql}
            }
        },
        "references": _dv_ref(dv_id)
    }


def metric(obj_id, dv_id, title, kql=""):
    return {
        "id": obj_id, "type": "lens",
        "attributes": {
            "title": title, "description": "",
            "visualizationType": "lnsMetric",
            "state": {
                "datasourceStates": {
                    "formBased": {"layers": {"l1": {
                        "columnOrder": ["col_c"],
                        "columns": {"col_c": _count()}
                    }}}
                },
                "visualization": {
                    "layers": [{
                        "layerId": "l1", "layerType": "data",
                        "metricAccessor": "col_c"
                    }]
                },
                "filters": [],
                "query": {"language": "kuery", "query": kql}
            }
        },
        "references": _dv_ref(dv_id)
    }


# ── Dashboard builder ─────────────────────────────────────────────────────────

def panel(viz_id, idx, x, y, w, h, title=None):
    p = {
        "type": "lens", "version": "8.13.4",
        "gridData": {"x": x, "y": y, "w": w, "h": h, "i": f"p{idx}"},
        "panelIndex": f"p{idx}",
        "panelRefName": f"panel_{idx}",
        "embeddableConfig": {"enhancements": {}}
    }
    if title:
        p["title"] = title
    ref = {"id": viz_id, "name": f"panel_{idx}", "type": "lens"}
    return p, ref


def dashboard(obj_id, title, panel_pairs, time_from="now-7d"):
    panels = [p for p, _ in panel_pairs]
    refs   = [r for _, r in panel_pairs]
    return {
        "id": obj_id, "type": "dashboard",
        "attributes": {
            "title": title, "description": "",
            "panelsJSON": json.dumps(panels),
            "optionsJSON": json.dumps({
                "useMargins": True, "syncColors": True, "hidePanelTitles": False
            }),
            "timeRestore": True,
            "timeFrom": time_from, "timeTo": "now",
            "refreshInterval": {"pause": True, "value": 0},
            "kibanaSavedObjectMeta": {
                "searchSourceJSON": json.dumps({
                    "query": {"language": "kuery", "query": ""},
                    "filter": []
                })
            }
        },
        "references": refs
    }


# ── Build all objects ─────────────────────────────────────────────────────────

objects = []

# ── 1. Windows Security Dashboard ────────────────────────────────────────────
objects += [
    xy_time( ID["w_time"],     DV_WIN, "Events Over Time"),
    xy_terms(ID["w_evtid"],    DV_WIN, "Top Event IDs",        "winlog.event_id",     size=15),
    pie(     ID["w_channel"],  DV_WIN, "Events by Channel",    "winlog.channel"),
    pie(     ID["w_level"],    DV_WIN, "Events by Log Level",  "log.level"),
    metric(  ID["w_logins"],   DV_WIN, "Login Successes",      "tags: login_success"),
    metric(  ID["w_fails"],    DV_WIN, "Login Failures",       "tags: login_failure"),
    xy_terms(ID["w_provider"], DV_WIN, "Top Event Providers",  "event.provider",      size=10),
    xy_terms(ID["w_tags"],     DV_WIN, "Security Event Tags",  "tags",                size=10),
]

win_panels = [
    panel(ID["w_time"],      0,  0,  0, 48, 15),   # row 0 — full width
    panel(ID["w_evtid"],     1,  0, 15, 24, 15),   # row 1 — left
    panel(ID["w_channel"],   2, 24, 15, 12, 15),   # row 1 — centre
    panel(ID["w_level"],     3, 36, 15, 12, 15),   # row 1 — right
    panel(ID["w_logins"],    4,  0, 30,  8,  8),   # row 2 — metrics
    panel(ID["w_fails"],     5,  8, 30,  8,  8),
    panel(ID["w_tags"],      6, 16, 30, 32,  8),   # row 2 — tags bar
    panel(ID["w_provider"],  7,  0, 38, 48, 15),   # row 3 — full width
]
objects.append(dashboard(ID["dash_win"], "Windows Security", win_panels))


# ── 2. Webapp Activity Dashboard ──────────────────────────────────────────────
objects += [
    xy_time( ID["a_time"],   DV_WEB, "Request Volume Over Time"),
    pie(     ID["a_type"],   DV_WEB, "Log Type Breakdown",  "fields.log_subtype"),
    xy_terms(ID["a_tags"],   DV_WEB, "Tags Breakdown",      "tags",           size=10),
    metric(  ID["a_total"],  DV_WEB, "Total Log Events"),
    metric(  ID["a_logins"], DV_WEB, "Webapp Login Logs",   "tags: webapp"),
    xy_terms(ID["a_agents"], DV_WEB, "Events by Agent",     "agent.name",     size=10),
]

web_panels = [
    panel(ID["a_time"],   0,  0,  0, 48, 15),
    panel(ID["a_type"],   1,  0, 15, 24, 15),
    panel(ID["a_tags"],   2, 24, 15, 24, 15),
    panel(ID["a_total"],  3,  0, 30, 12,  8),
    panel(ID["a_logins"], 4, 12, 30, 12,  8),
    panel(ID["a_agents"], 5, 24, 30, 24,  8),
]
objects.append(dashboard(ID["dash_web"], "Webapp Activity", web_panels))


# ── 3. SIEM Overview Dashboard ────────────────────────────────────────────────
objects += [
    xy_time(ID["o_misc_time"], DV_MSC, "Misc Logs Over Time"),
    metric( ID["o_misc_tot"],  DV_MSC, "Total Misc Events"),
    metric( ID["o_win_tot"],   DV_WIN, "Total Windows Events"),
    metric( ID["o_web_tot"],   DV_WEB, "Total Webapp Events"),
]

over_panels = [
    panel(ID["o_win_tot"],   0,  0,  0, 16,  8),   # row 0 — 3 metrics
    panel(ID["o_web_tot"],   1, 16,  0, 16,  8),
    panel(ID["o_misc_tot"],  2, 32,  0, 16,  8),
    panel(ID["w_time"],      3,  0,  8, 48, 15),   # row 1 — windows time
    panel(ID["a_time"],      4,  0, 23, 48, 15),   # row 2 — webapp time
    panel(ID["o_misc_time"], 5,  0, 38, 48, 15),   # row 3 — misc time
]
objects.append(dashboard(ID["dash_over"], "SIEM Overview", over_panels))


# ── Import ────────────────────────────────────────────────────────────────────

ndjson = "\n".join(json.dumps(o) for o in objects)
buf    = io.BytesIO(ndjson.encode())

r = requests.post(
    f"{BASE}/api/saved_objects/_import?overwrite=true",
    auth=AUTH,
    headers={"kbn-xsrf": "true"},
    files={"file": ("dashboards.ndjson", buf, "application/ndjson")}
)

result = r.json()
if result.get("success"):
    print(f"Imported {result['successCount']} objects successfully.\n")
    print("Dashboards:")
    print(f"  SIEM Overview      -> {BASE}/app/dashboards#/view/{ID['dash_over']}")
    print(f"  Windows Security   -> {BASE}/app/dashboards#/view/{ID['dash_win']}")
    print(f"  Webapp Activity    -> {BASE}/app/dashboards#/view/{ID['dash_web']}")
else:
    print(f"HTTP {r.status_code}")
    for e in result.get("errors", []):
        print(f"  ERROR: {e.get('id')} — {e.get('error', {}).get('message', e)}")
    if not result.get("errors"):
        print(r.text[:500])

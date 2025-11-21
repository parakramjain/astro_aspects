"""
Single-file FastAPI app that serves BOTH the Aspect Cards JSON API and a lightweight Admin UI (HTMX + Tailwind).

Run:
    python -m pip install "fastapi>=0.115" "uvicorn[standard]>=0.30" "pydantic>=2.7" portalocker>=2.8 python-multipart>=0.0.9
    uvicorn aspect_card_mgmt:app --reload --host 127.0.0.1 --port 8788

Routes (UI):
  GET  /admin                         # dashboard + search
  GET  /admin/cards                   # HTMX table (filters: planet, aspect_code, q, page, page_size)
  GET  /admin/cards/new               # create new card (raw JSON editor with starter template)
  GET  /admin/cards/{card_id}         # edit existing card (raw JSON editor)
  POST /admin/cards                   # create from raw JSON payload
  POST /admin/cards/{card_id}         # save (replace) from raw JSON payload
  POST /admin/cards/{card_id}/delete  # delete card

JSON API:
  GET  /health
  GET  /cards
  GET  /cards/{card_id}
  POST /cards
  PUT  /cards/{card_id}
  PATCH /cards/{card_id}
  DELETE /cards/{card_id}
  GET  /schema
  GET  /enums

Notes:
- UI uses HTMX for partial refreshes and Tailwind (CDN). No build step.
- Raw JSON editor keeps you fast while you iterate. You can add a guided form later.
"""
from __future__ import annotations
import json, os, re, glob
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

import portalocker
from fastapi import FastAPI, HTTPException, Query, Body, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field, ValidationError, field_validator, ConfigDict
from .aspect_card_viewer import render_card_readonly  # HTML viewer components

# ---------------------------------
# Storage config
# ---------------------------------
ROOT_DIR = os.path.abspath(".")
KB_DIR = os.path.join(ROOT_DIR, "kb")
ASPECTS_DIR = os.path.join(KB_DIR, "aspects")
INDEX_PATH = os.path.join(KB_DIR, "index.json")

# ---------------------------------
# Domain constants
# ---------------------------------
ID_PATTERN = re.compile(r"^[A-Z]{3}_[A-Z]{3}_[A-Z]{3}__v\d+\.\d+\.\d+$")
PLANETS = ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn","Uranus","Neptune","Pluto"]
ASPECT_NAME_BY_CODE = {
    "CON": "Conjunction",
    "OPP": "Opposition",
    "SQR": "Square",
    "TRI": "Trine",
    "SXT": "Sextile",
}
ASPECT_CODES = list(ASPECT_NAME_BY_CODE.keys())

# ---------------------------------
# Pydantic models
# ---------------------------------
class LocalizedText(BaseModel):
    title: Optional[str] = None
    core: Optional[str] = None
    tone: Optional[str] = None

class AspectCardModel(BaseModel):
    id: str = Field(..., description="AAA_ASP_BBB__vX.Y.Z")
    pair: List[str] = Field(..., min_length=3, max_length=3)
    applies_to: List[str] = Field(default_factory=lambda: ["natal","transit","progressed"]) 
    # legacy: str; new bilingual: {"en": str, "hi": str}
    core_meaning: Union[str, Dict[str, str]]
    # facets legacy: {domain: str}; new: {domain: {"en": str, "hi": str}}
    facets: Dict[str, Union[str, Dict[str, str]]]
    # legacy: List[str]; new: {"en": [...], "hi": [...]}
    life_event_type: Union[List[str], Dict[str, List[str]]] = Field(default_factory=list, description="List or bilingual mapping of life event labels")
    risk_notes: Union[List[str], Dict[str, List[str]]] = Field(default_factory=list)
    # legacy: {phase: [..]}; new: {phase: {"en": [...], "hi": [...]}}
    actionables: Dict[str, Union[List[str], Dict[str, List[str]]]] = Field(default_factory=dict)
    keywords: Union[List[str], Dict[str, List[str]]] = Field(default_factory=list)
    quality_tags: Union[List[str], Dict[str, List[str]]] = Field(default_factory=list)
    weights_hint: Dict[str, Any] = Field(default_factory=dict)
    modifiers: Dict[str, Any] = Field(default_factory=dict)
    # legacy: List[str]; new: {"en": [...], "hi": [...]}
    theme_overlays: Union[List[str], Dict[str, List[str]]] = Field(default_factory=list)
    refs: List[str] = Field(default_factory=list)
    provenance: Dict[str, Any] = Field(default_factory=dict)
    # locales stays bilingual but allow either LocalizedText or raw dict for flexibility
    locales: Dict[str, Union[LocalizedText, Dict[str, Optional[str]]]] = Field(default_factory=dict)
    # retrieval.embedding_sections legacy: strings; new: {"en": str, "hi": str}; leave flexible
    retrieval: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def _id_format(cls, v: str) -> str:
        if not ID_PATTERN.match(v):
            raise ValueError("id must match AAA_ASP_BBB__vX.Y.Z (uppercase 3-letter codes)")
        return v

    @field_validator("pair")
    @classmethod
    def _pair_format(cls, v: List[str]) -> List[str]:
        if len(v) != 3:
            raise ValueError("pair must be [PlanetA, AspectName, PlanetB]")
        pa, an, pb = v
        if pa not in PLANETS or pb not in PLANETS:
            raise ValueError(f"Planet must be one of {PLANETS}")
        if an not in set(ASPECT_NAME_BY_CODE.values()):
            raise ValueError(f"AspectName must be one of {list(ASPECT_NAME_BY_CODE.values())}")
        return v

class AspectCardPatch(BaseModel):
    # Flexible partial update model; all fields optional; accept bilingual or legacy variants
    model_config = ConfigDict(extra='ignore')
    id: Optional[str] = None
    pair: Optional[List[str]] = None
    applies_to: Optional[List[str]] = None
    core_meaning: Optional[Union[str, Dict[str, str]]] = None
    facets: Optional[Dict[str, Union[str, Dict[str, str]]]] = None
    life_event_type: Optional[Union[List[str], Dict[str, List[str]]]] = None
    risk_notes: Optional[Union[List[str], Dict[str, List[str]]]] = None
    actionables: Optional[Dict[str, Union[List[str], Dict[str, List[str]]]]] = None
    keywords: Optional[Union[List[str], Dict[str, List[str]]]] = None
    quality_tags: Optional[Union[List[str], Dict[str, List[str]]]] = None
    weights_hint: Optional[Dict[str, Any]] = None
    modifiers: Optional[Dict[str, Any]] = None
    theme_overlays: Optional[Union[List[str], Dict[str, List[str]]]] = None
    refs: Optional[List[str]] = None
    provenance: Optional[Dict[str, Any]] = None
    locales: Optional[Dict[str, Union[LocalizedText, Dict[str, Optional[str]]]]] = None
    retrieval: Optional[Dict[str, Any]] = None

# ---------------------------------
# FS helpers with locking
# ---------------------------------

def ensure_dirs() -> None:
    os.makedirs(ASPECTS_DIR, exist_ok=True)
    os.makedirs(KB_DIR, exist_ok=True)

def card_path(card_id: str) -> str:
    return os.path.join(ASPECTS_DIR, f"{card_id}.json")

def load_card(card_id: str) -> AspectCardModel:
    path = card_path(card_id)
    if not os.path.exists(path):
        raise FileNotFoundError(card_id)
    # Use the locked file handle to avoid Windows sharing violations
    # Open in binary and decode UTF-8 to handle non-ASCII content on Windows
    with portalocker.Lock(path, "rb", timeout=5) as f:
        data = json.loads(f.read().decode("utf-8"))
    try:
        return AspectCardModel(**data)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())

def save_card(model: AspectCardModel) -> None:
    ensure_dirs()
    path = card_path(model.id)
    # Write UTF-8 to avoid encoding issues across platforms
    with portalocker.Lock(path, "wb", timeout=5) as f:
        payload_str = json.dumps(
            json.loads(model.model_dump_json(by_alias=False, exclude_none=False)),
            ensure_ascii=False,
            indent=2,
        )
        f.write(payload_str.encode("utf-8"))

def delete_card(card_id: str) -> None:
    path = card_path(card_id)
    if os.path.exists(path):
        os.remove(path)

def list_card_ids() -> List[str]:
    ensure_dirs()
    files = glob.glob(os.path.join(ASPECTS_DIR, "*.json"))
    return sorted([os.path.splitext(os.path.basename(p))[0] for p in files])

# ---------------------------------
# Field selection utilities
# ---------------------------------
def _parse_fields_param(fields: Optional[str]) -> List[List[str]]:
    """Parse a comma-separated fields string into list of dot-path segments.
    Example: "core_meaning,facets.career,locales.en.title" ->
             [["core_meaning"],["facets","career"],["locales","en","title"]]
    """
    if not fields:
        return []
    out: List[List[str]] = []
    for token in fields.split(","):
        t = token.strip()
        if not t:
            continue
        out.append([seg for seg in t.split(".") if seg])
    return out

def _get_by_path(data: Any, path: List[str]) -> tuple[Any, bool]:
    cur = data
    for seg in path:
        if isinstance(cur, dict) and seg in cur:
            cur = cur[seg]
        else:
            return None, False
    return cur, True

def _assign_by_path(dst: dict, path: List[str], value: Any) -> None:
    cur = dst
    for seg in path[:-1]:
        if seg not in cur or not isinstance(cur[seg], dict):
            cur[seg] = {}
        cur = cur[seg]
    cur[path[-1]] = value

def _select_fields_dict(data: dict, paths: List[List[str]]) -> dict:
    if not paths:
        return {}
    result: dict = {}
    for p in paths:
        val, ok = _get_by_path(data, p)
        if ok:
            _assign_by_path(result, p, val)
    return result

# ---------------------------------
# FastAPI app (standalone)
# ---------------------------------
app = FastAPI(title="AstroVision Aspect Cards App", version="1.0.0", description="Aspect Cards Admin + JSON API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- API endpoints --------------------
@app.get("/health")
def health():
    return {"ok": True, "ts": datetime.utcnow().isoformat() + "Z"}

@app.get("/")
def root_redirect():
    return RedirectResponse(url="/admin", status_code=307)

@app.get("/cards")
def list_cards_api(
    planet: Optional[str] = Query(None),
    aspect_code: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    ids = list_card_ids()
    results = []
    aspect_name = ASPECT_NAME_BY_CODE.get(aspect_code) if aspect_code else None
    for cid in ids:
        try:
            c = load_card(cid)
        except Exception:
            continue
        if planet and planet not in (c.pair[0], c.pair[2]):
            continue
        if aspect_name and c.pair[1] != aspect_name:
            continue
        if q:
            blob = json.dumps(json.loads(c.model_dump_json()), ensure_ascii=False).lower()
            if q.lower() not in blob:
                continue
        title_val = None
        if c.locales:
            en_loc = c.locales.get("en")
            if isinstance(en_loc, LocalizedText):
                title_val = en_loc.title
            elif isinstance(en_loc, dict):
                title_val = en_loc.get("title")
        results.append({"id": c.id, "pair": c.pair, "title": title_val})
    return {"total": len(results), "items": results[offset: offset + limit]}

@app.get("/cards/{card_id}", response_model=AspectCardModel)
def get_card_api(card_id: str):
    try:
        return load_card(card_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Card not found")

@app.get("/cards/{card_id}/fields")
def get_card_fields(card_id: str, fields: Optional[str] = Query(None, description="Comma-separated list of fields (dot notation for nested) e.g. core_meaning,facets.career,locales.en.title")):
    """Return only selected fields from a card.

    Examples:
     cards/JUP_TRI_SUN__v1.0.0/fields?fields=core_meaning,keywords /
      /cards/JUP_TRI_SUN__v1.0.0/fields?fields=facets.career,locales.en.title

    If a requested path doesn't exist it is silently skipped.
    """
    try:
        model = load_card(card_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Card not found")
    paths = _parse_fields_param(fields)
    if not paths:
        raise HTTPException(status_code=400, detail="fields query parameter required")
    raw = json.loads(model.model_dump_json())  # full dict
    selected = _select_fields_dict(raw, paths)
    return {"id": card_id, "fields": selected}

@app.post("/cards", status_code=201, response_model=AspectCardModel)
def create_card_api(card: AspectCardModel):
    path = card_path(card.id)
    if os.path.exists(path):
        raise HTTPException(status_code=409, detail="Card with this id already exists")
    save_card(card)
    return card

@app.put("/cards/{card_id}", response_model=AspectCardModel)
def replace_card_api(card_id: str, card: AspectCardModel):
    if card_id != card.id:
        raise HTTPException(status_code=400, detail="Path id and body id must match")
    save_card(card)
    return card

@app.patch("/cards/{card_id}", response_model=AspectCardModel)
def patch_card_api(card_id: str, patch: AspectCardPatch = Body(...)):
    try:
        existing = load_card(card_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Card not found")
    data = json.loads(existing.model_dump_json())
    patch_data = {k: v for k, v in patch.model_dump(exclude_none=True).items()}
    # merge locales
    if "locales" in patch_data and isinstance(patch_data["locales"], dict):
        loc = data.get("locales", {})
        for lang, payload in patch_data["locales"].items():
            base = loc.get(lang, {})
            if isinstance(payload, dict):
                base.update({k: v for k, v in payload.items() if v is not None})
                loc[lang] = base
        data["locales"] = loc
        del patch_data["locales"]
    data.update(patch_data)
    try:
        updated = AspectCardModel(**data)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())
    if updated.id != card_id:
        old = card_path(card_id)
        if os.path.exists(old):
            os.remove(old)
    save_card(updated)
    return updated

@app.delete("/cards/{card_id}", status_code=204)
def delete_card_api(card_id: str):
    try:
        load_card(card_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Card not found")
    delete_card(card_id)
    return {"ok": True}

@app.get("/schema")
def get_schema_api():
    return AspectCardModel.model_json_schema()

@app.get("/enums")
def enums_api():
    return {"planets": PLANETS, "aspect_codes": ASPECT_CODES, "aspect_names": ASPECT_NAME_BY_CODE}

# ---------------------------------
# UI templates (inline HTML with Tailwind + HTMX)
# ---------------------------------
TAILWIND = "https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css"
HTMX = "https://unpkg.com/htmx.org@1.9.12"

def page(title: str, body_html: str) -> HTMLResponse:
    html = f"""
    <!doctype html>
    <html lang='en'>
    <head>
      <meta charset='utf-8'>
      <meta name='viewport' content='width=device-width, initial-scale=1'>
      <title>{title}</title>
      <link rel='stylesheet' href='{TAILWIND}' />
      <script src='{HTMX}' defer></script>
      <script>
        function prettify(id) {{
          const ta = document.getElementById(id);
          try {{
            const obj = JSON.parse(ta.value);
            ta.value = JSON.stringify(obj, null, 2);
          }} catch (e) {{ alert('Invalid JSON: ' + e.message); }}
        }}
        function minify(id) {{
          const ta = document.getElementById(id);
          try {{
            const obj = JSON.parse(ta.value);
            ta.value = JSON.stringify(obj);
          }} catch (e) {{ alert('Invalid JSON: ' + e.message); }}
        }}
      </script>
    </head>
    <body class='bg-gray-50 min-h-screen'>
      <div class='max-w-7xl mx-auto p-6'>
        <header class='mb-6 flex items-center justify-between'>
          <h1 class='text-2xl font-semibold text-gray-800'>AstroVision • Aspect Cards Admin</h1>
          <nav class='space-x-2'>
            <a href='/admin' class='px-3 py-2 bg-indigo-600 text-white rounded-lg shadow'>Dashboard</a>
            <a href='/admin/cards/new' class='px-3 py-2 bg-green-600 text-white rounded-lg shadow'>New Card</a>
          </nav>
        </header>
        {body_html}
      </div>
    </body>
    </html>
    """
    return HTMLResponse(html)

# ---- UI helpers ----
LIST_ROW_TEMPLATE = """
<tr class='border-b hover:bg-gray-50'>
  <td class='px-3 py-2 font-mono text-sm'>{id}</td>
  <td class='px-3 py-2'>{pair0} <span class='text-gray-400'>·</span> {pair1} <span class='text-gray-400'>·</span> {pair2}</td>
  <td class='px-3 py-2'><a href='/admin/cards/{id}' class='text-indigo-600 hover:underline'>Edit</a></td>
</tr>
"""

def render_table(items: List[dict]) -> str:
    rows = []
    for item in items:
        pair = item.get("pair", ["?","?","?"])
        rows.append(LIST_ROW_TEMPLATE.format(id=item["id"], pair0=pair[0], pair1=pair[1], pair2=pair[2]))
    if not rows:
        rows = ["<tr><td class='px-3 py-6 text-center text-gray-500' colspan='3'>No results</td></tr>"]
    table = f"""
    <table class='min-w-full bg-white rounded-lg shadow overflow-hidden'>
      <thead class='bg-gray-100 text-left text-sm text-gray-600'>
        <tr>
          <th class='px-3 py-2'>ID</th>
          <th class='px-3 py-2'>Pair</th>
          <th class='px-3 py-2'>Actions</th>
        </tr>
      </thead>
      <tbody>
        {''.join(rows)}
      </tbody>
    </table>
    """
    return table

# -------------------- UI routes --------------------
@app.get("/admin", response_class=HTMLResponse)
def admin_home(request: Request):
    body = f"""
    <section class='mb-6'>
      <form class='grid grid-cols-1 md:grid-cols-4 gap-3' hx-get='/admin/cards' hx-target='#results' hx-trigger='submit'>
        <input type='text' name='q' placeholder='Search text…' class='border rounded-lg px-3 py-2'>
        <select name='planet' class='border rounded-lg px-3 py-2'>
          <option value=''>Any planet</option>
          {''.join([f"<option value='{p}'>{p}</option>" for p in PLANETS])}
        </select>
        <select name='aspect_code' class='border rounded-lg px-3 py-2'>
          <option value=''>Any aspect</option>
          {''.join([f"<option value='{c}'>{c} · {ASPECT_NAME_BY_CODE[c]}</option>" for c in ASPECT_CODES])}
        </select>
        <button class='px-3 py-2 bg-indigo-600 text-white rounded-lg'>Search</button>
      </form>
    </section>
    <section id='results' hx-get='/admin/cards' hx-trigger='load'>Loading…</section>
    """
    return page("Aspect Cards Admin", body)

@app.get("/admin/cards", response_class=HTMLResponse)
def admin_cards_list(request: Request, planet: Optional[str] = None, aspect_code: Optional[str] = None, q: Optional[str] = None, page: int = 1, page_size: int = 25):
    # reuse API listing
    payload = list_cards_api(planet=planet, aspect_code=aspect_code, q=q, limit=10_000, offset=0)
    items: List[dict] = payload["items"]
    total = payload["total"]
    start = max((page-1)*page_size, 0)
    end = start + page_size
    page_items = items[start:end]
    table_html = render_table(page_items)
    # pager
    last_page = (total + page_size - 1)//page_size
    pager = f"""
    <div class='flex items-center justify-between mt-3 text-sm'>
      <div>Showing <span class='font-medium'>{start+1 if total else 0}</span>–<span class='font-medium'>{min(end,total)}</span> of <span class='font-medium'>{total}</span></div>
      <div class='space-x-2'>
        <button hx-get='/admin/cards?page={max(1,page-1)}&page_size={page_size}&planet={planet or ''}&aspect_code={aspect_code or ''}&q={q or ''}' class='px-3 py-1 border rounded {"opacity-50 cursor-not-allowed" if page<=1 else ""}'>Prev</button>
        <button hx-get='/admin/cards?page={min(last_page,page+1)}&page_size={page_size}&planet={planet or ''}&aspect_code={aspect_code or ''}&q={q or ''}' class='px-3 py-1 border rounded {"opacity-50 cursor-not-allowed" if page>=last_page else ""}'>Next</button>
      </div>
    </div>
    """
    return HTMLResponse(table_html + pager)

@app.get("/admin/cards/new", response_class=HTMLResponse)
def admin_new_card():
    starter = {
        "id": "JUP_TRI_SUN__v1.0.0",
        "pair": ["Jupiter","Trine","Sun"],
        "applies_to": ["natal","transit","progressed"],
        "core_meaning": "<one-sentence canonical meaning>",
        "facets": {"career":"","relationships":"","money":"","health_adj":""},
        "life_event_type": [],
        "risk_notes": [],
        "actionables": {"applying": [], "exact": [], "separating": []},
        "keywords": [],
        "quality_tags": ["major"],
        "weights_hint": {"default_orb_deg": 6, "planet_weight": {"Jupiter": 0.9, "Sun": 1.0}, "class_weight": {"natal": 1.0, "transit": 0.9, "progressed": 0.8}},
        "modifiers": {"dignity_adjustment": {}, "retrograde_adjustment": {}},
        "theme_overlays": [],
        "refs": [],
        "provenance": {"author": "Your Name", "reviewed_at": datetime.utcnow().date().isoformat()},
        "locales": {"en": {"title": "", "core": "", "tone": "warm"}, "hi": {"title": "", "core": "", "tone": "सरल"}},
        "retrieval": {"embedding_sections": {"core": "", "career": "", "relationships": "", "money": "", "health_adj": ""}, "aliases": []}
    }
    json_text = json.dumps(starter, ensure_ascii=False, indent=2)
    body = f"""
    <div class='bg-white rounded-lg shadow p-4'>
      <h2 class='text-lg font-semibold mb-3'>New Aspect Card</h2>
      <form method='post' action='/admin/cards'>
        <textarea id='json' name='json' rows='28' class='w-full font-mono text-sm border rounded-lg p-3'>{json_text}</textarea>
        <div class='mt-3 flex gap-2'>
          <button type='button' onclick='prettify("json")' class='px-3 py-2 border rounded'>Beautify</button>
          <button type='button' onclick='minify("json")' class='px-3 py-2 border rounded'>Minify</button>
          <button class='px-3 py-2 bg-green-600 text-white rounded'>Create</button>
        </div>
      </form>
    </div>
    """
    return page("New Card", body)

@app.post("/admin/cards")
def admin_create_card(payload: str = Form(...)):
    try:
        data_str = payload.strip() if payload else "{}"
        parsed = json.loads(data_str)
        if not isinstance(parsed, dict):
            raise ValueError("JSON payload must be an object")
        model = AspectCardModel(**parsed)
    except Exception as e:
        return HTMLResponse(f"<pre class='text-red-600 p-4'>Invalid JSON or schema: {e}</pre>", status_code=400)
    if os.path.exists(card_path(model.id)):
        return HTMLResponse("<pre class='text-red-600 p-4'>Card id already exists.</pre>", status_code=409)
    save_card(model)
    return RedirectResponse(url=f"/admin/cards/{model.id}", status_code=303)

@app.get("/admin/cards/{card_id}", response_class=HTMLResponse)
def admin_edit_card(card_id: str):
    try:
        model = load_card(card_id)
    except FileNotFoundError:
        return page("Not Found", f"<div class='text-red-600'>Card {card_id} not found.</div>")
    json_text = json.dumps(json.loads(model.model_dump_json()), ensure_ascii=False, indent=2)
    body = f"""
    <div class='bg-white rounded-lg shadow p-4'>
      <div class='flex items-center justify-between mb-3'>
        <h2 class='text-lg font-semibold'>Edit Card <span class='font-mono text-sm text-gray-500'>{card_id}</span></h2>
        <form method='post' action='/admin/cards/{card_id}/delete' onsubmit='return confirm("Delete this card?")'>
          <button class='px-3 py-2 bg-red-600 text-white rounded'>Delete</button>
        </form>
      </div>
            <div class='mb-4'>
                <a href='/admin/cards/{card_id}/view' class='text-indigo-600 text-sm underline'>Switch to viewer</a>
            </div>
      <form method='post' action='/admin/cards/{card_id}'>
        <textarea id='json' name='json' rows='30' class='w-full font-mono text-sm border rounded-lg p-3'>{json_text}</textarea>
        <div class='mt-3 flex gap-2'>
          <button type='button' onclick='prettify("json")' class='px-3 py-2 border rounded'>Beautify</button>
          <button type='button' onclick='minify("json")' class='px-3 py-2 border rounded'>Minify</button>
          <button class='px-3 py-2 bg-indigo-600 text-white rounded'>Save</button>
          <a href='/admin' class='px-3 py-2 border rounded'>Back</a>
        </div>
      </form>
    </div>
    """
    return page(f"Edit {card_id}", body)

@app.get("/admin/cards/{card_id}/view", response_class=HTMLResponse)
def admin_view_card(card_id: str):
        """Read-only structured viewer for a card using the viewer components module."""
        try:
                model = load_card(card_id)
        except FileNotFoundError:
                return page("Not Found", f"<div class='text-red-600'>Card {card_id} not found.</div>")
        viewer_html = render_card_readonly(model)
        body = f"""
        <div class='bg-white rounded-lg shadow p-5'>
            <div class='flex items-center justify-between mb-4'>
                <h2 class='text-lg font-semibold'>View Card <span class='font-mono text-sm text-gray-500'>{card_id}</span></h2>
                <div class='flex gap-2'>
                    <a href='/admin/cards/{card_id}' class='px-3 py-2 bg-indigo-600 text-white rounded text-sm'>Edit JSON</a>
                    <a href='/admin' class='px-3 py-2 border rounded text-sm'>Dashboard</a>
                </div>
            </div>
            {viewer_html}
        </div>
        """
        return page(f"View {card_id}", body)

@app.post("/admin/cards/{card_id}")
def admin_save_card(card_id: str, payload: str = Form(...)):
    try:
        data_str = payload.strip() if payload else "{}"
        parsed = json.loads(data_str)
        if not isinstance(parsed, dict):
            raise ValueError("JSON payload must be an object")
        model = AspectCardModel(**parsed)
    except Exception as e:
        return HTMLResponse(f"<pre class='text-red-600 p-4'>Invalid JSON or schema: {e}</pre>", status_code=400)
    if model.id != card_id:
        # allow rename by moving the file
        old_path = card_path(card_id)
        if os.path.exists(old_path):
            os.remove(old_path)
    save_card(model)
    return RedirectResponse(url=f"/admin/cards/{model.id}", status_code=303)

@app.post("/admin/cards/{card_id}/delete")
def admin_delete_card(card_id: str):
    try:
        delete_card_api(card_id)
    except HTTPException as e:
        return HTMLResponse(f"<pre class='text-red-600 p-4'>Error: {e.detail}</pre>", status_code=e.status_code)
    return RedirectResponse(url="/admin", status_code=303)

# Bootstrap dirs
ensure_dirs()

if __name__ == "__main__":
    # Dev convenience: preview some data & hint how to start server.
    # card_ids = list_card_ids()
    # print(f"Aspect Cards Admin app is ready. {len(card_ids)} cards available.")
    # if card_ids:
    #     print("card_ids[0]:", card_ids[0])
    #     sample_card = load_card(card_ids[0])
    #     print(f"Sample card ({sample_card.id}):")
    #     print(json.dumps(json.loads(sample_card.model_dump_json()), ensure_ascii=False, indent=2))
    # print("Run: uvicorn aspect_card_mgmt:app --reload --host 127.0.0.1 --port 8788")
    print("'C:\\Users\\parak\\anaconda3\\python.exe' -m uvicorn aspect_card_utils.aspect_card_mgmt:app --reload --host 127.0.0.1 --port 8788")
    # output = load_card("JUP_CON_MOO__v1.0.0")
    # get life_event_type field only
    # life_event_type = output.life_event_type
    # print(json.dumps(life_event_type, ensure_ascii=False, indent=2))
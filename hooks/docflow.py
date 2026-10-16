"""DocFlow: convierte los markdown de docs/funcionalidades/ (plantilla técnica 3.1.0)
en páginas con el diseño de client.css.

Contrato de la plantilla (todo documento que llegue a docs/funcionalidades/ lo cumple):

    # <nombre>
    > <resumen>
    **Entidad:** `X` · **Capacidad:** lectura · **Documentación:** vN · **Actualizada:** AAAA-MM-DD · **Confianza:** N%

    ## Resumen                      (obligatoria; tabla de funcionalidades + "Fuera de alcance")
    ## Empezar rápido                (condicional; rutas base + headers + autenticación)
    ## Cómo funciona                 (obligatoria; ### por servicio con #### diagrama(s) y #### Paso a paso;
                                      ### Reglas a respetar, una sola vez)
    ## Endpoints | Funcionalidades   (obligatoria; ### por funcionalidad)
    ## Respuestas comunes            (condicional)
    ## Modelos                       (condicional; ### por modelo)
    ## Advertencias                  (condicional)
    ## Fuentes de datos              (condicional)
    ## Configuración                 (condicional)
    ## Glosario                      (condicional)

Las secciones condicionales se omiten por completo cuando no hay contenido: aquí no se
renderiza ni se lista en el menú nada que el documento no traiga. Los encabezados H2 se
identifican por nombre (sin numerar); el id HTML de cada sección es el slug de su título
(`modelos`, `respuestas-comunes`, …) para que los enlaces internos de la plantilla funcionen.
Un H2 fuera de la plantilla se renderiza de forma genérica y emite un aviso en el build.

El front-matter YAML es opcional y solo admite `icono`, `orden` y `title`.

Cada .md se renderiza con overrides/docflow.html; la portada (overrides/docflow-home.html)
recibe la lista de documentos para armar el índice y el menú.
"""
import html
import logging
import re
import unicodedata

import markdown
import yaml
from mkdocs.exceptions import PluginError

log = logging.getLogger("mkdocs.hooks.docflow")

PLANTILLA_VERSION = "3.1.0"  # subir cuando cambie la estructura o los encabezados de la plantilla
DOCS_FOLDER = "funcionalidades/"
TEMPLATE = "docflow.html"
METHODS = "GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS"

_docs = []
_pages = {}


# ───────────────────────── utilidades ─────────────────────────

def esc(text):
    return html.escape(text, quote=False)


def norm(text):
    """Clave de comparación: minúsculas, sin tildes ni formato."""
    text = unicodedata.normalize("NFKD", plain(text)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", text.lower()).strip()


def slugify(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:64]


def plain(text):
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    return re.sub(r"[*_`]", "", text).strip()


def truncate(text, limit=260):
    text = " ".join(plain(text).split())
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(",;:.") + "…"


def icon(name, extra=""):
    return f'<span class="material-icons-round"{extra}>{name}</span>'


_inline_md = markdown.Markdown(extensions=["attr_list"])
_block_md = markdown.Markdown(extensions=["attr_list", "sane_lists"])


def tag(text):
    return f'<span class="tag">{text}</span>'


def tagify(h):
    """Html con nombres separados por comas (fuera de <code>) -> un tag por nombre."""
    parts = [p.strip() for p in re.split(r",\s*(?![^<]*</code>)", h.strip()) if p.strip()]
    return "".join(tag(p) for p in parts)


def decorate(h):
    """Convierte las marcas '*(Aplica a: …)*' en tags."""
    return re.sub(r"<em>\(Aplica a:?\s*(.*?)\)</em>",
                  lambda m: f'<span class="applies">Aplica a {tagify(m.group(1))}</span>', h)


def inline(text):
    _inline_md.reset()
    out = _inline_md.convert(text.strip())
    out = re.sub(r"^<p>|</p>$", "", out.strip())
    return decorate(out)


def block(text):
    if not text.strip():
        return ""
    _block_md.reset()
    return olists_to_timeline(decorate(_block_md.convert(text)))


def func_html(h):
    """`GET /ruta` (en <code>) -> badge del método + ruta."""
    return re.sub(
        rf"<code>({METHODS})\s+([^<]+)</code>",
        lambda m: f'<span class="method m-{m.group(1).lower()}">{m.group(1)}</span>'
                  f'<code class="route">{m.group(2)}</code>', h)


def split_func_title(title):
    """'`GET /x` — Etiqueta' -> ('GET', '/x', 'Etiqueta'); sin método -> (None, None, título)."""
    m = re.match(rf"^`({METHODS})\s+([^`]+)`\s*(?:[—–-]\s*(.*))?$", title.strip())
    if not m:
        return None, None, plain(title)
    return m.group(1), m.group(2), plain(m.group(3) or m.group(2))


def olists_to_timeline(h):
    def step(it):
        it = re.sub(r"^<p>|</p>$", "", it.strip())
        m = re.match(r"^<strong>(.*?)</strong>\s*[—–-]\s*(.*)$", it, re.S)
        if m:
            return (f'<div class="step-component">{m.group(1)}</div>'
                    f'<div class="timeline-desc">{m.group(2).strip()}</div>')
        return f'<div class="timeline-desc">{it}</div>'

    def repl(m):
        body = m.group(1)
        if "<ul" in body or "<ol" in body:
            return m.group(0)
        items = re.findall(r"<li>(.*?)</li>", body, re.S)
        if len(items) < 2:
            return m.group(0)
        rows = "".join(
            '<div class="timeline-item"><div class="timeline-dot">'
            f'<span class="step-num">{i}</span></div><div class="timeline-content">'
            f'{step(it)}</div></div>'
            for i, it in enumerate(items, 1))
        return f'<div class="timeline">{rows}</div>'
    return re.sub(r"<ol>\n(.*?)\n</ol>", repl, h, flags=re.S)


# ───────────────────────── parseo ─────────────────────────

FENCE = re.compile(r"^```[^\n]*\n.*?^```[ \t]*$", re.M | re.S)
COMMENT = re.compile(r"<!--.*?-->", re.S)


def split_front_matter(text):
    text = text.replace("\r\n", "\n").lstrip("﻿")
    m = re.match(r"^---\n(.*?)\n---\n?", text, re.S)
    if not m:
        return {}, text
    meta = yaml.safe_load(m.group(1)) or {}
    if not isinstance(meta, dict):
        raise ValueError("el front-matter debe ser un mapa YAML")
    return meta, text[m.end():]


def strip_comments(text):
    out, last = [], 0
    for m in FENCE.finditer(text):
        out.append(COMMENT.sub("", text[last:m.start()]))
        out.append(m.group(0))
        last = m.end()
    out.append(COMMENT.sub("", text[last:]))
    return "".join(out)


def parse_tree(text):
    """Árbol de encabezados H1 > H2 > H3 > H4 con el texto propio de cada nodo."""
    root = {"level": 0, "title": "", "text": [], "children": []}
    stack = [root]
    in_fence = False
    for line in text.split("\n"):
        if line.startswith("```"):
            in_fence = not in_fence
        m = None if in_fence else re.match(r"^(#{1,4})\s+(.*?)\s*$", line)
        if m:
            level = len(m.group(1))
            node = {"level": level, "title": m.group(2).strip(), "text": [], "children": []}
            while stack[-1]["level"] >= level:
                stack.pop()
            stack[-1]["children"].append(node)
            stack.append(node)
        elif not in_fence and re.fullmatch(r"-{3,}", line.strip()):
            continue
        else:
            stack[-1]["text"].append(line)

    def finish(n):
        n["text"] = "\n".join(n["text"]).strip("\n")
        for c in n["children"]:
            finish(c)
    finish(root)
    return root


def segments(text):
    """Separa el texto en bloques: markdown, tabla, código."""
    lines, out, buf, i = text.split("\n"), [], [], 0

    def flush():
        if "".join(buf).strip():
            out.append(("md", "\n".join(buf)))
        buf.clear()

    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            j, body = i + 1, []
            while j < len(lines) and not lines[j].startswith("```"):
                body.append(lines[j])
                j += 1
            flush()
            out.append(("code", line[3:].strip(), "\n".join(body)))
            i = j + 1
        elif (line.lstrip().startswith("|") and i + 1 < len(lines)
              and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1])):
            j = i
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                j += 1
            flush()
            out.append(("table", lines[i:j]))
            i = j
        else:
            buf.append(line)
            i += 1
    flush()
    return out


def paragraphs(text):
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def split_row(line):
    line = line.strip()
    line = line[1:] if line.startswith("|") else line
    line = line[:-1] if line.endswith("|") and not line.endswith("\\|") else line
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line)]


def bullets(text):
    """(texto previo, [items]) para una lista con viñetas."""
    lead, items = [], []
    for line in text.split("\n"):
        m = re.match(r"^\s*[*-]\s+(.*)$", line)
        if m:
            items.append(m.group(1))
        elif items and line.startswith((" ", "\t")) and line.strip():
            items[-1] += " " + line.strip()
        elif not items:
            lead.append(line)
    return "\n".join(lead).strip(), items


def split_item(item):
    """'**Nombre:** descripción' -> (nombre, descripción)."""
    m = re.match(r"\*\*(.+?)\*\*(.*)$", item, re.S)
    if not m:
        return "", item
    return m.group(1).rstrip(": "), m.group(2).lstrip(": ").strip()


META_KEYS = {"entidad": "entidad", "capacidad": "capacidad", "documentacion": "version",
             "actualizada": "fecha", "confianza": "confianza"}


def parse_header(h1):
    """Resumen (blockquote) y línea de metadatos que cuelgan del `# título`."""
    quote, meta = [], {}
    for line in h1["text"].split("\n"):
        s = line.strip()
        if s.startswith(">"):
            quote.append(s.lstrip("> ").strip())
        elif s.startswith("**Entidad:**"):
            for part in s.split("·"):
                m = re.match(r"\*\*(.+?):\*\*\s*(.*)$", part.strip())
                if not m or norm(m.group(1)) not in META_KEYS:
                    continue
                key, value = META_KEYS[norm(m.group(1))], plain(m.group(2))
                if key == "version":
                    value = value.lstrip("vV")
                elif key == "confianza":
                    value = value.rstrip("% ")
                meta[key] = value
    return " ".join(quote).strip(), meta


# ───────────────────────── render de bloques ─────────────────────────

def badge(kind, text):
    return f'<span class="badge {kind}"><span class="badge-dot"></span>{esc(text)}</span>'


def cell_html(header, raw):
    h = plain(header).lower()
    text = plain(raw)
    if h == "nullable":
        if text.startswith("Sí"):
            return badge("pending", text)
        if text == "No":
            return badge("yes", text)
    if h in ("obligatorio", "req."):
        if text == "Sí":
            return badge("yes", text)
        if text == "No":
            return badge("pending", text)
    if h.startswith("código") and re.fullmatch(r"\d{3}", text):
        kind = {"2": "yes", "4": "pending", "5": "no"}.get(text[0], "pending")
        return badge(kind, text)
    if h == "aplica a" and text:
        return tagify(inline(raw))
    if h == "funcionalidad":
        return func_html(inline(raw))
    return inline(raw)


def render_table(lines):
    rows = [split_row(l) for l in lines]
    headers, body = rows[0], rows[2:]
    ths = "".join(f"<th>{inline(h)}</th>" for h in headers)
    trs = "".join(
        "<tr>" + "".join(f"<td>{cell_html(headers[i] if i < len(headers) else '', c)}</td>"
                         for i, c in enumerate(r)) + "</tr>"
        for r in body)
    return (f'<div class="table-container"><table><thead><tr>{ths}</tr></thead>'
            f'<tbody>{trs}</tbody></table></div>')


def render_code(lang, body):
    if lang == "mermaid":
        return f'<div class="diagram"><pre class="mermaid">{esc(body)}</pre></div>'
    return ('<div class="code-block"><div class="code-head">'
            f'<span>{esc(lang or "texto")}</span>'
            f'<button class="copy-btn" type="button" aria-label="Copiar">{icon("content_copy")}</button></div>'
            f'<pre><code>{esc(body)}</code></pre></div>')


def render_text(text, card=True):
    """Renderiza un bloque de markdown sin encabezados."""
    out = []
    for seg in segments(text):
        if seg[0] == "md":
            h = block(seg[1])
            out.append(f'<div class="card prose">{h}</div>' if card else h)
        elif seg[0] == "table":
            out.append(render_table(seg[1]))
        else:
            out.append(render_code(seg[1], seg[2]))
    return "".join(out)


def feature_items(items, ico, cls=""):
    rows = []
    for it in items:
        name, desc = split_item(it)
        if not name:
            name, desc = it, ""
        rows.append(
            f'<div class="feature-item {cls}">{icon(ico)}<div class="feature-item-info">'
            f'<div class="feature-item-name">{inline(name)}</div>'
            + (f'<div class="feature-item-desc">{inline(desc)}</div>' if desc else "")
            + "</div></div>")
    return f'<div class="feature-list">{"".join(rows)}</div>'


def data_section(title, inner, ico):
    return (f'<div class="data-section"><div class="data-section-title">{icon(ico)}'
            f'{esc(title)}</div>{inner}</div>')


def label_only(par):
    """'**Parámetros**' (párrafo de una sola línea en negrita, sin ':') -> 'Parámetros'."""
    m = re.fullmatch(r"\*\*([^*:]+)\*\*", par.strip())
    return m.group(1).strip() if m else None


# ───────────────────────── render por sección ─────────────────────────

def render_resumen(node):
    out = []
    for seg in segments(node["text"]):
        if seg[0] == "table":
            out.append(render_table(seg[1]))
        elif seg[0] == "code":
            out.append(render_code(seg[1], seg[2]))
        elif re.match(r"\*\*Fuera de alcance:?\*\*", seg[1].strip()):
            lead, items = bullets(seg[1])
            out.append(data_section("Fuera de alcance", feature_items(items, "cancel", "out"), "block"))
        else:
            out.append(f'<div class="card prose">{block(seg[1])}</div>')
    return "".join(out)


def render_quickstart(node):
    out = []
    for seg in segments(node["text"]):
        if seg[0] == "table":
            out.append(render_table(seg[1]))
        elif seg[0] == "code":
            out.append(render_code(seg[1], seg[2]))
        else:
            conn, rest = [], []
            for line in seg[1].split("\n"):
                m = re.match(r"^\*\*(URL base|Ruta base):\*\*\s*(.*)$", line.strip())
                if m:
                    conn.append((m.group(1), m.group(2)))
                else:
                    rest.append(line)
            if conn:
                items = "".join(
                    f'<div class="conn-item"><span class="conn-label">{esc(k)}</span>{inline(v)}</div>'
                    for k, v in conn)
                out.append(f'<div class="conn">{items}</div>')
            if "".join(rest).strip():
                out.append(f'<div class="info-card">{icon("key")}<div>{block(chr(10).join(rest))}</div></div>')
    return "".join(out)


def render_service(node):
    sid = f"flujo-{slugify(plain(node['title']))}"
    parts = [render_text(node["text"])] if node["text"].strip() else []
    for c in node["children"]:
        if norm(c["title"]).startswith("paso a paso"):
            parts.append(f'<h4 class="subsection-title">{icon("format_list_numbered")}Paso a paso</h4>'
                         + render_steps(c["text"]))
        else:
            parts.append(f'<h4 class="subsection-title">{icon("account_tree")}{inline(c["title"])}</h4>'
                         + render_text(c["text"], card=False))
    return (f'<article class="service-card" id="{sid}"><h3 class="service-title">'
            f'{func_html(inline(node["title"]))}</h3>{"".join(parts)}</article>')


def render_steps(text):
    """Pasos numerados; en recorridos conjuntos, cada servicio trae su rótulo `**`GET /a`**`."""
    out = []
    for seg in segments(text):
        if seg[0] == "md":
            h = block(seg[1])
            h = re.sub(r"<p><strong>(<code>[^<]+</code>)</strong></p>",
                       r'<h5 class="service-label">\1</h5>', h)
            out.append(func_html(h))
        elif seg[0] == "table":
            out.append(render_table(seg[1]))
        else:
            out.append(render_code(seg[1], seg[2]))
    return "".join(out)


def render_flow(node):
    out = []
    if node["text"].strip():
        out.append(render_text(node["text"]))
    for c in node["children"]:
        if norm(c["title"]) == "reglas a respetar":
            lead, items = bullets(c["text"])
            inner = (block(lead) if lead else "") + (feature_items(items, "rule") if items else "")
            out.append(data_section("Reglas a respetar", inner, "gavel"))
        else:
            out.append(render_service(c))
    return "".join(out)


def render_endpoint(node):
    sid = f"ep-{slugify(plain(node['title']))}"
    out = [f'<h3 class="endpoint-title">{func_html(inline(node["title"]))}</h3>']
    for seg in segments(node["text"]):
        if seg[0] == "table":
            out.append(render_table(seg[1]))
        elif seg[0] == "code":
            out.append(render_code(seg[1], seg[2]))
        else:
            for par in paragraphs(seg[1]):
                label = label_only(par)
                impl = re.match(r"^\*\*Implementaci[oó]n:\*\*\s*(.*)$", par, re.S)
                if label:
                    out.append(f'<h4 class="subsection-title">{esc(label)}</h4>')
                elif impl:
                    out.append(f'<div class="impl-row">{icon("code")}<span>Implementación</span>'
                               f'{inline(impl.group(1))}</div>')
                else:
                    out.append(f'<div class="endpoint-text">{block(par)}</div>')
    return f'<article class="endpoint-card" id="{sid}">{"".join(out)}</article>'


def render_endpoints(node):
    out = [render_text(node["text"])] if node["text"].strip() else []
    out += [render_endpoint(c) for c in node["children"]]
    return "".join(out)


def render_model(node):
    sid = f"modelo-{slugify(plain(node['title']))}"
    out = [f'<h3 class="model-title">{inline(node["title"])}</h3>']
    for seg in segments(node["text"]):
        if seg[0] == "table":
            out.append(render_table(seg[1]))
        elif seg[0] == "code":
            out.append(render_code(seg[1], seg[2]))
        elif re.match(r"\*\*Garant[ií]as:?\*\*", seg[1].strip()):
            lead, items = bullets(seg[1])
            lis = "".join(f"<li>{inline(i)}</li>" for i in items)
            out.append(f'<div class="info-card">{icon("verified")}<div>'
                       f'<p><strong>Garantías</strong></p><ul>{lis}</ul></div></div>')
        else:
            out.append(f'<div class="endpoint-text">{block(seg[1])}</div>')
    return f'<article class="model-card" id="{sid}">{"".join(out)}</article>'


def render_models(node):
    out = [render_text(node["text"])] if node["text"].strip() else []
    out += [render_model(c) for c in node["children"]]
    return "".join(out)


def render_warnings(node):
    lead, items = bullets(node["text"])
    cards = []
    for it in items:
        name, desc = split_item(it)
        cards.append(
            f'<div class="alert-card warn"><div class="alert-icon">{icon("warning_amber")}</div>'
            f'<div><div class="alert-title">{inline(name or it)}</div>'
            f'<div class="alert-desc">{inline(desc)}</div></div></div>')
    return (block(lead) if lead else "") + f'<div class="alert-cards wide">{"".join(cards)}</div>'


def render_generic(node):
    out = [render_text(node["text"])] if node["text"].strip() else []
    for c in node["children"]:
        out.append(f'<h4 class="subsection-title">{inline(c["title"])}</h4>' + render_text(c["text"]))
    return "".join(out)


# clave normalizada -> (icono, variante de color, grupo del menú, renderer)
GROUPS = ["Uso", "Funcionamiento", "Referencia"]
SECTIONS = {
    "resumen": ("list_alt", "", 0, render_resumen),
    "empezar rapido": ("rocket_launch", "green", 0, render_quickstart),
    "como funciona": ("account_tree", "green", 1, render_flow),
    "endpoints": ("api", "", 0, render_endpoints),
    "funcionalidades": ("api", "", 0, render_endpoints),
    "respuestas comunes": ("reply_all", "green", 0, render_generic),
    "modelos": ("data_object", "", 0, render_models),
    "advertencias": ("warning", "amber", 1, render_warnings),
    "fuentes de datos": ("storage", "green", 1, render_generic),
    "configuracion": ("tune", "", 1, render_generic),
    "glosario": ("menu_book", "green", 2, render_generic),
}
REQUIRED = [("resumen",), ("como funciona",), ("endpoints", "funcionalidades")]
CAPACIDAD_ICONS = {"lectura": "manage_search", "escritura": "edit_note", "actualizacion": "edit_note",
                   "eliminacion": "delete", "sincronizacion": "sync_alt", "calculo": "calculate",
                   "notificacion": "notifications"}


def render_section(node, sid, spec):
    ico, color, _, renderer = spec
    return (f'<section class="section" id="{sid}"><div class="section-header">'
            f'<div class="section-icon {color}">{icon(ico)}</div>'
            f'<h2 class="section-title">{esc(node["title"])}</h2></div>'
            f'<div class="data-section">{renderer(node)}</div></section>')


# ───────────────────────── validación ─────────────────────────

def validate(file, title, summary, meta, h2s, func_names, raw_body):
    src = file.src_uri
    if title.startswith("<"):
        log.warning("%s: el título es un placeholder de la plantilla (%s)", src, title)
    if not summary:
        log.warning("%s: falta el resumen (`> …`) bajo el título", src)
    elif summary.startswith("<"):
        log.warning("%s: el resumen es un placeholder de la plantilla", src)
    for key in ("entidad", "capacidad", "version", "fecha", "confianza"):
        if not meta.get(key):
            log.warning("%s: falta '%s' en la línea de metadatos", src, key)
    keys = [norm(n["title"]) for n in h2s]
    for alternatives in REQUIRED:
        if not any(k in keys for k in alternatives):
            log.warning("%s: falta la sección obligatoria '%s'", src, alternatives[0])
    for n in h2s:
        if norm(n["title"]) not in SECTIONS:
            log.warning("%s: la sección '%s' no pertenece a la plantilla %s", src, n["title"], PLANTILLA_VERSION)
        if not n["text"].strip() and not n["children"]:
            log.warning("%s: la sección '%s' está vacía (las condicionales se eliminan por completo)",
                        src, n["title"])

    def walk(n):
        if re.search(r"(?<!\w)<[A-Za-z_][\w. ]*>", n["title"]):
            log.warning("%s: el encabezado '%s' tiene un placeholder sin llenar", src, n["title"])
        for c in n["children"]:
            walk(c)
    for n in h2s:
        walk(n)

    if func_names:
        known = {norm(f) for f in func_names}
        for m in re.finditer(r"\(Aplica a:?\s*(.*?)\)\*", raw_body):
            for name in re.findall(r"`([^`]+)`", m.group(1)):
                if norm(name) not in known:
                    log.warning("%s: 'Aplica a' referencia '%s', que no está en la tabla de Resumen", src, name)


# ───────────────────────── documento completo ─────────────────────────

def build_doc(file, meta_fm, body):
    clean = strip_comments(body)
    tree = parse_tree(clean)
    h1s = tree["children"]
    if not h1s:
        raise ValueError("el documento no tiene un título `# …`")
    if len(h1s) > 1:
        log.warning("%s: hay más de un `#`; solo el primero es el título", file.src_uri)

    summary, hmeta = parse_header(h1s[0])
    title = str(meta_fm.get("title") or h1s[0]["title"])
    h2s = [c for h in h1s for c in h["children"]]

    # funcionalidades declaradas en el Resumen
    func_names = []
    resumen = next((n for n in h2s if norm(n["title"]) == "resumen"), None)
    if resumen:
        tbl = next((s for s in segments(resumen["text"]) if s[0] == "table"), None)
        if tbl:
            func_names = [plain(split_row(l)[0]) for l in tbl[1][2:]]

    validate(file, title, summary, hmeta, h2s, func_names, clean)

    rendered, groups, ids = [], [[] for _ in GROUPS], set()
    for n in h2s:
        spec = SECTIONS.get(norm(n["title"]), ("article", "", 2, render_generic))
        if not n["text"].strip() and not n["children"]:
            continue
        sid = slugify(n["title"]) or "seccion"
        while sid in ids:
            sid += "-2"
        ids.add(sid)
        rendered.append(render_section(n, sid, spec))
        link = {"id": sid, "title": n["title"], "icon": spec[0], "children": []}
        if spec[3] is render_endpoints:
            for c in n["children"]:
                method, _, label = split_func_title(c["title"])
                link["children"].append({"id": f"ep-{slugify(plain(c['title']))}", "title": label,
                                         "method": method, "mclass": (method or "").lower()})
        groups[spec[2]].append(link)

    capacidad = hmeta.get("capacidad", "")
    entidad = hmeta.get("entidad", "")
    confianza = hmeta.get("confianza", "")
    version = hmeta.get("version", "")
    n_func = len(func_names)

    stats = []
    if n_func:
        stats.append((n_func, "Funcionalidades" if n_func != 1 else "Funcionalidad"))
    if confianza:
        stats.append((f"{confianza}%", "Confianza"))
    if version:
        stats.append((f"v{version}", "Versión"))

    return {
        "src_uri": file.src_uri,
        "url": file.url,
        "title": title,
        "summary": truncate(summary, 400),
        "icon": str(meta_fm.get("icono") or CAPACIDAD_ICONS.get(norm(capacidad), "description")),
        "entidad": entidad,
        "capacidad": capacidad,
        "confianza": confianza,
        "version": version,
        "fecha": hmeta.get("fecha", ""),
        "order": meta_fm.get("orden", 1000),
        "n_func": n_func,
        "stats": stats,
        "groups": [{"label": GROUPS[i], "links": g} for i, g in enumerate(groups) if g],
        "has_mermaid": "mermaid" in "".join(rendered),
        "html": "".join(rendered),
    }


# ───────────────────────── hooks de MkDocs ─────────────────────────

def on_files(files, config):
    _docs.clear()
    _pages.clear()
    for f in files.documentation_pages():
        name = f.src_uri.rsplit("/", 1)[-1]
        if (not f.src_uri.startswith(DOCS_FOLDER) or name.startswith("_")
                or name.lower() in ("index.md", "readme.md")):
            continue
        try:
            meta, body = split_front_matter(f.content_string)
            _pages[f.src_uri] = build_doc(f, meta, body)
        except Exception as e:
            raise PluginError(f"docflow: error al procesar {f.src_uri}: {e}") from e
    _docs.extend(sorted(_pages.values(), key=lambda d: (d["order"], d["title"].lower())))
    log.info("docflow: %d documento(s) en %s (plantilla %s)", len(_docs), DOCS_FOLDER, PLANTILLA_VERSION)
    return files


def on_page_markdown(md_text, page, config, files):
    doc = _pages.get(page.file.src_uri)
    if not doc:
        return md_text
    page.meta["template"] = TEMPLATE
    try:
        page.title = doc["title"]
    except AttributeError:
        pass
    return ""


def on_page_content(html_, page, config, files):
    doc = _pages.get(page.file.src_uri)
    return doc["html"] if doc else html_


def on_page_context(context, page, config, nav):
    context["docflow_docs"] = _docs
    context["docflow"] = _pages.get(page.file.src_uri)
    return context

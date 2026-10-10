"""Makes the editor as one file that works offline: editor.html with its stylesheet, fonts and photos inside.

Run from the repository root, after tools/build.py:  python3 tools/editor_local.py [output.html]
The file opens from the desktop with a double click; nothing else is needed.
Each photo is stored once (lighter copies, at most 1200 px), in a list the editor reads by its place on
the site (data-sk-src), so a replaced photo can be put back in assets/.
"""
import base64
import io
import json
import mimetypes
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TYPES = {".woff2": "font/woff2", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".svg": "image/svg+xml"}


def data_uri(rel):
    path = os.path.join(ROOT, rel.split("?")[0])
    kind = TYPES.get(os.path.splitext(path)[1].lower()) or mimetypes.guess_type(path)[0] or "application/octet-stream"
    with open(path, "rb") as f:
        return f"data:{kind};base64,{base64.b64encode(f.read()).decode()}"


def photo_uri(rel, size=1200, quality=72):
    """A lighter JPEG copy for the editor; the site keeps its own files."""
    from PIL import Image
    im = Image.open(os.path.join(ROOT, rel))
    im.thumbnail((size, size))
    buf = io.BytesIO()
    im.convert("RGB").save(buf, "JPEG", quality=quality, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "sakim-editor.html")
    with open(os.path.join(ROOT, "editor.html"), encoding="utf-8") as f:
        page = f.read()

    # the stylesheet, with its fonts inside
    with open(os.path.join(ROOT, "assets/css/site.css"), encoding="utf-8") as f:
        css = f.read()
    css = re.sub(r"url\(\.\./(fonts/[^)]+)\)", lambda m: f"url({data_uri('assets/' + m.group(1))})", css)
    page = re.sub(r'<link rel="stylesheet" href="assets/css/site\.css[^"]*">', lambda m: f"<style>\n{css}\n</style>", page)
    page = re.sub(r'<link rel="preload"[^>]*>\n', "", page)
    page = re.sub(r'<link rel="icon" href="(assets/[^"]+)">', lambda m: f'<link rel="icon" href="{data_uri(m.group(1))}">', page)

    # every photo once, in a list the editor reads (window.SK_IMG); the <img> keeps where it lives on the site
    paths = sorted(set(re.findall(r'src="(assets/img/[^"]+)"', page)))
    images = {p: photo_uri(p) if p.lower().endswith((".jpg", ".jpeg")) else data_uri(p) for p in paths}
    # the archived photos, smaller still: they are only for choosing (the site uses the files themselves)
    archive = json.loads(re.search(r'<script type="application/json" id="sk-archive">(.*?)</script>', page).group(1))
    for path in (p for ps in archive.values() for p in ps):
        images.setdefault(path, photo_uri(path, 400, 60))
    page = re.sub(r'src="(assets/img/[^"]+)"', r'data-sk-src="\1"', page)
    page = page.replace("</head>", f"<script>window.SK_IMG = {json.dumps(images)};</script>\n</head>", 1)

    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    print("wrote", out, f"({os.path.getsize(out) / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()

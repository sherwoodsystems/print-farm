# app.py
import os
import base64
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from reportlab.lib.pagesizes import inch
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics

PORT = int(os.getenv("PORT", "3001"))
OUTPUT_DIR = os.getenv("OUTPUT_DIR", r"C:\labels")  # change if you prefer
DEFAULT_LABEL_SIZE = os.getenv("LABEL_SIZE", "2x4")  # '1x3' | '2x4' | '4x6'

LABEL_SIZES = {
    "1x3": (1.0 * inch, 3.0 * inch),
    "2x4": (2.0 * inch, 4.0 * inch),
    "4x6": (4.0 * inch, 6.0 * inch),
}

app = Flask(__name__)
CORS(app)

os.makedirs(OUTPUT_DIR, exist_ok=True)

def _wrap_text_to_lines(text: str, font_name: str, font_size: float, max_width: float, max_lines: int = 3):
    words = text.split()
    if not words:
        return [""], True

    lines = [""]
    for word in words:
        candidate = word if lines[-1] == "" else lines[-1] + " " + word
        width = pdfmetrics.stringWidth(candidate, font_name, font_size)
        if width <= max_width:
            lines[-1] = candidate
        else:
            # move to next line
            if len(lines) + 1 > max_lines:
                return lines, False
            lines.append(word)

    return lines, True


def make_pdf_big_bold_landscape(path, page_size_portrait, content):
    # Force landscape by swapping width/height
    ph_w, ph_h = page_size_portrait
    width, height = ph_h, ph_w

    margin = 0.15 * inch
    avail_w = max(width - 2 * margin, 1)
    avail_h = max(height - 2 * margin, 1)

    c = canvas.Canvas(path, pagesize=(width, height))
    font_name = "Helvetica-Bold"

    text = (content or "").strip() or "LABEL"

    # Binary search the largest font size that fits within width/height with up to 3 lines
    min_size = 6.0
    # Upper bound heuristic: ensure even the longest word can fit width-wise at size=hi
    longest_word = max(text.split(), key=len) if text.split() else "LABEL"
    lw_base = max(pdfmetrics.stringWidth(longest_word, font_name, 1), 1)
    hi_by_width = avail_w / lw_base
    hi_by_height = avail_h / 1.05  # 1.05 line height factor
    max_size = max(min(hi_by_width, hi_by_height), min_size)

    best_size = min_size
    best_lines = [text]
    for _ in range(22):
        mid = (min_size + max_size) / 2.0
        # Wrap into at most 3 lines at this font size
        lines, ok = _wrap_text_to_lines(text, font_name, mid, avail_w, max_lines=3)
        if not ok:
            # too big; doesn't fit width-wise into <=3 lines
            max_size = mid
            continue
        # Check height
        line_height = mid * 1.1
        total_h = line_height * len(lines)
        if total_h <= avail_h:
            best_size = mid
            best_lines = lines
            min_size = mid
        else:
            max_size = mid

    # Draw centered block
    c.setFont(font_name, best_size)
    line_height = best_size * 1.1
    total_h = line_height * len(best_lines)
    start_y = (height + total_h) / 2 - line_height * 0.75  # slight visual tweak
    x = width / 2
    y = start_y
    for line in best_lines:
        c.drawCentredString(x, y, line)
        y -= line_height

    c.showPage()
    c.save()

@app.get("/")
def root():
    return jsonify({
        "status": "running",
        "outputDir": OUTPUT_DIR,
        "defaultLabelSize": DEFAULT_LABEL_SIZE,
        "endpoints": {
            "POST /generate": "Generate a PDF label (no printing)",
            "GET /files/<name>": "Download a generated PDF"
        }
    })

@app.get("/files/<path:filename>")
def get_file(filename: str):
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=False)

@app.post("/generate")
def generate():
    payload = request.get_json(silent=True) or {}
    template = payload.get("template", "simple")
    data = payload.get("data", {}) or {}
    label_size = payload.get("labelSize", DEFAULT_LABEL_SIZE)
    copies = int(payload.get("copies", 1))  # ignored for now, no printing

    if label_size not in LABEL_SIZES:
        return jsonify({"error": f"Invalid labelSize. Use one of {list(LABEL_SIZES.keys())}"}), 400

    page_size = LABEL_SIZES[label_size]

    # Generate a filename and path
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S-%f")
    filename = f"label_{label_size}_{ts}.pdf"
    filepath = os.path.join(OUTPUT_DIR, filename)

    # Landscape, single-line, bold-as-big-as-possible text
    make_pdf_big_bold_landscape(
        path=filepath,
        page_size_portrait=page_size,
        content=str(data.get("content", ""))
    )

    # Return metadata and a URL to view the file
    return jsonify({
        "ok": True,
        "template": template,
        "labelSize": label_size,
        "file": filename,
        "path": filepath,
        "url": f"http://{request.host}/files/{filename}"
    }), 200

if __name__ == "__main__":
    # Bind to all interfaces so Tailscale/LAN can reach it
    app.run(host="0.0.0.0", port=PORT)
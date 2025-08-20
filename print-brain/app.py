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

    # Compute font size to fit single line within box
    # stringWidth scales linearly with font size
    base_width = pdfmetrics.stringWidth(text, font_name, 1)
    if base_width <= 0:
        base_width = 1

    size_by_width = avail_w / base_width
    # Height fudge: approximate that a line needs ~1.1x font size of vertical space
    size_by_height = avail_h / 1.1
    font_size = max(6, min(size_by_width, size_by_height))

    c.setFont(font_name, font_size)

    # Draw centered
    x = width / 2
    y = height / 2 - (font_size * 0.3)  # visual centering tweak
    c.drawCentredString(x, y, text)

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
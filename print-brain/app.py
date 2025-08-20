# app.py
import os
import base64
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from reportlab.lib.pagesizes import inch
from reportlab.pdfgen import canvas

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

def make_pdf_simple(path, page_size, content, align="center", text_align="center", font_size="12pt"):
    # Parse font size like "12pt"
    try:
        size_pt = int(str(font_size).replace("pt", "").strip())
    except Exception:
        size_pt = 12

    width, height = page_size
    c = canvas.Canvas(path, pagesize=page_size)
    c.setFont("Helvetica", size_pt)

    # Split content lines
    lines = (content or "").splitlines() or ["Label Content"]

    # Determine starting y based on alignment
    line_height = size_pt * 1.25
    total_text_height = line_height * len(lines)
    if align == "start":
        y = height - line_height * 1.5
    elif align == "end":
        y = total_text_height + line_height
    else:
        y = (height + total_text_height) / 2

    # Draw lines with text alignment
    for line in lines:
        line = line.strip()
        if text_align == "left":
            x = 0.2 * inch
            c.drawString(x, y, line)
        elif text_align == "right":
            x = width - 0.2 * inch
            c.drawRightString(x, y, line)
        else:
            x = width / 2
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

    # Only implement 'simple' for now
    if template == "simple":
        make_pdf_simple(
            path=filepath,
            page_size=page_size,
            content=str(data.get("content", "")),
            align=str(data.get("align", "center")),
            text_align=str(data.get("textAlign", "center")),
            font_size=str(data.get("fontSize", "12pt"))
        )
    else:
        # stub other templates now to keep it minimal
        make_pdf_simple(
            path=filepath,
            page_size=page_size,
            content=f"[{template}] template not implemented yet\n" + str(data),
            align="center",
            text_align="center",
            font_size="12pt"
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
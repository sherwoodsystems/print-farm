# app.py
import os
import shutil
import subprocess
import base64
import sys
import tempfile
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from reportlab.lib.pagesizes import inch
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics

# Windows printing support
try:
    import win32print
    import win32api
    WINDOWS_PRINTING_AVAILABLE = True
except ImportError:
    WINDOWS_PRINTING_AVAILABLE = False
    print("Warning: Windows printing not available. Install pywin32 to enable printing.")

PORT = int(os.getenv("PORT", "3001"))
OUTPUT_DIR = os.getenv("OUTPUT_DIR", r"C:\labels")  # change if you prefer
DEFAULT_LABEL_SIZE = os.getenv("LABEL_SIZE", "3x1")  # '3x1' | '102x51mm' | '4x6.25'
# Sumatra settings (override via env). These strongly hint the driver to print wide labels correctly.
SUMATRA_PRINT_SETTINGS = os.getenv("SUMATRA_PRINT_SETTINGS", "landscape,fit")
SUMATRA_PRINTER = os.getenv("SUMATRA_PRINTER")  # optional explicit printer name

# Actual label sizes for your printers (all horizontal/landscape orientation)
LABEL_SIZES = {
    "3x1": (3.0 * inch, 1.0 * inch),           # Small green labels
    "102x51mm": (4.02 * inch, 2.01 * inch),    # Medium white labels (102mm x 51mm)
    "4x6.25": (4.0 * inch, 6.25 * inch),       # Standard shipping labels (159mm x 102mm)
}

# Map label sizes to descriptive names
LABEL_SIZE_NAMES = {
    "3x1": "Small Green (3\" x 1\")",
    "102x51mm": "Medium White (102mm x 51mm)", 
    "4x6.25": "Large Shipping (4\" x 6.25\")"
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
    # Ensure landscape orientation regardless of how sizes are defined
    ph_w, ph_h = page_size_portrait
    if ph_w < ph_h:
        width, height = ph_h, ph_w
    else:
        width, height = ph_w, ph_h

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

def get_default_printer():
    """Get the default Windows printer name."""
    if not WINDOWS_PRINTING_AVAILABLE:
        return None
    try:
        return win32print.GetDefaultPrinter()
    except Exception as e:
        print(f"Error getting default printer: {e}")
        return None

def print_pdf_to_default_printer(pdf_path, printer_name=None):
    """Print a PDF file to the default Windows printer."""
    if not WINDOWS_PRINTING_AVAILABLE:
        return False, "Windows printing not available. Install pywin32."
    
    try:
        if printer_name is None:
            printer_name = get_default_printer()
        
        if not printer_name:
            return False, "No default printer found"
        
        # Use Windows ShellExecute to print the PDF
        # This requires a PDF viewer to be installed (like Adobe Reader or browser)
        result = win32api.ShellExecute(
            0,  # handle to parent window
            "print",  # operation to perform
            pdf_path,  # file to print
            None,  # parameters
            ".",  # default directory
            0  # show command (0 = hide)
        )
        
        if result > 32:  # ShellExecute returns > 32 on success
            return True, f"Sent to printer: {printer_name}"
        else:
            return False, f"Failed to print (error code: {result})"
            
    except Exception as e:
        return False, f"Print error: {str(e)}"

def find_sumatra_exe():
    """Find SumatraPDF executable via env or common install paths."""
    candidates = []
    # Environment variable can directly specify the path
    env_path = os.getenv("SUMATRA_PATH")
    if env_path:
        candidates.append(env_path)
    # Common install locations
    candidates.extend([
        r"C:\\Program Files\\SumatraPDF\\SumatraPDF.exe",
        r"C:\\Program Files (x86)\\SumatraPDF\\SumatraPDF.exe",
    ])
    # Local repo bin path (optional)
    repo_bin = os.path.join(os.path.dirname(__file__), "bin", "SumatraPDF.exe")
    candidates.append(repo_bin)

    for path in candidates:
        if path and os.path.isfile(path):
            return path
    # Also try PATH lookup
    path_lookup = shutil.which("SumatraPDF.exe")
    if path_lookup:
        return path_lookup
    return None

def print_pdf_with_sumatra(pdf_path, copies=1, printer_name=None):
    """Print a PDF using SumatraPDF command-line if available."""
    exe = find_sumatra_exe()
    if not exe:
        return False, "SumatraPDF not found"

    # Use explicit printer from env if provided
    if SUMATRA_PRINTER:
        printer_name = SUMATRA_PRINTER

    # Build command. Prefer explicit printer if provided; otherwise default.
    args = [exe]
    if printer_name:
        args += ["-print-to", printer_name]
    else:
        args += ["-print-to-default"]

    # Copies (Sumatra supports copies via -print-settings "copies=N")
    copies = max(int(copies or 1), 1)
    # Merge copies with default/override settings
    settings = f"copies={copies}"
    if SUMATRA_PRINT_SETTINGS:
        settings = settings + "," + SUMATRA_PRINT_SETTINGS
    args += ["-silent", "-exit-on-print", "-print-settings", settings, pdf_path]

    try:
        completed = subprocess.run(args, capture_output=True, text=True, timeout=30)
        if completed.returncode == 0:
            return True, (f"Sent to printer via SumatraPDF ({'default' if not printer_name else printer_name}), "
                          f"copies={copies}")
        else:
            return False, f"Sumatra print failed (code {completed.returncode}): {completed.stderr or completed.stdout}"
    except Exception as e:
        return False, f"Sumatra print error: {str(e)}"

def validate_label_size_for_printer(label_size):
    """Check if the label size is valid for printing."""
    # All defined label sizes are allowed for printing
    return label_size in LABEL_SIZES

@app.get("/")
def root():
    printer = get_default_printer() if WINDOWS_PRINTING_AVAILABLE else None
    return jsonify({
        "status": "running",
        "outputDir": OUTPUT_DIR,
        "defaultLabelSize": DEFAULT_LABEL_SIZE,
        "printingAvailable": WINDOWS_PRINTING_AVAILABLE,
        "defaultPrinter": printer,
        "supportedSizes": list(LABEL_SIZES.keys()),
        "sizeDescriptions": LABEL_SIZE_NAMES,
        "endpoints": {
            "POST /generate": "Generate a PDF label (with optional printing)",
            "GET /files/<name>": "Download a generated PDF",
            "GET /printer": "Get default printer info"
        }
    })

@app.get("/files/<path:filename>")
def get_file(filename: str):
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=False)

@app.get("/printer")
def get_printer_info():
    """Get information about the default printer."""
    printer = get_default_printer() if WINDOWS_PRINTING_AVAILABLE else None
    return jsonify({
        "printingAvailable": WINDOWS_PRINTING_AVAILABLE,
        "defaultPrinter": printer,
        "supportedSizes": list(LABEL_SIZES.keys()),
        "sizeDescriptions": LABEL_SIZE_NAMES,
        "sumatra": {
            "found": bool(find_sumatra_exe()),
            "settings": SUMATRA_PRINT_SETTINGS,
            "printerOverride": SUMATRA_PRINTER or None
        }
    })

@app.post("/generate")
def generate():
    payload = request.get_json(silent=True) or {}
    template = payload.get("template", "simple")
    data = payload.get("data", {}) or {}
    label_size = payload.get("labelSize", DEFAULT_LABEL_SIZE)
    copies = int(payload.get("copies", 1))
    should_print = payload.get("print", False)  # New parameter to trigger printing

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

    # Handle printing if requested
    print_result = None
    if should_print:
        if not validate_label_size_for_printer(label_size):
            print_result = {
                "success": False,
                "method": "validation",
                "message": f"Invalid label size for printing: {label_size}"
            }
        else:
            # Prefer SumatraPDF if available (does not require Adobe)
            printer_name = get_default_printer() if WINDOWS_PRINTING_AVAILABLE else None
            success, message = print_pdf_with_sumatra(filepath, copies=copies, printer_name=printer_name)
            method_used = "sumatra" if success or "not found" not in message.lower() else "shell"

            if not success and method_used == "shell":
                # Fallback to Windows ShellExecute (requires association)
                first_failure = None
                for i in range(copies):
                    ok, msg = print_pdf_to_default_printer(filepath)
                    if not ok and first_failure is None:
                        first_failure = msg
                        break
                if first_failure:
                    print_result = {"success": False, "method": method_used, "message": first_failure}
                else:
                    print_result = {
                        "success": True,
                        "method": method_used,
                        "message": f"Printed {copies} copies to default printer",
                        "printer": printer_name
                    }
            else:
                print_result = {
                    "success": success,
                    "method": method_used,
                    "message": message,
                    "printer": printer_name,
                }

    # Return metadata and a URL to view the file
    response = {
        "ok": True,
        "template": template,
        "labelSize": label_size,
        "file": filename,
        "path": filepath,
        "url": f"http://{request.host}/files/{filename}",
        "copies": copies
    }
    
    if print_result is not None:
        response["print"] = print_result
    
    return jsonify(response), 200

@app.post("/test-print")
def test_print():
    """Generate a simple test label and print it using current settings."""
    payload = request.get_json(silent=True) or {}
    label_size = payload.get("labelSize", DEFAULT_LABEL_SIZE)
    copies = int(payload.get("copies", 1))

    if label_size not in LABEL_SIZES:
        return jsonify({"error": f"Invalid labelSize. Use one of {list(LABEL_SIZES.keys())}"}), 400

    page_size = LABEL_SIZES[label_size]
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    filename = f"test_{label_size}_{datetime.utcnow().strftime('%Y%m%d-%H%M%S-%f')}.pdf"
    filepath = os.path.join(OUTPUT_DIR, filename)

    make_pdf_big_bold_landscape(
        path=filepath,
        page_size_portrait=page_size,
        content=f"TEST {label_size} {ts}"
    )

    printer_name = get_default_printer() if WINDOWS_PRINTING_AVAILABLE else None
    success, message = print_pdf_with_sumatra(filepath, copies=copies, printer_name=printer_name)

    return jsonify({
        "ok": success,
        "message": message,
        "file": filename,
        "path": filepath,
        "url": f"http://{request.host}/files/{filename}",
        "print": {
            "success": success,
            "method": "sumatra" if success else "sumatra?",
            "message": message,
            "printer": printer_name,
            "settings": SUMATRA_PRINT_SETTINGS
        }
    }), (200 if success else 500)

if __name__ == "__main__":
    # Bind to all interfaces so Tailscale/LAN can reach it
    app.run(host="0.0.0.0", port=PORT)
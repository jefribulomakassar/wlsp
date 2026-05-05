# index.py
import os
import csv
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# ── Google Sheets config ──────────────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "")          # ganti di .env
SERVICE_ACCOUNT_FILE = os.environ.get("SERVICE_ACCOUNT_FILE", "service_account.json")
SHEET_NAME = os.environ.get("SHEET_NAME", "Registrasi")

HEADER = [
    "Timestamp",
    "Nama Lengkap Kaprodi",
    "Nomor HP Kaprodi",
    "Program Studi",
    "Dosen Diusulkan",          # JSON string: [{nama, hp}, ...]
    "Judul Skema",              # JSON string: [skema1, skema2, ...]
]

FALLBACK_CSV = "data_registrasi.csv"


def get_sheet():
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    gc = gspread.authorize(creds)
    return gc.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)


def ensure_header(sheet):
    """Tambahkan header jika sheet masih kosong."""
    if sheet.row_count == 0 or sheet.cell(1, 1).value != "Timestamp":
        sheet.insert_row(HEADER, 1)


def save_to_sheets(row: list) -> bool:
    try:
        sheet = get_sheet()
        ensure_header(sheet)
        sheet.append_row(row, value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        logging.error(f"[Google Sheets] Gagal menyimpan: {e}")
        return False


def save_to_csv(row: list):
    file_exists = os.path.isfile(FALLBACK_CSV)
    with open(FALLBACK_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(HEADER)
        writer.writerow(row)
    logging.info(f"[CSV Fallback] Data disimpan ke {FALLBACK_CSV}")


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/submit", methods=["POST"])
def submit():
    try:
        data = request.get_json(force=True)

        # ── Validasi dasar ────────────────────────────────────────────────────
        errors = []
        nama_kaprodi = (data.get("nama_kaprodi") or "").strip()
        no_hp        = (data.get("no_hp") or "").strip()
        prodi        = (data.get("prodi") or "").strip()
        dosen_list   = data.get("dosen", [])
        skema_list   = data.get("skema", [])

        if not nama_kaprodi:
            errors.append("Nama Lengkap Kaprodi wajib diisi.")
        if not no_hp:
            errors.append("Nomor HP wajib diisi.")
        if not prodi:
            errors.append("Program Studi wajib diisi.")

        # Filter dosen: hanya yang nama-nya terisi
        dosen_valid = [
            d for d in dosen_list
            if isinstance(d, dict) and (d.get("nama") or "").strip()
        ]
        if len(dosen_valid) < 2:
            errors.append("Minimal 2 dosen yang diusulkan harus diisi.")

        # Filter skema: hanya yang judulnya terisi
        skema_valid = [s.strip() for s in skema_list if (s or "").strip()]
        if len(skema_valid) < 2:
            errors.append("Minimal 2 judul skema harus diisi.")

        if errors:
            return jsonify({"success": False, "errors": errors}), 422

        # ── Susun baris ───────────────────────────────────────────────────────
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dosen_str = json.dumps(dosen_valid, ensure_ascii=False)
        skema_str = json.dumps(skema_valid, ensure_ascii=False)
        row = [timestamp, nama_kaprodi, no_hp, prodi, dosen_str, skema_str]

        # ── Simpan ────────────────────────────────────────────────────────────
        saved_to_sheets = save_to_sheets(row)
        if not saved_to_sheets:
            save_to_csv(row)          # fallback CSV jika Sheets gagal

        return jsonify({
            "success": True,
            "message": "Pendaftaran berhasil disimpan!",
            "saved_to": "google_sheets" if saved_to_sheets else "csv_fallback",
        })

    except Exception as e:
        logging.exception("Unhandled error di /submit")
        return jsonify({"success": False, "errors": [str(e)]}), 500


if __name__ == "__main__":
    app.run(debug=True)

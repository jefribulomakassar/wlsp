import os
import csv
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# ── Google Sheets config ──────────────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SPREADSHEET_ID_1     = os.environ.get("SPREADSHEET_ID", "")
SPREADSHEET_ID_2     = os.environ.get("SPREADSHEET_ID_2", "")
SERVICE_ACCOUNT_JSON = os.environ.get("SERVICE_ACCOUNT_JSON", "")
SHEET_NAME           = os.environ.get("SHEET_NAME", "Registrasi")

HEADER = [
    "Timestamp",
    "Nama Lengkap Kaprodi",
    "Nomor HP Kaprodi",
    "Program Studi",
    "Dosen Diusulkan",
    "Judul Skema",
]

FALLBACK_CSV = "/tmp/data_registrasi.csv"


def get_credentials():
    if SERVICE_ACCOUNT_JSON:
        info = json.loads(SERVICE_ACCOUNT_JSON)
        return Credentials.from_service_account_info(info, scopes=SCOPES)
    return Credentials.from_service_account_file("service_account.json", scopes=SCOPES)


def get_sheet(spreadsheet_id: str):
    creds = get_credentials()
    gc = gspread.authorize(creds)
    return gc.open_by_key(spreadsheet_id).worksheet(SHEET_NAME)


def ensure_header(sheet):
    if sheet.row_count == 0 or sheet.cell(1, 1).value != "Timestamp":
        sheet.insert_row(HEADER, 1)


def format_dosen(dosen_list: list) -> str:
    parts = []
    for d in dosen_list:
        nama = (d.get("nama") or "").strip()
        hp   = (d.get("hp") or "").strip()
        if nama and hp:
            parts.append(f"{nama} ({hp})")
        elif nama:
            parts.append(nama)
    return " | ".join(parts)


def format_skema(skema_list: list) -> str:
    return " | ".join(s.strip() for s in skema_list if s.strip())


def save_to_one_sheet(spreadsheet_id: str, row: list) -> bool:
    if not spreadsheet_id:
        logging.warning("[Google Sheets] SPREADSHEET_ID kosong, dilewati.")
        return False
    try:
        sheet = get_sheet(spreadsheet_id)
        ensure_header(sheet)
        sheet.append_row(row, value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        logging.error(f"[Google Sheets] Gagal ke {spreadsheet_id[:12]}...: {e}")
        return False


def save_to_sheets(row: list) -> bool:
    ok1 = save_to_one_sheet(SPREADSHEET_ID_1, row)
    ok2 = save_to_one_sheet(SPREADSHEET_ID_2, row)
    if ok1 and ok2:
        logging.info("[Google Sheets] Berhasil disimpan ke kedua sheet.")
    elif ok1:
        logging.warning("[Google Sheets] Hanya berhasil ke sheet 1.")
    elif ok2:
        logging.warning("[Google Sheets] Hanya berhasil ke sheet 2.")
    else:
        logging.error("[Google Sheets] Gagal ke semua sheet.")
    return ok1 or ok2


def save_to_csv(row: list):
    file_exists = os.path.isfile(FALLBACK_CSV)
    with open(FALLBACK_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(HEADER)
        writer.writerow(row)
    logging.info(f"[CSV Fallback] Disimpan ke {FALLBACK_CSV}")


# ── HTML ──────────────────────────────────────────────────────────────────────
HTML = """<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Registrasi Workshop Penyusunan Skema Kompetensi</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=DM+Sans:wght@400;500;600&display=swap" rel="stylesheet" />
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    :root {
      --navy:   #0d2137;
      --gold:   #c9972c;
      --gold-lt:#f0c96a;
      --cream:  #faf7f2;
      --white:  #ffffff;
      --gray:   #6b7280;
      --gray-lt:#e5e7eb;
      --danger: #dc2626;
      --success:#16a34a;
      --radius: 10px;
      --shadow: 0 4px 24px rgba(13,33,55,.10);
    }
    body {
      font-family: 'DM Sans', sans-serif;
      background: var(--cream);
      color: var(--navy);
      min-height: 100vh;
      padding: 0 0 60px;
    }

    /* ── Closed Notice Bar ─────────────────────────────────────────────── */
    .closed-notice {
      background: #7f1d1d;
      color: #fff;
      text-align: center;
      padding: 14px 24px;
      font-size: 14px;
      font-weight: 600;
      letter-spacing: .01em;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
    }
    .closed-notice-wrap {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 3px;
    }
    .closed-notice .closed-sub {
      font-weight: 400;
      opacity: .85;
      font-size: 12.5px;
    }

    /* ── Banner ────────────────────────────────────────────────────────── */
    .banner {
      background: var(--navy);
      color: var(--white);
      padding: 36px 24px 32px;
      text-align: center;
      position: relative;
      overflow: hidden;
    }
    .banner::before {
      content: '';
      position: absolute; inset: 0;
      background: repeating-linear-gradient(
        45deg, transparent, transparent 18px,
        rgba(201,151,44,.08) 18px, rgba(201,151,44,.08) 36px
      );
    }
    .banner-inner { position: relative; z-index: 1; max-width: 680px; margin: auto; }
    .banner h1 {
      font-family: 'Playfair Display', serif;
      font-size: clamp(20px, 4vw, 28px);
      line-height: 1.25;
      margin-bottom: 10px;
    }
    .banner h1 span { color: var(--gold-lt); }
    .banner p { font-size: 13px; opacity: .75; line-height: 1.6; max-width: 560px; margin: 0 auto; }

    /* ── Card ──────────────────────────────────────────────────────────── */
    .card {
      background: var(--white);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      max-width: 680px;
      margin: -20px auto 0;
      padding: 36px 32px 40px;
      position: relative; z-index: 2;
    }
    @media (max-width: 600px) {
      .card { margin: -16px 12px 0; padding: 24px 18px 32px; }
    }

    /* ── Closed Card Banner ────────────────────────────────────────────── */
    .closed-card-banner {
      background: #fef2f2;
      border: 1.5px solid #fecaca;
      border-radius: var(--radius);
      padding: 16px 20px;
      display: flex;
      align-items: flex-start;
      gap: 14px;
      margin-bottom: 28px;
    }
    .closed-card-icon {
      width: 38px; height: 38px;
      background: #fee2e2;
      border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
      font-size: 18px;
      flex-shrink: 0;
      margin-top: 1px;
    }
    .closed-card-text h3 {
      font-size: 14px; font-weight: 700;
      color: #991b1b;
      margin-bottom: 4px;
    }
    .closed-card-text p {
      font-size: 12.5px;
      color: #b91c1c;
      line-height: 1.55;
    }

    /* ── Section Label ─────────────────────────────────────────────────── */
    .section-label {
      font-size: 11px; font-weight: 600; letter-spacing: .08em;
      text-transform: uppercase; color: var(--gold);
      margin: 28px 0 14px;
      display: flex; align-items: center; gap: 8px;
    }
    .section-label::after { content: ''; flex: 1; height: 1px; background: var(--gray-lt); }

    /* ── Field ─────────────────────────────────────────────────────────── */
    .field { margin-bottom: 18px; }
    .field label { display: block; font-size: 13px; font-weight: 600; margin-bottom: 6px; color: var(--navy); }
    .field label .req { color: var(--danger); margin-left: 2px; }
    .field input[type="text"],
    .field input[type="tel"],
    .field select {
      width: 100%; padding: 10px 14px;
      border: 1.5px solid var(--gray-lt);
      border-radius: var(--radius);
      font-family: inherit; font-size: 14px;
      color: var(--navy);
      outline: none; background: var(--white);
      appearance: none; -webkit-appearance: none;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%236b7280' stroke-width='2.5'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
      background-repeat: no-repeat; background-position: right 12px center;
      padding-right: 36px;
      cursor: not-allowed;
      opacity: .55;
    }
    .field select option { color: var(--navy); }
    .field select option[value=""] { color: var(--gray); }

    /* ── Dynamic rows ──────────────────────────────────────────────────── */
    .dynamic-list { display: flex; flex-direction: column; gap: 10px; }

    .dosen-row {
      display: grid; grid-template-columns: 1fr 1fr auto;
      gap: 8px; align-items: center;
      background: #f8fafc; border: 1.5px solid var(--gray-lt);
      border-radius: var(--radius); padding: 10px 12px;
    }
    .dosen-row input {
      padding: 8px 10px; border: 1.5px solid var(--gray-lt);
      border-radius: 6px; font-family: inherit; font-size: 13px;
      outline: none; background: var(--white);
      opacity: .55; cursor: not-allowed;
    }
    .dosen-row input::placeholder { color: #9ca3af; font-size: 12px; }

    .skema-row { display: grid; grid-template-columns: 1fr auto; gap: 8px; align-items: center; }
    .skema-row input {
      padding: 10px 14px; border: 1.5px solid var(--gray-lt);
      border-radius: var(--radius); font-family: inherit; font-size: 14px;
      outline: none; width: 100%;
      opacity: .55; cursor: not-allowed;
    }

    /* ── Buttons ───────────────────────────────────────────────────────── */
    .btn-remove {
      width: 30px; height: 30px; border-radius: 50%;
      border: 1.5px solid #fecaca; background: #fff5f5; color: var(--danger);
      font-size: 16px; cursor: not-allowed;
      display: flex; align-items: center; justify-content: center;
      flex-shrink: 0; opacity: .4;
    }
    .btn-add {
      margin-top: 8px; border: 1.5px dashed var(--gray-lt);
      background: transparent; color: var(--gray);
      padding: 8px 16px; border-radius: var(--radius);
      font-family: inherit; font-size: 13px; font-weight: 600;
      cursor: not-allowed;
      display: inline-flex; align-items: center; gap: 6px;
      opacity: .5;
    }
    .btn-ref {
      display: inline-flex; align-items: center; gap: 6px;
      margin-top: 6px; font-size: 12px; font-weight: 600; color: var(--gold);
      background: rgba(201,151,44,.09); border: 1px solid rgba(201,151,44,.3);
      border-radius: 20px; padding: 5px 12px;
      text-decoration: none; cursor: pointer; transition: background .15s;
    }
    .btn-ref:hover { background: rgba(201,151,44,.18); }
    .btn-ref svg { width: 13px; height: 13px; }

    .btn-submit {
      margin-top: 30px; width: 100%;
      background: #9ca3af; color: var(--white);
      border: none; border-radius: var(--radius);
      padding: 14px; font-family: inherit;
      font-size: 15px; font-weight: 600; cursor: not-allowed;
      display: flex; align-items: center; justify-content: center; gap: 8px;
      opacity: .65;
    }

    /* ── WA Banner ─────────────────────────────────────────────────────── */
    .wa-banner {
      display: flex; align-items: center; gap: 14px;
      background: #f0fdf4; border: 1.5px solid #86efac;
      border-radius: var(--radius); padding: 14px 16px;
      text-decoration: none; color: #15803d; margin-bottom: 24px;
      transition: background .2s, border-color .2s, transform .1s;
    }
    .wa-banner:hover { background: #dcfce7; border-color: #4ade80; transform: translateY(-1px); }
    .wa-banner:active { transform: translateY(0); }
    .wa-icon { width: 36px; height: 36px; flex-shrink: 0; color: #16a34a; }
    .wa-text { flex: 1; display: flex; flex-direction: column; gap: 2px; }
    .wa-label { font-size: 10px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: #16a34a; opacity: .7; }
    .wa-desc { font-size: 13px; font-weight: 500; color: #15803d; line-height: 1.4; }
    .wa-desc strong { font-weight: 700; }
    .wa-arrow { width: 18px; height: 18px; flex-shrink: 0; opacity: .5; }

    .hint { font-size: 11.5px; color: var(--gray); margin-top: 4px; }
  </style>
</head>
<body>

<!-- ── Closed Notice Bar ───────────────────────────────────────────────────── -->
<div class="closed-notice" role="alert">
  <span style="font-size:16px;">🔒</span>
  <div class="closed-notice-wrap">
    <span>Pendaftaran Telah Ditutup</span>
    <span class="closed-sub">Formulir registrasi tidak lagi menerima pendaftaran baru.</span>
  </div>
</div>

<!-- ── Banner ──────────────────────────────────────────────────────────────── -->
<div class="banner">
  <div class="banner-inner">
    <h1>Workshop Penyusunan<br/><span>Skema Kompetensi</span></h1>
    <p>Isi formulir ini secara lengkap dan akurat untuk mendukung pengembangan skema sertifikasi.</p>
  </div>
</div>

<!-- ── Card ────────────────────────────────────────────────────────────────── -->
<div class="card">

  <!-- Closed card banner -->
  <div class="closed-card-banner" role="alert">
    <div class="closed-card-icon">&#9940;</div>
    <div class="closed-card-text">
      <h3>Periode Pendaftaran Sudah Berakhir</h3>
      <p>Formulir registrasi Workshop Penyusunan Skema Kompetensi telah ditutup. Seluruh kolom isian dan tombol pengiriman tidak dapat digunakan. Hubungi panitia untuk informasi lebih lanjut.</p>
    </div>
  </div>

  <div id="formWrapper">

    <!-- WA Banner -->
    <a class="wa-banner" href="https://chat.whatsapp.com/HlANj8ZwqdbILXgD3clXOT" target="_blank" rel="noopener">
      <svg class="wa-icon" viewBox="0 0 24 24" fill="currentColor">
        <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/>
        <path d="M12 0C5.373 0 0 5.373 0 12c0 2.136.564 4.14 1.543 5.876L.057 23.5l5.773-1.515A11.945 11.945 0 0012 24c6.627 0 12-5.373 12-12S18.627 0 12 0zm0 21.894a9.887 9.887 0 01-5.034-1.378l-.361-.214-3.427.899.915-3.342-.235-.374A9.861 9.861 0 012.106 12C2.106 6.58 6.58 2.106 12 2.106S21.894 6.58 21.894 12 17.42 21.894 12 21.894z"/>
      </svg>
      <div class="wa-text">
        <span class="wa-label">Grup WhatsApp</span>
        <span class="wa-desc">Klik untuk bergabung dengan Grup <strong>Skema Kompetensi</strong></span>
      </div>
      <svg class="wa-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"/></svg>
    </a>

    <!-- ── A. Data Kaprodi ─────────────────────────────────────────────── -->
    <div class="section-label">Data Kaprodi</div>

    <div class="field">
      <label>Nama Lengkap Kaprodi <span class="req">*</span></label>
      <input type="text" placeholder="cth. Dr. Andi Baso, S.T., M.T." disabled />
    </div>
    <div class="field">
      <label>Nomor HP (WhatsApp) <span class="req">*</span></label>
      <input type="tel" placeholder="cth. 08123456789" disabled />
    </div>
    <div class="field">
      <label>Program Studi <span class="req">*</span></label>
      <select disabled>
        <option value="">-- Pilih Program Studi --</option>
        <optgroup label="Fakultas Pertanian">
          <option>Budidaya Perairan</option>
          <option>Teknologi Pangan</option>
          <option>Peternakan</option>
          <option>Agribisnis</option>
          <option>Agroteknologi</option>
        </optgroup>
        <optgroup label="Fakultas Teknik">
          <option>Teknologi Informasi</option>
          <option>Teknik Geologi</option>
          <option>Perencanaan Wilayah dan Kota</option>
          <option>Teknik Arsitektur</option>
          <option>Teknik Lingkungan</option>
          <option>Teknik Sipil</option>
          <option>Teknik Kimia</option>
        </optgroup>
        <optgroup label="Fakultas Teknik Pertambangan">
          <option>Teknik Pertambangan</option>
        </optgroup>
        <optgroup label="Fakultas Ilmu Sosial &amp; Politik">
          <option>Sosiologi</option>
          <option>Administrasi Publik</option>
          <option>Ilmu Hubungan Internasional</option>
        </optgroup>
        <optgroup label="Fakultas Ekonomi &amp; Bisnis">
          <option>Ilmu Ekonomi Pembangunan</option>
          <option>Akuntansi</option>
          <option>Manajemen</option>
        </optgroup>
        <optgroup label="Fakultas Sastra &amp; Pendidikan">
          <option>Bahasa Mandarin</option>
          <option>Pendidikan Bahasa Indonesia</option>
        </optgroup>
        <optgroup label="Vokasi">
          <option>Teknik Mekatronika</option>
          <option>Teknik Listrik</option>
          <option>Perawatan dan Perbaikan Mesin</option>
          <option>Perhotelan</option>
          <option>Perpajakan</option>
        </optgroup>
      </select>
    </div>

    <!-- ── B. Dosen ─────────────────────────────────────────────────────── -->
    <div class="section-label">Dosen yang Diusulkan <span style="font-weight:400;text-transform:none;letter-spacing:0;color:var(--gray);font-size:11px;">(minimal 2 dosen)</span></div>
    <div class="dynamic-list" id="dosenList"></div>
    <button class="btn-add" type="button" disabled>+ Tambah Dosen</button>

    <!-- ── C. Skema ─────────────────────────────────────────────────────── -->
    <div class="section-label">Judul Skema Kompetensi <span style="font-weight:400;text-transform:none;letter-spacing:0;color:var(--gray);font-size:11px;">(minimal 2 skema)</span></div>
    <p class="hint" style="margin-bottom:10px;">Sesuaikan judul skema dengan program studi dan kompetensi teknis dosen. Gunakan referensi SKKNI resmi:</p>
    <a class="btn-ref" href="https://skkni.kemnaker.go.id/" target="_blank" rel="noopener">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
      Buka SKKNI Kemnaker (tab baru)
    </a>
    <div class="dynamic-list" id="skemaList" style="margin-top:14px;"></div>
    <button class="btn-add" type="button" disabled>+ Tambah Skema</button>

    <!-- Submit -->
    <button class="btn-submit" type="button" disabled>
      &#128274;&nbsp; Pendaftaran Telah Ditutup
    </button>

  </div>
</div>

<script>
  function init() {
    const dosenList = document.getElementById('dosenList');
    const skemaList = document.getElementById('skemaList');
    for (let i = 1; i <= 2; i++) {
      const dr = document.createElement('div');
      dr.className = 'dosen-row';
      dr.innerHTML = `
        <input type="text" placeholder="Nama Dosen ${i}" disabled />
        <input type="tel"  placeholder="No. HP / WA" disabled />
        <button class="btn-remove" type="button" disabled>&#215;</button>`;
      dosenList.appendChild(dr);

      const sr = document.createElement('div');
      sr.className = 'skema-row';
      sr.innerHTML = `
        <input type="text" placeholder="cth. SKKNI Nomor ... Bidang Teknologi Informasi" disabled />
        <button class="btn-remove" type="button" disabled>&#215;</button>`;
      skemaList.appendChild(sr);
    }
  }
  init();
</script>
</body>
</html>"""


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def index():
    return HTML, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/submit", methods=["POST"])
def submit():
    try:
        data = request.get_json(force=True)

        nama_kaprodi = (data.get("nama_kaprodi") or "").strip()
        no_hp        = (data.get("no_hp") or "").strip()
        prodi        = (data.get("prodi") or "").strip()
        dosen_list   = data.get("dosen", [])
        skema_list   = data.get("skema", [])

        errors = []
        if not nama_kaprodi: errors.append("Nama Lengkap Kaprodi wajib diisi.")
        if not no_hp:        errors.append("Nomor HP wajib diisi.")
        if not prodi:        errors.append("Program Studi wajib dipilih.")

        dosen_valid = [d for d in dosen_list if isinstance(d, dict) and (d.get("nama") or "").strip()]
        skema_valid = [s.strip() for s in skema_list if (s or "").strip()]

        if len(dosen_valid) < 2: errors.append("Minimal 2 dosen yang diusulkan.")
        if len(skema_valid) < 2: errors.append("Minimal 2 judul skema.")

        if errors:
            return jsonify({"success": False, "errors": errors}), 422

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [
            timestamp,
            nama_kaprodi,
            no_hp,
            prodi,
            format_dosen(dosen_valid),
            format_skema(skema_valid),
        ]

        saved = save_to_sheets(row)
        if not saved:
            save_to_csv(row)

        return jsonify({
            "success": True,
            "message": "Pendaftaran berhasil!",
            "saved_to": "google_sheets" if saved else "csv_fallback",
        })

    except Exception as e:
        logging.exception("Error di /submit")
        return jsonify({"success": False, "errors": [str(e)]}), 500


if __name__ == "__main__":
    app.run(debug=True)

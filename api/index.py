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
SPREADSHEET_ID      = os.environ.get("SPREADSHEET_ID", "")
SERVICE_ACCOUNT_JSON = os.environ.get("SERVICE_ACCOUNT_JSON", "")  # JSON string di env var
SHEET_NAME          = os.environ.get("SHEET_NAME", "Registrasi")

HEADER = [
    "Timestamp",
    "Nama Lengkap Kaprodi",
    "Nomor HP Kaprodi",
    "Program Studi",
    "Dosen Diusulkan",   # JSON string
    "Judul Skema",       # JSON string
]

FALLBACK_CSV = "/tmp/data_registrasi.csv"   # /tmp adalah satu-satunya writable di Vercel


def get_sheet():
    if SERVICE_ACCOUNT_JSON:
        # Di Vercel: credentials dari environment variable (JSON string)
        info = json.loads(SERVICE_ACCOUNT_JSON)
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    else:
        # Lokal: dari file service_account.json
        creds = Credentials.from_service_account_file("service_account.json", scopes=SCOPES)
    gc = gspread.authorize(creds)
    return gc.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)


def ensure_header(sheet):
    if sheet.row_count == 0 or sheet.cell(1, 1).value != "Timestamp":
        sheet.insert_row(HEADER, 1)


def save_to_sheets(row: list) -> bool:
    try:
        sheet = get_sheet()
        ensure_header(sheet)
        sheet.append_row(row, value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        logging.error(f"[Google Sheets] Gagal: {e}")
        return False


def save_to_csv(row: list):
    file_exists = os.path.isfile(FALLBACK_CSV)
    with open(FALLBACK_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(HEADER)
        writer.writerow(row)
    logging.info(f"[CSV Fallback] Disimpan ke {FALLBACK_CSV}")


# ── HTML (inline karena Vercel Python tidak serve static folder) ──────────────
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

    .section-label {
      font-size: 11px; font-weight: 600; letter-spacing: .08em;
      text-transform: uppercase; color: var(--gold);
      margin: 28px 0 14px;
      display: flex; align-items: center; gap: 8px;
    }
    .section-label::after { content: ''; flex: 1; height: 1px; background: var(--gray-lt); }

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
      transition: border-color .2s, box-shadow .2s;
      outline: none; background: var(--white);
    }
    .field select {
      appearance: none; -webkit-appearance: none;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%236b7280' stroke-width='2.5'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
      background-repeat: no-repeat; background-position: right 12px center;
      padding-right: 36px; cursor: pointer;
    }
    .field input:focus, .field select:focus {
      border-color: var(--gold);
      box-shadow: 0 0 0 3px rgba(201,151,44,.14);
    }
    .field input.error, .field select.error { border-color: var(--danger); }

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
      outline: none; background: var(--white); transition: border-color .2s;
    }
    .dosen-row input:focus { border-color: var(--gold); }
    .dosen-row input::placeholder { color: #9ca3af; font-size: 12px; }

    .skema-row { display: grid; grid-template-columns: 1fr auto; gap: 8px; align-items: center; }
    .skema-row input {
      padding: 10px 14px; border: 1.5px solid var(--gray-lt);
      border-radius: var(--radius); font-family: inherit; font-size: 14px;
      outline: none; width: 100%; transition: border-color .2s;
    }
    .skema-row input:focus { border-color: var(--gold); }

    .btn-remove {
      width: 30px; height: 30px; border-radius: 50%;
      border: 1.5px solid #fecaca; background: #fff5f5; color: var(--danger);
      font-size: 16px; cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      flex-shrink: 0; transition: background .15s;
    }
    .btn-remove:hover { background: #fee2e2; }
    .btn-remove:disabled { opacity: .3; cursor: not-allowed; }

    .btn-add {
      margin-top: 8px; border: 1.5px dashed var(--gold);
      background: transparent; color: var(--gold);
      padding: 8px 16px; border-radius: var(--radius);
      font-family: inherit; font-size: 13px; font-weight: 600;
      cursor: pointer; transition: background .15s;
      display: inline-flex; align-items: center; gap: 6px;
    }
    .btn-add:hover { background: rgba(201,151,44,.07); }

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
      background: var(--navy); color: var(--white);
      border: none; border-radius: var(--radius);
      padding: 14px; font-family: inherit;
      font-size: 15px; font-weight: 600; cursor: pointer;
      display: flex; align-items: center; justify-content: center; gap: 8px;
      transition: background .2s, transform .1s;
    }
    .btn-submit:hover { background: #162f4f; }
    .btn-submit:active { transform: scale(.98); }
    .btn-submit:disabled { opacity: .6; cursor: not-allowed; }

    .alert {
      border-radius: var(--radius); padding: 14px 16px;
      font-size: 13px; line-height: 1.5;
      margin-top: 16px; display: none;
    }
    .alert.show { display: block; }
    .alert.danger { background: #fef2f2; border: 1px solid #fecaca; color: var(--danger); }
    .alert.success { background: #f0fdf4; border: 1px solid #bbf7d0; color: var(--success); }
    .alert ul { padding-left: 18px; margin-top: 4px; }

    .hint { font-size: 11.5px; color: var(--gray); margin-top: 4px; }

    .spinner {
      width: 18px; height: 18px;
      border: 2.5px solid rgba(255,255,255,.4);
      border-top-color: #fff; border-radius: 50%;
      animation: spin .7s linear infinite; display: none;
    }
    .btn-submit.loading .spinner { display: block; }
    .btn-submit.loading .btn-text { opacity: .7; }
    @keyframes spin { to { transform: rotate(360deg); } }

    .success-screen { display: none; text-align: center; padding: 20px 0; }
    .success-screen.show { display: block; }
    .success-icon {
      width: 64px; height: 64px; border-radius: 50%;
      background: #dcfce7; color: var(--success);
      display: flex; align-items: center; justify-content: center;
      margin: 0 auto 20px; font-size: 28px;
    }
    .success-screen h2 { font-family: 'Playfair Display', serif; font-size: 22px; margin-bottom: 10px; }
    .success-screen p { font-size: 14px; color: var(--gray); }
  </style>
</head>
<body>
<div class="banner">
  <div class="banner-inner">
    <h1>Workshop Penyusunan<br/><span>Skema Kompetensi</span></h1>
    <p>Isi formulir ini secara lengkap dan akurat untuk mendukung pengembangan skema sertifikasi.</p>
  </div>
</div>

<div class="card">
  <div class="success-screen" id="successScreen">
    <div class="success-icon">&#10003;</div>
    <h2>Pendaftaran Berhasil!</h2>
    <p>Data Anda telah tersimpan. Terima kasih telah mendaftar Workshop Penyusunan Skema Kompetensi.</p>
  </div>

  <div id="formWrapper">
    <div class="section-label">Data Kaprodi</div>

    <div class="field">
      <label>Nama Lengkap Kaprodi <span class="req">*</span></label>
      <input type="text" id="namaKaprodi" placeholder="cth. Dr. Andi Baso, S.T., M.T." />
    </div>

    <div class="field">
      <label>Nomor HP (WhatsApp) <span class="req">*</span></label>
      <input type="tel" id="noHp" placeholder="cth. 08123456789" />
    </div>

    <div class="field">
      <label>Program Studi <span class="req">*</span></label>
      <select id="prodi">
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

    <div class="section-label">Dosen yang Diusulkan <span style="font-weight:400;text-transform:none;letter-spacing:0;color:var(--gray);font-size:11px;">(minimal 2 dosen)</span></div>
    <div class="dynamic-list" id="dosenList"></div>
    <button class="btn-add" type="button" onclick="tambahDosen()">+ Tambah Dosen</button>

    <div class="section-label">Judul Skema Kompetensi <span style="font-weight:400;text-transform:none;letter-spacing:0;color:var(--gray);font-size:11px;">(minimal 2 skema)</span></div>
    <p class="hint" style="margin-bottom:10px;">Sesuaikan judul skema dengan program studi dan kompetensi teknis dosen. Gunakan referensi SKKNI resmi:</p>
    <a class="btn-ref" href="https://skkni.kemnaker.go.id/" target="_blank" rel="noopener">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
      Buka SKKNI Kemnaker (tab baru)
    </a>
    <div class="dynamic-list" id="skemaList" style="margin-top:14px;"></div>
    <button class="btn-add" type="button" onclick="tambahSkema()">+ Tambah Skema</button>

    <div class="alert danger" id="alertError"></div>

    <button class="btn-submit" id="btnSubmit" type="button" onclick="submitForm()">
      <span class="spinner"></span>
      <span class="btn-text">Kirim Pendaftaran</span>
    </button>
  </div>
</div>

<script>
  let dosenCount = 0, skemaCount = 0;

  function init() {
    tambahDosen(); tambahDosen();
    tambahSkema(); tambahSkema();
  }

  function tambahDosen() {
    dosenCount++;
    const id = dosenCount;
    const row = document.createElement('div');
    row.className = 'dosen-row'; row.id = `dosenRow${id}`;
    row.innerHTML = `
      <input type="text" id="dosenNama${id}" placeholder="Nama Dosen ${id}" />
      <input type="tel"  id="dosenHp${id}"   placeholder="No. HP / WA" />
      <button class="btn-remove" type="button" onclick="hapusDosen(${id})" title="Hapus">&#215;</button>`;
    document.getElementById('dosenList').appendChild(row);
    updateRemoveButtons('dosenList', 'dosenRow', 2);
  }

  function hapusDosen(id) {
    const row = document.getElementById(`dosenRow${id}`);
    if (row) row.remove();
    updateRemoveButtons('dosenList', 'dosenRow', 2);
  }

  function tambahSkema() {
    skemaCount++;
    const id = skemaCount;
    const row = document.createElement('div');
    row.className = 'skema-row'; row.id = `skemaRow${id}`;
    row.innerHTML = `
      <input type="text" id="skema${id}" placeholder="cth. SKKNI Nomor ... Bidang Teknologi Informasi" />
      <button class="btn-remove" type="button" onclick="hapusSkema(${id})" title="Hapus">&#215;</button>`;
    document.getElementById('skemaList').appendChild(row);
    updateRemoveButtons('skemaList', 'skemaRow', 2);
  }

  function hapusSkema(id) {
    const row = document.getElementById(`skemaRow${id}`);
    if (row) row.remove();
    updateRemoveButtons('skemaList', 'skemaRow', 2);
  }

  function updateRemoveButtons(listId, rowPrefix, minCount) {
    const rows = document.getElementById(listId).querySelectorAll(`[id^="${rowPrefix}"]`);
    rows.forEach(row => {
      const btn = row.querySelector('.btn-remove');
      if (btn) btn.disabled = rows.length <= minCount;
    });
  }

  function collectDosen() {
    return [...document.getElementById('dosenList').querySelectorAll('.dosen-row')]
      .map(row => {
        const inputs = row.querySelectorAll('input');
        return { nama: (inputs[0]?.value||'').trim(), hp: (inputs[1]?.value||'').trim() };
      }).filter(d => d.nama);
  }

  function collectSkema() {
    return [...document.getElementById('skemaList').querySelectorAll('.skema-row input')]
      .map(i => (i.value||'').trim()).filter(Boolean);
  }

  async function submitForm() {
    const btn = document.getElementById('btnSubmit');
    const alertEl = document.getElementById('alertError');
    alertEl.className = 'alert'; alertEl.innerHTML = '';

    const payload = {
      nama_kaprodi: document.getElementById('namaKaprodi').value.trim(),
      no_hp:        document.getElementById('noHp').value.trim(),
      prodi:        document.getElementById('prodi').value,
      dosen:        collectDosen(),
      skema:        collectSkema(),
    };

    const preErrors = [];
    if (!payload.nama_kaprodi) preErrors.push('Nama Lengkap Kaprodi wajib diisi.');
    if (!payload.no_hp)        preErrors.push('Nomor HP wajib diisi.');
    if (!payload.prodi)        preErrors.push('Program Studi wajib dipilih.');
    if (payload.dosen.length < 2) preErrors.push('Minimal 2 dosen yang diusulkan harus diisi.');
    if (payload.skema.length < 2) preErrors.push('Minimal 2 judul skema harus diisi.');

    if (preErrors.length) {
      alertEl.className = 'alert danger show';
      alertEl.innerHTML = '<strong>Mohon lengkapi data berikut:</strong><ul>' +
        preErrors.map(e => `<li>${e}</li>`).join('') + '</ul>';
      alertEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      return;
    }

    btn.disabled = true; btn.classList.add('loading');
    btn.querySelector('.btn-text').textContent = 'Mengirim...';

    try {
      const res = await fetch('/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const json = await res.json();
      if (json.success) {
        document.getElementById('formWrapper').style.display = 'none';
        document.getElementById('successScreen').classList.add('show');
      } else {
        alertEl.className = 'alert danger show';
        alertEl.innerHTML = '<strong>Gagal menyimpan:</strong><ul>' +
          (json.errors||['Terjadi kesalahan.']).map(e => `<li>${e}</li>`).join('') + '</ul>';
      }
    } catch {
      alertEl.className = 'alert danger show';
      alertEl.innerHTML = 'Gagal terhubung ke server. Periksa koneksi Anda.';
    } finally {
      btn.disabled = false; btn.classList.remove('loading');
      btn.querySelector('.btn-text').textContent = 'Kirim Pendaftaran';
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
            timestamp, nama_kaprodi, no_hp, prodi,
            json.dumps(dosen_valid, ensure_ascii=False),
            json.dumps(skema_valid, ensure_ascii=False),
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


# Untuk local development
if __name__ == "__main__":
    app.run(debug=True)

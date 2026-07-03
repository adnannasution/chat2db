# Chat to DB — Equipment Inspection

Web chat sederhana: user ketik narasi hasil inspeksi equipment (bahasa natural),
LLM (Dinoiki API / gpt-4o) mengekstrak jadi JSON terstruktur, lalu otomatis
tersimpan ke PostgreSQL.

## Struktur

```
chat2db/
├── main.py            # FastAPI app + endpoints
├── database.py         # SQLAlchemy engine, session, ORM models
├── schemas.py           # Pydantic schemas (validasi hasil ekstraksi LLM)
├── llm_service.py       # Pemanggilan Dinoiki API + parsing JSON
├── schema.sql            # DDL manual (opsional, alternatif dari init_db())
├── requirements.txt
├── .env.example
└── static/
    └── index.html        # Chat UI (vanilla HTML/JS)
```

## Setup lokal

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: isi DATABASE_URL dan DINOIKI_API_KEY

uvicorn main:app --reload --port 8000
```

Buka http://localhost:8000

Tabel `inspections` dan `inspection_findings` dibuat otomatis saat startup
(`init_db()` di `main.py`). Kalau mau apply manual, jalankan `schema.sql`
langsung di database Postgres kamu.

## Environment Variables

| Variable          | Keterangan                                      |
|--------------------|--------------------------------------------------|
| `DATABASE_URL`     | Connection string PostgreSQL                     |
| `DINOIKI_URL`      | Endpoint Dinoiki API (default sudah di-set)      |
| `DINOIKI_API_KEY`  | API key Dinoiki kamu                             |
| `DINOIKI_MODEL`    | Default `gpt-4o`                                 |

## Deploy ke Railway

1. Push folder ini ke GitHub repo.
2. Buat project baru di Railway, connect ke repo.
3. Attach plugin **PostgreSQL** — Railway otomatis inject `DATABASE_URL`.
4. Tambahkan env var `DINOIKI_API_KEY` (dan `DINOIKI_MODEL` kalau mau ganti model).
5. Set start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Deploy. Tabel akan otomatis dibuat saat pertama kali start.

## Cara kerja alur data

1. User ketik narasi di chat, mis: *"Pompa P-101A DE bearing naik ke 87°C dari 72°C..."*
2. Frontend POST ke `/api/chat` → backend kirim narasi + system prompt (berisi skema JSON target) ke Dinoiki API.
3. Response LLM di-parse dan divalidasi pakai Pydantic (`InspectionExtract`).
4. Data disimpan: 1 row di `inspections`, N rows di `inspection_findings` (relasi 1-ke-banyak).
5. `raw_json` juga disimpan penuh di kolom JSONB untuk audit trail / debug kalau parsing prompt perlu di-tuning.
6. Frontend menampilkan kartu ringkasan hasil ekstraksi + refresh daftar riwayat di sidebar.

## Endpoint API

- `POST /api/chat` — `{ "message": "narasi inspeksi..." }` → ekstrak, simpan, balas ringkasan + data
- `GET /api/inspections?equipment_tag=P-101A&limit=50` — daftar riwayat (bisa difilter by tag)
- `GET /api/inspections/{id}` — detail 1 inspeksi + findings-nya
- `DELETE /api/inspections/{id}` — hapus inspeksi (findings ikut terhapus via cascade)

## Catatan tuning prompt

Kalau hasil ekstraksi kurang konsisten (misal status salah simpul, parameter
penamaan tidak seragam), edit `SYSTEM_PROMPT` di `llm_service.py` — tambahkan
lebih banyak contoh few-shot atau perketat aturan penamaan `parameter`
supaya query/filter di masa depan tetap konsisten (mis. selalu snake_case).
"# chat2db" 

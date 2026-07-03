from typing import List, Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

import database
import llm_service
from database import Finding, Inspection, get_db, init_db
from schemas import ChatRequest, ChatResponse, InspectionOut

app = FastAPI(title="Chat-to-DB Equipment Inspection")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


# ---------- Chat endpoint: narasi -> LLM -> simpan ke DB ----------
@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, db: Session = Depends(get_db)):
    narrative = req.message.strip()
    if not narrative:
        raise HTTPException(status_code=400, detail="Pesan tidak boleh kosong.")

    try:
        extracted = await llm_service.extract_inspection(narrative)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gagal mengekstrak data: {e}")

    inspection = Inspection(
        equipment_tag=extracted.equipment_tag,
        inspection_date=extracted.inspection_date,
        equipment_type=extracted.equipment_type,
        operating_status=extracted.operating_status,
        raw_narrative=narrative,
        raw_json=extracted.model_dump(mode="json"),
    )
    db.add(inspection)
    db.flush()  # dapatkan inspection.id sebelum commit

    for f in extracted.findings:
        db.add(Finding(
            inspection_id=inspection.id,
            parameter=f.parameter,
            component=f.component,
            finding=f.finding,
            location=f.location,
            value=f.value,
            unit=f.unit,
            previous_value=f.previous_value,
            normal_value=f.normal_value,
            status=f.status,
        ))

    db.commit()
    db.refresh(inspection)

    n_findings = len(extracted.findings)
    n_alerts = sum(1 for f in extracted.findings if f.status in ("high", "warning", "low", "decreasing", "increasing"))
    reply = (
        f"Tersimpan: {extracted.equipment_tag} ({extracted.inspection_date}). "
        f"{n_findings} temuan dicatat"
        + (f", {n_alerts} di antaranya perlu perhatian." if n_alerts else ".")
    )

    return ChatResponse(reply=reply, data=extracted, saved_id=inspection.id)


# ---------- CRUD read endpoints ----------
@app.get("/api/inspections", response_model=List[InspectionOut])
def list_inspections(
    equipment_tag: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    q = db.query(Inspection).order_by(Inspection.created_at.desc())
    if equipment_tag:
        q = q.filter(Inspection.equipment_tag.ilike(f"%{equipment_tag}%"))
    return q.limit(limit).all()


@app.get("/api/inspections/{inspection_id}", response_model=InspectionOut)
def get_inspection(inspection_id: int, db: Session = Depends(get_db)):
    inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection tidak ditemukan.")
    return inspection


@app.delete("/api/inspections/{inspection_id}")
def delete_inspection(inspection_id: int, db: Session = Depends(get_db)):
    inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection tidak ditemukan.")
    db.delete(inspection)
    db.commit()
    return {"deleted": inspection_id}


# ---------- Static frontend ----------
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def index():
    return FileResponse("static/index.html")


@app.get("/data")
def data_page():
    return FileResponse("static/data.html")

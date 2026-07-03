import json
import os
import re
from datetime import date

import httpx

from schemas import InspectionExtract

DINOIKI_URL = os.getenv("DINOIKI_URL", "https://ai.dinoiki.com/v1/chat/completions")
DINOIKI_API_KEY = os.getenv("DINOIKI_API_KEY", "")
DINOIKI_MODEL = os.getenv("DINOIKI_MODEL", "gpt-4o")

SYSTEM_PROMPT = """Kamu adalah sistem ekstraksi data untuk laporan inspeksi equipment refinery.
Tugasmu: baca narasi inspeksi (Bahasa Indonesia atau Inggris) dan ubah menjadi JSON terstruktur
sesuai skema berikut. HANYA balas dengan JSON valid, tanpa markdown fence, tanpa penjelasan tambahan.

Skema:
{
  "equipment_tag": "string, wajib. Contoh: P-101A",
  "inspection_date": "YYYY-MM-DD, wajib. Jika tidak disebutkan, gunakan tanggal hari ini: %(today)s",
  "equipment_type": "string atau null. Contoh: centrifugal_pump, compressor, heat_exchanger",
  "operating_status": "string atau null. Contoh: running, standby, shutdown",
  "findings": [
    {
      "parameter": "string atau null. snake_case. Contoh: bearing_temperature, vibration, discharge_pressure, suction_pressure, flow_rate, motor_current",
      "component": "string atau null. Isi HANYA jika finding tentang komponen (bukan parameter terukur). Contoh: mechanical_seal, coupling, foundation_bolt",
      "finding": "string atau null. Isi HANYA jika component diisi. Deskripsi singkat temuan. Contoh: minor leakage",
      "location": "string atau null. Contoh: DE, NDE, DE-horizontal, DE-vertical, NDE-axial",
      "value": "number atau null. Nilai terukur saat ini",
      "unit": "string atau null. Contoh: degC, mm/s, bar, A, m3/h",
      "previous_value": "number atau null. Nilai pengukuran sebelumnya jika disebutkan",
      "normal_value": "number atau null. Nilai normal/setpoint jika disebutkan",
      "status": "salah satu: normal, warning, high, low, increasing, decreasing. Simpulkan dari konteks (misal naik drastis dari nilai sebelumnya = high atau increasing; sedikit di atas normal = warning)"
    }
  ]
}

Setiap item dalam findings HARUS berupa salah satu dari dua bentuk:
1. Finding parameter terukur: isi "parameter", boleh isi location/value/unit/previous_value/normal_value/status, "component" dan "finding" harus null.
2. Finding komponen/kualitatif: isi "component" dan "finding", "parameter"/"value"/"unit" boleh null.

Jangan mengarang angka yang tidak disebutkan di narasi. Jika suatu field tidak disebutkan, isi null.
Balas HANYA objek JSON tersebut, tidak ada teks lain sebelum atau sesudahnya.
"""


def _build_system_prompt() -> str:
    return SYSTEM_PROMPT % {"today": date.today().isoformat()}


def _strip_json_fence(text: str) -> str:
    text = text.strip()
    # buang ```json ... ``` atau ``` ... ``` jika model tetap membungkusnya
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


async def describe_photo(image_base64: str, mime_type: str = "image/jpeg") -> str:
    """Generate short Indonesian description of equipment condition from photo."""
    if not DINOIKI_API_KEY:
        raise RuntimeError("DINOIKI_API_KEY belum di-set di environment variable.")

    payload = {
        "model": DINOIKI_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{image_base64}"},
                    },
                    {
                        "type": "text",
                        "text": (
                            "Kamu adalah inspektor equipment industri. "
                            "Deskripsikan kondisi equipment dalam foto ini secara singkat dalam Bahasa Indonesia, "
                            "maksimal 2 kalimat. Fokus pada kondisi fisik yang terlihat, anomali, atau kerusakan. "
                            "Jika tidak ada anomali yang jelas, sebutkan kondisi tampak normal."
                        ),
                    },
                ],
            }
        ],
        "max_tokens": 200,
        "temperature": 0.3,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DINOIKI_API_KEY}",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(DINOIKI_URL, headers=headers, json=payload)
        resp.raise_for_status()
        result = resp.json()

    try:
        return result["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError):
        return "Deskripsi tidak tersedia."


async def extract_inspection(narrative: str) -> InspectionExtract:
    if not DINOIKI_API_KEY:
        raise RuntimeError("DINOIKI_API_KEY belum di-set di environment variable.")

    payload = {
        "model": DINOIKI_MODEL,
        "messages": [
            {"role": "system", "content": _build_system_prompt()},
            {"role": "user", "content": narrative},
        ],
        "max_tokens": 1200,
        "temperature": 0.1,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DINOIKI_API_KEY}",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(DINOIKI_URL, headers=headers, json=payload)
        resp.raise_for_status()
        result = resp.json()

    try:
        content = result["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Format respons LLM tidak dikenali: {result}") from e

    cleaned = _strip_json_fence(content)

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Gagal parse JSON dari LLM: {e}\nRaw content: {content}") from e

    return InspectionExtract(**parsed)

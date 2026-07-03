-- ============================================================
-- Schema: Chat-to-DB Equipment Inspection
-- ============================================================

CREATE TABLE IF NOT EXISTS inspections (
    id                SERIAL PRIMARY KEY,
    equipment_tag     VARCHAR(50)  NOT NULL,
    inspection_date   DATE         NOT NULL,
    equipment_type    VARCHAR(100),
    operating_status  VARCHAR(50),
    raw_narrative     TEXT         NOT NULL,   -- teks chat asli dari user
    raw_json          JSONB,                   -- hasil mentah ekstraksi LLM (audit trail)
    created_at        TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS inspection_findings (
    id                SERIAL PRIMARY KEY,
    inspection_id     INTEGER      NOT NULL REFERENCES inspections(id) ON DELETE CASCADE,
    parameter         VARCHAR(100),            -- ex: bearing_temperature, vibration, discharge_pressure
    component         VARCHAR(100),            -- ex: mechanical_seal (untuk finding non-parameter)
    finding           TEXT,                    -- ex: "minor leakage"
    location           VARCHAR(50),             -- ex: DE, NDE, DE-horizontal
    value             NUMERIC,
    unit              VARCHAR(20),
    previous_value    NUMERIC,
    normal_value      NUMERIC,
    status            VARCHAR(20),             -- normal/warning/high/low/increasing/decreasing
    created_at        TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_inspections_tag    ON inspections(equipment_tag);
CREATE INDEX IF NOT EXISTS idx_inspections_date   ON inspections(inspection_date);
CREATE INDEX IF NOT EXISTS idx_findings_status    ON inspection_findings(status);
CREATE INDEX IF NOT EXISTS idx_findings_inspid    ON inspection_findings(inspection_id);

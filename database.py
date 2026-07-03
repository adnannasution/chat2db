import os
from datetime import datetime

from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Numeric, Date, DateTime,
    ForeignKey, JSON
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/chat2db")

# Railway kadang kasih url dengan prefix postgres:// -> perlu diubah ke postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Inspection(Base):
    __tablename__ = "inspections"

    id = Column(Integer, primary_key=True, index=True)
    equipment_tag = Column(String(50), nullable=False, index=True)
    inspection_date = Column(Date, nullable=False, index=True)
    equipment_type = Column(String(100))
    operating_status = Column(String(50))
    raw_narrative = Column(Text, nullable=False)
    raw_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    findings = relationship(
        "Finding", back_populates="inspection", cascade="all, delete-orphan"
    )


class Finding(Base):
    __tablename__ = "inspection_findings"

    id = Column(Integer, primary_key=True, index=True)
    inspection_id = Column(Integer, ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False)
    parameter = Column(String(100))
    component = Column(String(100))
    finding = Column(Text)
    location = Column(String(50))
    value = Column(Numeric)
    unit = Column(String(20))
    previous_value = Column(Numeric)
    normal_value = Column(Numeric)
    status = Column(String(20), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    inspection = relationship("Inspection", back_populates="findings")


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Boolean
from sqlalchemy.sql import func
from backend.db.database import Base
import uuid


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    location = Column(String)
    remote = Column(Boolean, default=False)
    salary_min = Column(Integer)
    salary_max = Column(Integer)
    salary_estimated = Column(Boolean, default=False)
    description = Column(Text)
    url = Column(String)
    source = Column(String)          # linkedin | indeed | reed | adzuna | glassdoor | totaljobs
    industry = Column(String)
    date_posted = Column(DateTime)
    date_scraped = Column(DateTime, server_default=func.now())
    compatibility_score = Column(Float)   # 0–100
    score_reason = Column(String)         # one-line AI explanation
    score_suggestion = Column(String)     # one-line tailoring tip
    is_active = Column(Boolean, default=True)
    is_gaming = Column(Boolean, default=False)

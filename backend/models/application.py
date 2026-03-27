from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from backend.db.database import Base
import uuid


class Application(Base):
    __tablename__ = "applications"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False)
    status = Column(String, default="applied")   # applied | screen | interview | offer | rejected
    applied_at = Column(DateTime, server_default=func.now())
    next_action = Column(String)
    next_action_date = Column(DateTime)
    notes = Column(Text)
    cv_version = Column(Text)        # the tailored CV used for this application

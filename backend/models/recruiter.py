from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from backend.db.database import Base
import uuid


class Recruiter(Base):
    __tablename__ = "recruiters"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=True, index=True)  # owner; nullable for legacy rows
    name = Column(String)
    title = Column(String)
    company = Column(String)
    linkedin_url = Column(String)
    job_id = Column(String)          # linked job they're hiring for
    message_draft = Column(String)   # AI-suggested outreach message
    contacted = Column(String, default="no")   # no | sent | replied
    found_at = Column(DateTime, server_default=func.now())

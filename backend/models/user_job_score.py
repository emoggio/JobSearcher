from sqlalchemy import Column, String, Float, Text, UniqueConstraint
from backend.db.database import Base


class UserJobScore(Base):
    """Per-user Claude-scored compatibility for a job. One row per (user, job)."""

    __tablename__ = "user_job_scores"
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_user_job"),)

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    job_id = Column(String, nullable=False, index=True)
    score = Column(Float)
    reason = Column(String)
    suggestion = Column(Text)

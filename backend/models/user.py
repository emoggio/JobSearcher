from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.sql import func
from backend.db.database import Base
import uuid


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)       # sha256(password).hexdigest()
    recovery_code_hash = Column(String, nullable=True)  # sha256(recovery_code).hexdigest()
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

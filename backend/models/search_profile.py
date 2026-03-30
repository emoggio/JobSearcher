from sqlalchemy import Column, String, Text
from backend.db.database import Base
import uuid


class SearchProfile(Base):
    __tablename__ = "search_profiles"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    filters = Column(Text, nullable=False)  # JSON string of filter config

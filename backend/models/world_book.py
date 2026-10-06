from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, func
from backend.models.database import Base


class WorldBook(Base):
    __tablename__ = "world_books"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # 所有者：同 CharacterCard.user_id，查询必须带
    user_id = Column(Integer, index=True)
    name = Column(String(200), nullable=False, default="未命名世界书")
    description = Column(Text, default="")
    tags = Column(JSON, default=list)
    entries = Column(JSON, default=list)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

from sqlalchemy import Column, Integer, String, Text, Boolean, JSON, DateTime, func
from backend.models.database import Base


class CharacterCard(Base):
    __tablename__ = "character_cards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # 所有者：公网版「只有本人能看到自己的卡」靠它，所有查询都必须带这个条件
    user_id = Column(Integer, index=True)
    name = Column(String(200), nullable=False, default="未命名角色")
    age = Column(String(50), default="")
    gender = Column(String(50), default="")
    species = Column(String(100), default="")
    occupation = Column(String(200), default="")
    appearance = Column(Text, default="")
    personality = Column(Text, default="")
    background = Column(Text, default="")
    description = Column(Text, default="")
    tags = Column(JSON, default=list)
    has_status_bar = Column(Boolean, default=False)
    status_bar_content = Column(Text, default="")
    custom_css = Column(Text, default="")
    first_message = Column(Text, default="")
    image_path = Column(String(500), default="")
    raw_json = Column(JSON, default=dict)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

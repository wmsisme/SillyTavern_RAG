from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, func
from backend.models.database import Base


class User(Base):
    """账号。

    公网版是「每个人自己的私有卡库 + 一个公共知识库」——所以数据必须先有主，
    卡片/世界书都挂在 user_id 上，谁的数据只有谁能看（见 card_service / worldbook_service）。
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(200), nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)   # 首个注册者
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class SessionToken(Base):
    """登录会话。

    选「数据库会话 + httponly Cookie」而不是 JWT，理由有三：
      ① 不引第三方库（python-jose / passlib 都没装，也不想为此加依赖）；
      ② 能吊销（改密码/踢下线只是删一行）；
      ③ Cookie 能跟着 <img src> 一起走 —— 角色卡图片要过鉴权端点，用 Authorization
         头的话 <img> 标签根本发不出去（图片会 401）。
    """

    __tablename__ = "sessions"

    token = Column(String(64), primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=False)


class UserLLMSettings(Base):
    """用户存在自己账号里的大模型配置（换了设备登录也能直接用）。

    与「只存浏览器」的区别就在这里：存账号 = 服务器替你保管（加密态），
    代价是服务器必须能解出明文才能调用平台；存浏览器 = 服务器从不经手。
    两种都由用户在设置框里自选，界面上会写明差别。

    api_key 只存密文（见 services/secret_box.py）；接口**永不回传原文**，只回 masked。
    """

    __tablename__ = "user_llm_settings"

    user_id = Column(Integer, primary_key=True)
    provider = Column(String(32), nullable=False)
    model = Column(String(128), default="")
    base_url = Column(String(255), default="")
    api_key_enc = Column(Text, nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

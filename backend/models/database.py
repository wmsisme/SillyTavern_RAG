from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.config import DB_PATH

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _columns_of(conn, table: str) -> set:
    try:
        rows = conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
    except Exception:
        return set()
    return {r[1] for r in rows}


def _ensure_columns() -> None:
    """给老库补列。

    `Base.metadata.create_all` 只建「不存在的表」，**不会**给已存在的表加列 ——
    本地那份 data.db 是加多租户之前建的，得手动补 user_id，否则老数据一条都读不出来。
    加管理/封禁功能时同理：users 表要补 ban_reason 与 banned_at。
    """
    wanted = {
        "character_cards": [("user_id", "INTEGER")],
        "world_books": [("user_id", "INTEGER")],
        "users": [("ban_reason", "VARCHAR(255)"), ("banned_at", "DATETIME")],
        "query_logs": [("feedback_reason", "TEXT"), ("feedback_at", "DATETIME"),
                       ("sources_digest", "TEXT"), ("marked", "BOOLEAN"),
                       ("marked_at", "DATETIME")],
    }
    with engine.begin() as conn:
        for table, cols in wanted.items():
            have = _columns_of(conn, table)
            if not have:            # 表还不存在，create_all 会建全，不用补
                continue
            for c, sqltype in cols:
                if c not in have:
                    conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {c} {sqltype}")
                    print(f"[db] 已给 {table} 补列 {c}（老记录该列为空，不影响使用）")


def init_db():
    # 这些 import 不能移到文件顶部：模型要 import Base，而 Base 在本模块里定义
    from backend.models.character_card import CharacterCard  # noqa: F401
    from backend.models.world_book import WorldBook          # noqa: F401
    from backend.models.user import User, SessionToken, UserLLMSettings  # noqa: F401
    from backend.models.admin import IpBan, QueryLog, UserFeedback  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_columns()

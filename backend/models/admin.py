from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float
from backend.models.database import Base


class IpBan(Base):
    """IP 黑名单。

    为什么账号封了还要能封 IP：账号可以换、可以共享、可以再注册，**换 IP 的成本高得多**。
    两者配合才挡得住「共享账号发违规内容」这种玩法。

    ⚠️ 环回地址（127.0.0.1 / ::1）由中间件写死放行、也拒绝被写进黑名单：
    一旦前面挂了反向代理，所有请求在服务端看来都来自 127.0.0.1 ——
    那时封任何一个 IP 都等于**把全站封掉**（见 api/ban_guard.py 的说明）。
    """

    __tablename__ = "ip_bans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ip = Column(String(64), unique=True, nullable=False, index=True)
    reason = Column(String(255), default="")
    created_by = Column(String(64), default="")
    created_at = Column(DateTime, default=datetime.now)
    expires_at = Column(DateTime, nullable=True)        # 空 = 永久


class QueryLog(Base):
    """提问记录：谁、什么时候、问了什么、答没答上来。

    两个用途：
      ① **有据可查** —— 站长能看到用户在问什么，发现有人拿共享账号发违规内容时不是瞎猜；
      ② **攒改进清单** —— 没答上来的问题（检索无来源，或最高相关度低于阈值）
         汇总起来就是「下次该往知识库补什么」。

    只在服务端留最近的一批，超过上限自动裁掉最老的（见 admin_service.prune_query_logs）。

    ⚠️ 时间一律**本地时间**（`default=datetime.now`）：SQLite 的 `CURRENT_TIMESTAMP`
    给的是 UTC，会让「今天有多少提问」差 8 小时。全项目的 created_at 都是 server_default，
    那是历史；这张表是给站长看报表的，按北京时间算才对。
    """

    __tablename__ = "query_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.now, index=True)
    ip = Column(String(64), default="", index=True)
    user_id = Column(Integer, nullable=True, index=True)     # 未登录提问时为 NULL
    username = Column(String(64), default="")
    kind = Column(String(16), default="search")              # search / ask / ask_stream
    query = Column(Text, nullable=False)
    sources_count = Column(Integer, default=0)
    top_score = Column(Float, default=0.0)
    answered = Column(Boolean, default=True, nullable=False)  # False = 疑似没答上来
    # 用户反馈："" / solved（有帮助）/ unsolved（没解决）/ irrelevant（检索到了但不相关）
    feedback = Column(String(16), default="")
    feedback_reason = Column(Text, default="")                # 用户填的原因（选填）
    feedback_at = Column(DateTime, nullable=True)
    # 当时的检索结果摘要（前 5 条的 source + score，JSON）——
    # 没有它，事后看到「用户说不相关」也不知道当时系统给了什么，等于无法复现。
    sources_digest = Column(Text, default="")

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
    # 顺手做「标记」：站长在后台勾选「这条要拿去更新知识库」。
    # **勾选权必须留在人手上** —— 用户随便问一句就自动灌进知识库会污染它，
    # 所以这里只做标记，真正的「补什么内容」由站长勾选后再定（见 tools/update_queue.py）。
    marked = Column(Boolean, default=False, nullable=False, index=True)
    marked_at = Column(DateTime, nullable=True)
    # 同一 IP 在短时间内重复问同一个问题时**不新建记录**，只在这条上累加。
    # 判据是「同 IP + 同问题」（达铭 2026-10-07 定）—— 不同用户问同一个问题很正常，不该合并。
    repeat_count = Column(Integer, default=1, nullable=False)
    # 用户反馈："" / solved（有帮助）/ unsolved（没解决）/ irrelevant（检索到了但不相关）
    feedback = Column(String(16), default="")
    feedback_reason = Column(Text, default="")                # 用户填的原因（选填）
    feedback_at = Column(DateTime, nullable=True)
    # 当时的检索结果摘要（前 5 条的 source + score，JSON）——
    # 没有它，事后看到「用户说不相关」也不知道当时系统给了什么，等于无法复现。
    sources_digest = Column(Text, default="")


class LoginLog(Base):
    """登录记录：谁、什么时候、从哪个 IP 登录的。

    用途（达铭 2026-10-07）：判断「**同一个账号是不是被多人共用**」——
    一个账号短时间内从好几个不同 IP 登录，通常就是共享账号；
    配合提问记录看，就能定位"用共享账号发违规内容"的人。

    ⚠️ 这是**敏感数据**（用户的网络来源），只给管理员看，界面上也不该外露给普通用户。
    """

    __tablename__ = "login_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.now, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    username = Column(String(64), default="")
    ip = Column(String(64), default="", index=True)
    user_agent = Column(String(255), default="")      # 浏览器/系统，辅助判断是不是同一台设备
    action = Column(String(16), default="login")      # login / register / logout


class UserFeedback(Base):
    """用户主动提交的功能反馈（顶部栏「反馈」按钮，只有登录用户能看到入口）。

    与 QueryLog 的区别：QueryLog 记的是「用户问了什么」（系统自动记），
    这张表记的是「用户主动想说什么」—— 哪里不足、哪里不顺手、哪里报错。
    建议类信息只有用户主动说才拿得到，日志里永远不会有。
    """

    __tablename__ = "user_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.now, index=True)   # 本地时间，同上
    user_id = Column(Integer, nullable=True, index=True)
    username = Column(String(64), default="")
    ip = Column(String(64), default="")
    category = Column(String(16), default="其他")     # 建议 / 体验 / 故障 / 其他
    content = Column(Text, nullable=False)
    page = Column(String(128), default="")            # 在哪个页面点的（方便定位）
    handled = Column(Boolean, default=False, nullable=False, index=True)
    handled_at = Column(DateTime, nullable=True)
    handled_by = Column(String(64), default="")


class ClientError(Base):
    """前端错误上报：用户浏览器里崩了，服务端第一次能知道。

    为什么单独存一张表、而不只是写日志：
      · 日志是**轮转**的（10MB × 5），错误一多就被冲掉 —— 而错误恰恰是要**事后翻**的；
      · 存表才能回答「这类错误今天出了多少次、集中在哪个页面」这种问题。

    与 QueryLog 的分工：那个记「用户问了什么」，这个记「我们的前端坏了什么」。
    与 LoginLog 一样带 IP，同属只给管理员看的运维数据。

    **刻意不记**：用户输入内容、Cookie、token、localStorage 里的任何东西。
    上报字段全是浏览器自己产生的技术信息（消息 / 堆栈 / 页面 / UA），
    前端也只发这些（见 frontend/src/services/errorReporter.ts）。
    """

    __tablename__ = "client_errors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.now, index=True)   # 本地时间，理由同 QueryLog
    ip = Column(String(64), default="", index=True)
    user_id = Column(Integer, nullable=True, index=True)              # 未登录时报错也要收
    username = Column(String(64), default="")
    kind = Column(String(24), default="error")                        # error / unhandledrejection
    message = Column(Text, default="")
    stack = Column(Text, default="")                                  # 已截断的堆栈
    page = Column(String(255), default="", index=True)                # 出错时所在的前端路由
    source = Column(String(255), default="")                          # 报错脚本的 URL
    line = Column(Integer, default=0)
    col = Column(Integer, default=0)
    user_agent = Column(String(255), default="")


class FeedbackAttachment(Base):
    """反馈附件：用户在反馈时投递的文件（技术档案之类）。

    **为什么单独一张表**：两个入口都要用（顶部「反馈」按钮 / 提问后的评价），
    而且一次可以传多个 —— 是一对多的关系。
    用 `source` + `ref_id` 指回来源；`ref_id` 允许为空（"先传文件、后交反馈"的顺序也可能出现）。

    **它是「待灌库素材」的来源之一**：站长在后台勾选「这条要补进知识库」时，
    能顺手把附件下载下来看 —— 但**绝不自动入库**（延续「我来勾选」那条规矩）。

    与卡图的分工：卡图是**用户自己的资产**（他自己要看），
    附件是**投递给站长的**（站长要用来改知识库），所以后台的可见性要求更高。

    ⚠️ 磁盘闸门（2026-10-08 达铭明确要求「服务器是我的电脑，放不了那么多东西」）：
    单文件大小 / 每次个数 / 每 IP 每天 / 每用户累计 / **全局总量** —— 五道都在
    `services/attachment_service.py` 里，那张表只是记账。
    """

    __tablename__ = "feedback_attachments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.now, index=True)   # 本地时间，理由同 QueryLog
    ip = Column(String(64), default="", index=True)
    user_id = Column(Integer, nullable=True, index=True)
    username = Column(String(64), default="")
    source = Column(String(24), default="feedback")        # feedback / query
    ref_id = Column(Integer, nullable=True, index=True)    # user_feedback.id 或 query_logs.id
    orig_name = Column(String(255), default="")            # 原文件名 —— **仅用于展示**，不参与取文件
    stored_name = Column(String(80), unique=True, nullable=False)   # UUID + 扩展名，真正的磁盘名
    size = Column(Integer, default=0)                      # 字节
    content_type = Column(String(128), default="")

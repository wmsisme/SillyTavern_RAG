import base64
import json
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import Response
from backend.services import toolbox_service

router = APIRouter()

# 上传体积上限（2026-10-07 安全加固）。
# 原来直接 file.file.read() 把整个文件读进内存，实测传 50MB 照样 200 ——
# 天花板完全由来访者决定。本机只有 16GB 内存，几个人同时传大文件就能把服务打趴，
# 而这个接口**连登录都不需要**（工具箱是免费开放的）。
# 32MB 与前端 ToolDetailPage 的 MAX_UPLOAD_MB 保持一致 —— 两边不一样的话，
# 用户会先被前端放行、再被后端一句"太大了"顶回来，看着像 bug。
MAX_UPLOAD_BYTES = 32 * 1024 * 1024


def _read_upload(file: UploadFile) -> bytes:
    """读上传内容，**在读取这一步就设上限**。

    多读 1 字节只是用来判断"是否超限"，所以超大文件不会被整个拉进内存。
    """
    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"文件太大了（上限 {MAX_UPLOAD_BYTES // 1024 // 1024} MB）。"
                   f"工具箱是随手转小文件用的，大文件请本地处理。")
    return data


# ⚠️ 这里刻意**不用 async def**。
# 这些工具全是同步重活（图片处理、正则替换、JSONL 解析、OCR 前处理），
# 写在 async def 里会**阻塞整个事件循环** —— 一个人转大文件，别人连页面都加载不出来。
# 改成普通 def，FastAPI 会把它们丢进线程池并发跑；读上传文件用 file.file.read()（同步读）。
# 判据：**只要函数体里没有 await 的必要，就别写成 async def**。


@router.post("/separator")
def metadata_separator(file: UploadFile = File(...)):
    content = _read_upload(file)
    result = toolbox_service.separate_metadata(content, file.filename or "unnamed.png")

    # 图片是 bytes，直接塞进返回值会让 FastAPI 的 JSON 序列化抛 500，
    # 所以在这里转成 base64 字符串出网。
    image_data = result.pop("image_data", None)
    result["image_base64"] = base64.b64encode(image_data).decode("ascii") if image_data else None
    result["image_mime"] = "image/png"
    return result


@router.post("/worldbook-converter")
def worldbook_converter(
    file: UploadFile = File(...),
    direction: str = Form("characterbook_to_worldbook"),
):
    content = _read_upload(file)
    result = toolbox_service.convert_worldbook(content, file.filename or "unnamed.json", direction)
    return result


@router.post("/chinese-converter")
def chinese_converter(
    file: UploadFile = File(...),
    direction: str = Form("s2t"),
):
    content = _read_upload(file)
    result = toolbox_service.convert_chinese(content, file.filename or "unnamed.txt", direction)
    return result


@router.post("/width-converter")
def width_converter(
    file: UploadFile = File(...),
    operation: str = Form("fullwidth_to_halfwidth"),
):
    content = _read_upload(file)
    result = toolbox_service.format_text(content, file.filename or "unnamed.txt", operation)
    return result


@router.post("/jsonl-novel-converter")
def jsonl_novel_converter(
    file: UploadFile = File(...),
    character_mapping: str = Form("{}"),
    include_reasoning: str = Form("false"),
):
    content = _read_upload(file)
    try:
        mapping = json.loads(character_mapping)
        if not isinstance(mapping, dict):
            mapping = {}
    except Exception:
        mapping = {}
    include = str(include_reasoning).lower() in ("1", "true", "yes", "on")
    result = toolbox_service.convert_jsonl_to_novel(
        content, file.filename or "unnamed.jsonl", mapping, include)
    return result

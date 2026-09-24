import base64
import json
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import Response
from backend.services import toolbox_service

router = APIRouter()


@router.post("/separator")
async def metadata_separator(file: UploadFile = File(...)):
    content = await file.read()
    result = toolbox_service.separate_metadata(content, file.filename or "unnamed.png")

    # 图片是 bytes，直接塞进返回值会让 FastAPI 的 JSON 序列化抛 500，
    # 所以在这里转成 base64 字符串出网。
    image_data = result.pop("image_data", None)
    result["image_base64"] = base64.b64encode(image_data).decode("ascii") if image_data else None
    result["image_mime"] = "image/png"
    return result


@router.post("/worldbook-converter")
async def worldbook_converter(
    file: UploadFile = File(...),
    direction: str = Form("characterbook_to_worldbook"),
):
    content = await file.read()
    result = toolbox_service.convert_worldbook(content, file.filename or "unnamed.json", direction)
    return result


@router.post("/chinese-converter")
async def chinese_converter(
    file: UploadFile = File(...),
    direction: str = Form("s2t"),
):
    content = await file.read()
    result = toolbox_service.convert_chinese(content, file.filename or "unnamed.txt", direction)
    return result


@router.post("/width-converter")
async def width_converter(
    file: UploadFile = File(...),
    operation: str = Form("fullwidth_to_halfwidth"),
):
    content = await file.read()
    result = toolbox_service.format_text(content, file.filename or "unnamed.txt", operation)
    return result


@router.post("/jsonl-novel-converter")
async def jsonl_novel_converter(
    file: UploadFile = File(...),
    character_mapping: str = Form("{}"),
):
    content = await file.read()
    try:
        mapping = json.loads(character_mapping)
    except Exception:
        mapping = {}
    result = toolbox_service.convert_jsonl_to_novel(content, file.filename or "unnamed.jsonl", mapping)
    return result

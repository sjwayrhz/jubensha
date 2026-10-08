"""管理员后台：剧本上传 → 解析 → 校对 → 结构化 → 发布。"""
import logging
import os
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from ...core.config import settings
from ...core.deps import require_admin
from ...db.session import get_db
from ...models.script import Script, ScriptCharacter, ScriptClue
from ...models.user import User
from ...schemas.room import RoleUpdateIn
from ...schemas.script import (
    ScriptOut,
    ScriptParseOut,
    ScriptRawIn,
    ScriptRawOut,
    ScriptStructureOut,
    ScriptUploadOut,
)
from ...schemas.user import UserOut
from ...services.script_parse import parse_pdf
from ...services.script_structure import structure_script

log = logging.getLogger("jubensha.admin")
router = APIRouter(prefix="/admin", tags=["admin"])

_ALLOWED_TYPES = {"application/pdf", "application/octet-stream"}


def _get_script_or_404(db: Session, script_id: int) -> Script:
    script = db.get(Script, script_id)
    if not script:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "剧本不存在")
    return script


@router.get("/scripts", response_model=list[ScriptOut])
def list_scripts(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """剧本列表（全部状态，管理员视角）。"""
    return db.query(Script).order_by(Script.id.desc()).all()


@router.post("/scripts/upload", response_model=ScriptUploadOut, status_code=201)
async def upload_script_pdf(
    file: UploadFile,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """上传剧本 PDF。校验类型/大小，落盘后建 status=uploaded 的记录。"""
    name = file.filename or ""
    if not name.lower().endswith(".pdf") or (
        file.content_type and file.content_type not in _ALLOWED_TYPES
    ):
        raise HTTPException(400, "只接受 PDF 文件")
    os.makedirs(settings.upload_dir, exist_ok=True)
    max_bytes = settings.max_upload_mb * 1024 * 1024
    safe_name = f"{uuid.uuid4().hex}.pdf"
    dest = os.path.join(settings.upload_dir, safe_name)
    size = 0
    with open(dest, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > max_bytes:
                f.close()
                os.remove(dest)
                raise HTTPException(400, f"文件超过 {settings.max_upload_mb}MB 限制")
            f.write(chunk)
    script = Script(
        title=os.path.splitext(name)[0][:255] or "未命名剧本",
        status="uploaded",
        pdf_path=dest,
        created_by=admin.id,
    )
    db.add(script)
    db.commit()
    db.refresh(script)
    log.info("剧本上传：id=%d file=%s size=%d", script.id, dest, size)
    return ScriptUploadOut(script_id=script.id, status=script.status)


@router.post("/scripts/{script_id}/parse", response_model=ScriptParseOut)
def parse_script(
    script_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """解析 PDF：文字版直接提取，扫描版走 OCR。status: uploaded → parsed。"""
    script = _get_script_or_404(db, script_id)
    if not script.pdf_path or not os.path.exists(script.pdf_path):
        raise HTTPException(400, "PDF 文件不存在，请重新上传")
    try:
        text, method = parse_pdf(script.pdf_path, text_threshold=settings.ocr_text_threshold)
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    script.raw_text = text
    script.status = "parsed"
    db.commit()
    log.info("剧本解析：id=%d method=%s chars=%d", script.id, method, len(text))
    return ScriptParseOut(script_id=script.id, status=script.status, method=method, chars=len(text))


@router.get("/scripts/{script_id}/raw", response_model=ScriptRawOut)
def get_script_raw(
    script_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """取解析文本，用于人工校对页展示。"""
    script = _get_script_or_404(db, script_id)
    return ScriptRawOut(
        script_id=script.id, title=script.title, status=script.status,
        raw_text=script.raw_text or "",
    )


@router.put("/scripts/{script_id}/raw", response_model=ScriptRawOut)
def save_script_raw(
    script_id: int,
    data: ScriptRawIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """保存人工校对后的文本。status → reviewed。"""
    script = _get_script_or_404(db, script_id)
    script.raw_text = data.raw_text
    script.status = "reviewed"
    db.commit()
    return ScriptRawOut(
        script_id=script.id, title=script.title, status=script.status,
        raw_text=script.raw_text or "",
    )


@router.post("/scripts/{script_id}/structure", response_model=ScriptStructureOut)
def structure_script_api(
    script_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """规则拆分校对文本 → 人物/线索入库。status → published。"""
    script = _get_script_or_404(db, script_id)
    if not script.raw_text:
        raise HTTPException(400, "没有可拆分的文本，请先解析并校对")
    result = structure_script(script.raw_text)
    # 幂等：先清掉旧的结构化数据
    db.query(ScriptClue).filter_by(script_id=script.id).delete()
    db.query(ScriptCharacter).filter_by(script_id=script.id).delete()
    if result["title"] and script.title in ("未命名剧本", ""):
        script.title = result["title"][:255]
    if result["description"]:
        script.description = result["description"]
    if result["player_min"]:
        script.player_min = result["player_min"]
    if result["player_max"]:
        script.player_max = result["player_max"]
    for c in result["characters"]:
        db.add(ScriptCharacter(
            script_id=script.id, name=c["name"][:64],
            description=c["description"], sort_order=c["sort_order"],
        ))
    db.flush()  # 拿到 character 行后再标真凶
    # 真凶标记：按手册约定从校对文本中找"真凶：X"，匹配角色名后标 is_murderer
    mm = re.search(r"真凶[：:]\s*([^\s，,。；;]+)", script.raw_text or "")
    if mm:
        mname = mm.group(1).strip()
        for ch in db.query(ScriptCharacter).filter_by(script_id=script.id).all():
            if ch.name == mname or mname in ch.name:
                ch.is_murderer = True
                log.info("剧本结构化：真凶标记 -> %s", ch.name)
                break
    for cl in result["clues"]:
        db.add(ScriptClue(
            script_id=script.id, title=cl["title"][:255],
            content=cl["content"], clue_type="public", sort_order=cl["sort_order"],
        ))
    script.status = "published"
    db.commit()
    log.info(
        "剧本结构化：id=%d 人物=%d 线索=%d → published",
        script.id, len(result["characters"]), len(result["clues"]),
    )
    return ScriptStructureOut(
        script_id=script.id, status=script.status,
        characters=len(result["characters"]), clues=len(result["clues"]),
    )


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """用户列表（开 DM 权限用）。"""
    return db.query(User).order_by(User.id.desc()).limit(200).all()


@router.put("/users/{user_id}/role", response_model=UserOut)
def update_user_role(
    user_id: int,
    data: RoleUpdateIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """管理员修改用户角色（熟人邀请制开 DM 用）。"""
    if data.role not in ("admin", "dm", "player"):
        raise HTTPException(400, "role 只能是 admin/dm/player")
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "用户不存在")
    if target.id == admin.id and data.role != "admin":
        raise HTTPException(400, "不能降级自己的管理员身份")
    target.role = data.role
    db.commit()
    db.refresh(target)
    log.info("改角色：user=%d → %s（操作人 admin=%d）", target.id, data.role, admin.id)
    return target

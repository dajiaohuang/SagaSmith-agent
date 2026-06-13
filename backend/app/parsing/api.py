import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.db.database import get_db
from app.parsing.router import parse_file, parse_files
from app.services import ingest_rule_content

router = APIRouter(prefix="/parse", tags=["parsing"])


@router.post("/files")
async def parse_uploaded_files(
    files: list[UploadFile] = File(...),
    strategy: str = Form("auto"),
    per_file_max_chars: int = Form(4000),
    total_max_chars: int = Form(12000),
):
    root = Path(tempfile.mkdtemp(prefix="dnd_upload_"))
    paths: list[str] = []
    try:
        for index, upload in enumerate(files):
            filename = Path(upload.filename or f"file_{index}").name
            target = root / f"{index:02d}_{filename}"
            total = 0
            with target.open("wb") as output:
                while chunk := await upload.read(1024 * 1024):
                    total += len(chunk)
                    if total > settings.attachment_max_bytes:
                        raise HTTPException(413, f"{filename} exceeds attachment size limit")
                    output.write(chunk)
            paths.append(str(target))
        return parse_files(paths, per_file_max_chars, total_max_chars, strategy=strategy)
    finally:
        import shutil
        shutil.rmtree(root, ignore_errors=True)


@router.post("/rulebooks")
async def parse_and_ingest_rulebooks(
    files: list[UploadFile] = File(...),
    strategy: str = Form("auto"),
    system_version: str = Form("DND_5E_2014"),
    replace: bool = Form(True),
    db: Session = Depends(get_db),
):
    root = Path(tempfile.mkdtemp(prefix="dnd_rulebook_"))
    items, imported = [], 0
    try:
        for index, upload in enumerate(files):
            filename = Path(upload.filename or f"rulebook_{index}").name
            target = root / f"{index:02d}_{filename}"
            total = 0
            with target.open("wb") as output:
                while chunk := await upload.read(1024 * 1024):
                    total += len(chunk)
                    if total > settings.attachment_max_bytes:
                        raise HTTPException(413, f"{filename} exceeds attachment size limit")
                    output.write(chunk)
            parsed = parse_file(str(target), max_chars=2_000_000, strategy=strategy)
            item = {"file": filename, "parser": parsed.get("parser"), "warnings": parsed.get("warnings", [])}
            if not parsed.get("ok") or not str(parsed.get("content", "")).strip():
                item.update({"ok": False, "error": parsed.get("error") or "No text extracted"})
                items.append(item)
                continue
            chunk_count = ingest_rule_content(
                db, parsed["content"], filename, system_version,
                metadata={"original_file": filename, "parser": parsed.get("parser"), "parse_meta": parsed.get("meta", {})},
                replace=replace,
            )
            imported += chunk_count
            item.update({"ok": True, "chunks": chunk_count, "truncated": parsed.get("truncated", False)})
            items.append(item)
        return {
            "ok": all(item["ok"] for item in items),
            "files": len(files),
            "imported_chunks": imported,
            "items": items,
        }
    finally:
        import shutil
        shutil.rmtree(root, ignore_errors=True)

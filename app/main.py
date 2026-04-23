from __future__ import annotations

import asyncio
import io
import logging
import tempfile
import zipfile
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .cleanup import periodic_cleanup
from .config import settings
from .converter import convert_file
from .storage import (
    ConversionRecord,
    cleanup_expired,
    get_record,
    list_records,
    read_markdown,
    save_conversion,
    save_error,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    cleanup_expired()
    task = asyncio.create_task(periodic_cleanup())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="MD Parser", lifespan=lifespan)


def _record_to_json(record: ConversionRecord) -> dict:
    return {
        "id": record.id,
        "originalName": record.original_name,
        "markdownName": record.markdown_name,
        "sizeBytes": record.size_bytes,
        "createdAt": datetime.fromtimestamp(record.created_at, tz=timezone.utc).isoformat(),
        "llmUsed": record.llm_used,
        "status": record.status,
        "error": record.error,
    }


@app.get("/api/config")
async def get_config() -> dict:
    return {
        "maxFileSizeMB": settings.max_file_size_mb,
        "maxFilesPerUpload": settings.max_files_per_upload,
        "retentionHours": settings.retention_hours,
        "llm": {
            "enabled": settings.llm_enabled,
            "modelName": settings.fabrix_model_name if settings.llm_enabled else None,
        },
    }


@app.get("/api/history")
async def history() -> dict:
    records = sorted(list_records(), key=lambda r: r.created_at, reverse=True)
    return {"items": [_record_to_json(r) for r in records]}


@app.post("/api/convert")
async def convert(files: List[UploadFile] = File(...)) -> JSONResponse:
    if not files:
        raise HTTPException(status_code=400, detail="업로드된 파일이 없습니다.")
    if len(files) > settings.max_files_per_upload:
        raise HTTPException(
            status_code=400,
            detail=f"한 번에 최대 {settings.max_files_per_upload}개까지 업로드할 수 있습니다.",
        )

    results = []
    for upload in files:
        original_name = upload.filename or "unnamed"
        try:
            payload = await upload.read()
            if len(payload) == 0:
                raise ValueError("빈 파일입니다.")
            if len(payload) > settings.max_file_size_bytes:
                raise ValueError(
                    f"파일 크기가 {settings.max_file_size_mb}MB 제한을 초과했습니다."
                )

            suffix = Path(original_name).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(payload)
                tmp_path = Path(tmp.name)
            try:
                conversion = convert_file(tmp_path)
            finally:
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

            record = save_conversion(
                original_name=original_name,
                markdown=conversion.markdown,
                llm_used=conversion.llm_used,
            )
            results.append(_record_to_json(record))
        except Exception as exc:
            logger.exception("Conversion failed for %s", original_name)
            record = save_error(original_name=original_name, error=str(exc))
            results.append(_record_to_json(record))

    return JSONResponse({"items": results})


@app.get("/api/preview/{record_id}")
async def preview(record_id: str) -> dict:
    record = get_record(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="기록을 찾을 수 없습니다.")
    if record.status != "ok":
        raise HTTPException(status_code=400, detail="변환에 실패한 항목입니다.")
    return {
        "id": record.id,
        "markdownName": record.markdown_name,
        "markdown": read_markdown(record),
    }


@app.get("/api/download/{record_id}")
async def download(record_id: str):
    record = get_record(record_id)
    if record is None or record.status != "ok":
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
    if not record.markdown_path.exists():
        raise HTTPException(status_code=410, detail="파일이 만료되어 삭제되었습니다.")
    return FileResponse(
        record.markdown_path,
        media_type="text/markdown; charset=utf-8",
        filename=record.markdown_name,
    )


@app.get("/api/download-zip")
async def download_zip(ids: str | None = None):
    records = [r for r in list_records() if r.status == "ok"]
    if ids:
        wanted = {part for part in ids.split(",") if part}
        records = [r for r in records if r.id in wanted]
    records = [r for r in records if r.markdown_path.exists()]
    if not records:
        raise HTTPException(status_code=404, detail="다운로드할 파일이 없습니다.")

    buffer = io.BytesIO()
    seen: dict[str, int] = {}
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for record in records:
            name = record.markdown_name
            if name in seen:
                seen[name] += 1
                stem = Path(name).stem
                suffix = Path(name).suffix
                name = f"{stem} ({seen[name]}){suffix}"
            else:
                seen[name] = 0
            zf.write(record.markdown_path, arcname=name)
    buffer.seek(0)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"markdown-{timestamp}.zip"
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    return HTMLResponse((STATIC_DIR / "index.html").read_text(encoding="utf-8"))


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

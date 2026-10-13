# app.py
import os
import uuid, shutil, time, mimetypes, json
from fastapi import FastAPI, UploadFile, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)  # creates the folder automatically if missing

STATUS_DIR = os.path.join(UPLOAD_DIR, ".meta")  # one JSON per job, survives restarts
os.makedirs(STATUS_DIR, exist_ok=True)

STALE_AFTER = 60  # seconds; a job still "processing" past this is treated as interrupted


app = FastAPI()


def _status_path(job_id: str) -> str:
    return os.path.join(STATUS_DIR, f"{job_id}.json")

def read_status(job_id: str) -> dict:
    # retry: a concurrent write / OneDrive-Defender lock can briefly deny or truncate the file
    for _ in range(5):
        try:
            with open(_status_path(job_id)) as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except (OSError, ValueError):
            time.sleep(0.05)
    return {}

def write_status(job_id: str, **fields):
    data = read_status(job_id)
    data.update(fields)
    blob = json.dumps(data)
    # best-effort: OneDrive sync / Defender on this folder can hold a transient lock;
    # a lost status write self-heals on the next one (~1s later)
    for _ in range(5):
        try:
            with open(_status_path(job_id), "w") as f:
                f.write(blob)
            return
        except OSError:
            time.sleep(0.1)

def process_file(job_id: str, path: str):
    write_status(job_id, status="processing", progress=0)
    try:
        total_steps = 10
        for i in range(total_steps):
            time.sleep(1)  # replace with real file processing
            write_status(job_id, progress=int((i + 1) / total_steps * 100))
        write_status(job_id, status="done", progress=100)
    except Exception as e:
        write_status(job_id, status="failed", error=str(e))
        raise

@app.post("/upload")
async def upload(file: UploadFile, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    path = os.path.join(UPLOAD_DIR, f"{job_id}_{file.filename}")
    # path = f"./uploads/{job_id}_{file.filename}"
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    write_status(job_id, status="queued", progress=0)
    background_tasks.add_task(process_file, job_id, path)
    return {"job_id": job_id}

@app.get("/progress/{job_id}")
async def progress(job_id: str):
    return read_status(job_id) or {"progress": 0, "status": "not_found"}

@app.get("/files")
async def list_files():
    files = []
    for name in os.listdir(UPLOAD_DIR):
        full = os.path.join(UPLOAD_DIR, name)
        if not os.path.isfile(full):
            continue
        job_id, sep, original = name.partition("_")
        stat = os.stat(full)
        info = read_status(job_id) if sep else {}
        status = info.get("status", "unknown")
        # a job left "queued"/"processing" by a killed server is really interrupted
        if status in ("queued", "processing"):
            try:
                if time.time() - os.path.getmtime(_status_path(job_id)) > STALE_AFTER:
                    status = "interrupted"
            except OSError:
                pass
        files.append({
            "job_id": job_id if sep else "",
            "disk_name": name,
            "filename": original if sep else name,
            "size_bytes": stat.st_size,
            "uploaded_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
            "status": status,
            "progress": info.get("progress", 0),
        })
    files.sort(key=lambda f: f["uploaded_at"], reverse=True)
    return {"files": files}

@app.get("/files/{disk_name}")
async def get_file(disk_name: str):
    # guard against path traversal: only allow plain names inside UPLOAD_DIR
    if disk_name != os.path.basename(disk_name):
        raise HTTPException(status_code=400, detail="invalid file name")
    full = os.path.join(UPLOAD_DIR, disk_name)
    if not os.path.isfile(full):
        raise HTTPException(status_code=404, detail="file not found")
    original = disk_name.partition("_")[2] or disk_name
    media_type = mimetypes.guess_type(original)[0] or "application/octet-stream"
    return FileResponse(full, media_type=media_type, filename=original)

@app.delete("/files/{disk_name}")
async def delete_file(disk_name: str):
    # guard against path traversal: only allow plain names inside UPLOAD_DIR
    if disk_name != os.path.basename(disk_name):
        raise HTTPException(status_code=400, detail="invalid file name")
    full = os.path.join(UPLOAD_DIR, disk_name)
    if not os.path.isfile(full):
        raise HTTPException(status_code=404, detail="file not found")
    os.remove(full)
    job_id = disk_name.partition("_")[0]
    try:
        os.remove(_status_path(job_id))
    except OSError:
        pass
    return {"deleted": disk_name}
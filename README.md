# File Uploader

A file-upload dashboard built with Streamlit and a FastAPI backend. Users can upload files, view simulated processing progress, list and delete uploads, and preview or download supported file types.

## Architecture

- **Streamlit frontend:** `streamlit_app.py`, with the file viewer at `pages/viewer.py`.
- **FastAPI backend:** `app.py`, which exposes the upload, progress, list, download, and delete endpoints.
- **Upload storage:** Files and job status JSON are written to the backend's local `uploads/` directory.
- **Processing:** The API currently simulates processing for about 10 seconds using FastAPI background tasks. `celery_app.py` is a separate Celery example and is not used by the current API flow.

## Run locally

Use Python 3.12 and install the dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Start the API in one terminal:

```powershell
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal, point the frontend to the local API and start Streamlit:

```powershell
$env:API_URL = "http://127.0.0.1:8000"
streamlit run streamlit_app.py
```

The dashboard will be available at `http://localhost:8501`. The API can be checked at `http://127.0.0.1:8000/files`; its interactive API documentation is at `http://127.0.0.1:8000/docs`.

## Deploy

The frontend and API are separate services:

1. Deploy `streamlit_app.py` from the repository on [Streamlit Community Cloud](https://share.streamlit.io/). The repository's `requirements.txt` contains the frontend dependencies.
2. Deploy the FastAPI service on [Render](https://render.com/) using the same repository:
   - **Root directory:** leave blank when `app.py` and `requirements-api.txt` are at the repository root.
   - **Build command:** `pip install -r requirements-api.txt`
   - **Start command:** `uvicorn app:app --host 0.0.0.0 --port $PORT`
3. The frontend and viewer both read the `API_URL` environment variable and default to `https://file-uploader-ycgq.onrender.com`. For Streamlit Community Cloud, that default is already the deployed backend URL. If you change backend hosts, update the default in both files and redeploy, or configure `API_URL` in an environment that supports environment variables.
4. Verify the API by opening `<API_URL>/files`. It should return JSON, for example `{"files":[]}`.

Do not point `API_URL` at the Streamlit app URL or at `localhost` in a hosted deployment. `localhost` refers to the machine running the frontend, not the separately deployed API.

## API endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/upload` | Upload a file and receive a job ID. |
| `GET` | `/progress/{job_id}` | Read the job status and progress. |
| `GET` | `/files` | List uploaded files and metadata. |
| `GET` | `/files/{disk_name}` | Download a file. |
| `DELETE` | `/files/{disk_name}` | Delete a file. |

## Deployment notes

- The backend stores uploads on its local filesystem. Files may be lost when the hosting service restarts, redeploys, or replaces its instance. Use persistent storage or object storage if uploads must be retained.
- The API currently has no authentication or authorization. Anyone who can reach it can use its upload, list, download, and delete endpoints. Restrict access or add authentication before using it for private files.
- `uploads/`, the local virtual environment, and Python bytecode are excluded from Git by `.gitignore`.

# pages/viewer.py
import io, mimetypes, os
import streamlit as st, requests, pandas as pd

API = os.environ.get("API_URL", "https://file-uploader-ycgq.onrender.com").rstrip("/")
TEXT_LIMIT = 200_000  # bytes of text to render inline

st.page_link("streamlit_app.py", label="⬅ Back to dashboard")
st.title("File viewer")

disk_name = st.session_state.get("view_file") or st.query_params.get("file")
if not disk_name:
    st.info("Pick a file from the dashboard (👁) to view its content.")
    st.stop()
st.session_state["view_file"] = disk_name  # keep it across reruns on this page


def human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


# --- metadata (reuse the list endpoint) ---
meta = None
try:
    for f in requests.get(f"{API}/files").json()["files"]:
        if f["disk_name"] == disk_name:
            meta = f
            break
except Exception as e:
    st.error(f"Could not reach API at {API}: {e}")
    st.stop()

filename = meta["filename"] if meta else disk_name
if meta:
    st.caption(
        f"{filename} · {human_size(meta['size_bytes'])} · "
        f"{meta['status']} ({meta['progress']}%) · uploaded {meta['uploaded_at']}"
    )

# --- content ---
try:
    r = requests.get(f"{API}/files/{disk_name}")
except Exception as e:
    st.error(f"Could not fetch file: {e}")
    st.stop()

if not r.ok:
    st.error(f"Could not load file: {r.status_code} {r.text}")
    st.stop()

content = r.content
ctype = (r.headers.get("content-type") or "").split(";")[0].strip()
if not ctype or ctype == "application/octet-stream":
    ctype = mimetypes.guess_type(filename)[0] or "application/octet-stream"

st.download_button("Download", content, file_name=filename)
st.divider()

is_csv = ctype == "text/csv" or filename.lower().endswith(".csv")

if ctype == "application/pdf":
    st.pdf(io.BytesIO(content), height=800)
elif ctype.startswith("image/"):
    st.image(content)
elif is_csv:
    try:
        st.dataframe(pd.read_csv(io.BytesIO(content)), use_container_width=True)
    except Exception as e:
        st.warning(f"Could not parse CSV ({e}); showing raw text.")
        st.code(content[:TEXT_LIMIT].decode("utf-8", errors="replace"))
elif ctype.startswith("text/") or ctype in ("application/json", "application/xml"):
    text = content[:TEXT_LIMIT].decode("utf-8", errors="replace")
    st.code(text, language="json" if ctype == "application/json" else None)
    if len(content) > TEXT_LIMIT:
        st.caption(f"Showing first {TEXT_LIMIT:,} of {len(content):,} bytes.")
else:
    st.caption(f"No inline preview for `{ctype}` — use the download button above.")

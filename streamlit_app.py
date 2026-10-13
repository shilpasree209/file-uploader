# streamlit_app.py
import os
import streamlit as st, requests, time

API = os.environ.get("API_URL", "https://file-uploader-ycgq.onrender.com").rstrip("/")

st.title("Upload dashboard")
uploaded = st.file_uploader("Choose a file")

if uploaded is not None and st.session_state.get("uploaded_file_id") != uploaded.file_id:
    resp = requests.post(f"{API}/upload", files={"file": uploaded})
    if resp.ok:
        st.session_state.uploaded_file_id = uploaded.file_id  # don't re-upload on rerun / page nav
        st.session_state.job_id = resp.json()["job_id"]
    else:
        st.error(f"Upload failed: {resp.status_code} {resp.text}")

if "job_id" in st.session_state:
    bar = st.progress(0)
    status = st.empty()
    while True:
        p = requests.get(f"{API}/progress/{st.session_state.job_id}").json()["progress"]
        bar.progress(p)
        status.text(f"{p}%")
        if p >= 100:
            del st.session_state["job_id"]
            break
        time.sleep(1)

st.divider()
st.subheader("Uploaded files")

if st.button("Refresh"):
    st.rerun()


def human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


try:
    files = requests.get(f"{API}/files").json()["files"]
except Exception as e:
    st.error(f"Could not reach API at {API}: {e}")
    files = []

if not files:
    st.info("No files uploaded yet.")
else:
    st.caption(f"{len(files)} file(s)")
    header = st.columns([4, 1.5, 2.5, 2, 1, 1])
    for col, label in zip(header, ["Filename", "Size", "Uploaded", "Status", "", ""]):
        col.markdown(f"**{label}**")
    for f in files:
        c1, c2, c3, c4, c5, c6 = st.columns([4, 1.5, 2.5, 2, 1, 1])
        c1.write(f["filename"])
        c2.write(human_size(f["size_bytes"]))
        c3.write(f["uploaded_at"])
        c4.write(f"{f['status']} ({f['progress']}%)")
        if c5.button("👁", key=f"view_{f['disk_name']}", help="View content"):
            st.session_state["view_file"] = f["disk_name"]
            st.switch_page("pages/viewer.py")
        if c6.button("🗑️", key=f"del_{f['disk_name']}", help="Delete this file"):
            r = requests.delete(f"{API}/files/{f['disk_name']}")
            if r.ok:
                st.toast(f"Deleted {f['filename']}")
                st.rerun()
            else:
                st.error(f"Delete failed: {r.status_code} {r.text}")

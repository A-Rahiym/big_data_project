import os
import streamlit as st
from pathlib import Path
import tempfile
import shutil
import threading
import time
import math

st.title("Kaggle Dataset Downloader")

st.markdown("Upload your `kaggle.json` (Kaggle API credentials). The app will download the specified dataset into `data/raw/`.")

uploaded = st.file_uploader("Upload kaggle.json", type=["json"])

dataset_ref = st.text_input("Kaggle dataset (owner/dataset-name)", value="hmavrodiev/sofia-air-quality-dataset" )

if st.button("Download dataset"):
    if not uploaded:
        st.error("Please upload kaggle.json first.")
    elif not dataset_ref.strip():
        st.error("Please provide a Kaggle dataset reference like 'zynicide/wine-reviews' or 'username/dataset-name'.")
    else:
        # Save kaggle.json to a temp dir and set KAGGLE_CONFIG_DIR
        with tempfile.TemporaryDirectory() as td:
            kaggle_path = os.path.join(td, "kaggle.json")
            with open(kaggle_path, "wb") as f:
                f.write(uploaded.getbuffer())

            # prepare KAGGLE_CONFIG_DIR
            env_dir = os.path.join(td, "kaggle")
            os.makedirs(env_dir, exist_ok=True)
            os.replace(kaggle_path, os.path.join(env_dir, "kaggle.json"))

            st.info("Saved kaggle.json and configured KAGGLE_CONFIG_DIR for the session.")

            # Ensure data/raw exists
            raw_dir = Path("data/raw")
            raw_dir.mkdir(parents=True, exist_ok=True)

            # Use KaggleApi (pure Python) with the provided kaggle.json
            # read credentials and set env vars so Kaggle API can authenticate without writing to user homedir
            try:
                kaggle_bytes = uploaded.getvalue()
                import json as _json
                creds = _json.loads(kaggle_bytes)
                if "username" in creds and "key" in creds:
                    os.environ["KAGGLE_USERNAME"] = creds["username"]
                    os.environ["KAGGLE_KEY"] = creds["key"]
                # also set KAGGLE_CONFIG_DIR for libraries that honor it
                os.environ["KAGGLE_CONFIG_DIR"] = env_dir
            except Exception as e:
                st.error(f"Failed to parse uploaded kaggle.json: {e}")
                creds = None

            # As a fallback, also write the kaggle.json into the user's home .kaggle so
            # libraries that only look there will find it. We avoid printing secrets.
            try:
                home_kaggle_dir = os.path.join(Path.home(), ".kaggle")
                os.makedirs(home_kaggle_dir, exist_ok=True)
                home_kaggle_path = os.path.join(home_kaggle_dir, "kaggle.json")
                # only write if not present to avoid overwriting existing config
                if not os.path.exists(home_kaggle_path):
                    with open(home_kaggle_path, "wb") as hf:
                        hf.write(kaggle_bytes)
                    try:
                        os.chmod(home_kaggle_path, 0o600)
                    except Exception:
                        # chmod may fail on Windows; ignore
                        pass
                # show top-level keys to help debugging structure without exposing secrets
                try:
                    keys = list(creds.keys()) if creds else []
                    if keys:
                        st.info(f"Uploaded kaggle.json keys: {keys}")
                except Exception:
                    pass
            except Exception as e:
                st.warning(f"Could not write fallback kaggle.json to home directory: {e}")

            # import here so kaggle reads env vars or KAGGLE_CONFIG_DIR
            try:
                from kaggle.api.kaggle_api_extended import KaggleApi
            except Exception as e:
                st.error(f"Failed to import Kaggle API client: {e}")
                api = None
            else:
                api = KaggleApi()
            try:
                if api is None:
                    raise RuntimeError("Kaggle API client not available")
                api.authenticate()
            except Exception as e:
                st.error(f"Failed to authenticate with Kaggle API: {e}")
            else:
                # Attempt to get dataset size via metadata (best-effort). If not available, show an indeterminate progress bar.
                total_bytes = None
                try:
                    # Kaggle API doesn't provide a direct dataset size endpoint; try listing files metadata
                    meta = api.dataset_list_files(dataset_ref)
                    if meta and hasattr(meta, 'files'):
                        total_bytes = sum(f.size for f in meta.files if getattr(f, 'size', None) is not None)
                except Exception:
                    total_bytes = None

                progress = st.progress(0)
                status_text = st.empty()

                download_exception = [None]

                def _download():
                    try:
                        api.dataset_download_files(dataset_ref, path=str(raw_dir), unzip=True, quiet=True)
                    except Exception as e:
                        download_exception[0] = e

                thread = threading.Thread(target=_download)
                thread.start()

                last_size = 0
                start_time = time.time()
                while thread.is_alive():
                    # compute bytes downloaded so far
                    size = 0
                    for f in raw_dir.rglob('*'):
                        if f.is_file():
                            try:
                                size += f.stat().st_size
                            except Exception:
                                pass
                    # update progress
                    if total_bytes and total_bytes > 0:
                        pct = min(1.0, size / total_bytes)
                        progress.progress(pct)
                        status_text.text(f"{size:,} bytes downloaded of approx {total_bytes:,} ({math.floor(pct*100)}%)")
                    else:
                        # indeterminate progress: show bytes downloaded
                        status_text.text(f"{size:,} bytes downloaded")
                    last_size = size
                    time.sleep(0.5)

                thread.join()

                if download_exception[0]:
                    st.error(f"Dataset download failed: {download_exception[0]}")
                    try:
                        if raw_dir.exists():
                            shutil.rmtree(raw_dir)
                    except Exception:
                        pass
                else:
                    # final update
                    size = 0
                    for f in raw_dir.rglob('*'):
                        if f.is_file():
                            try:
                                size += f.stat().st_size
                            except Exception:
                                pass
                    if total_bytes and total_bytes > 0:
                        progress.progress(1.0)
                        status_text.text(f"{size:,} bytes downloaded of approx {total_bytes:,} (100%)")
                    else:
                        status_text.text(f"{size:,} bytes downloaded")

                    st.success("Download completed.")
                    files = list(raw_dir.glob("**/*"))
                    files = [f for f in files if f.is_file()]
                    if files:
                        st.markdown("**Downloaded files:**")
                        for f in files:
                            st.write(str(f))

# Big Data Pipeline & Dashboard

This project provides a data pipeline for processing Sofia air quality and weather data, plus a Streamlit dashboard to explore results.

## Project structure

- `run_pipeline.py` — Main script to run the ETL pipeline
- `processing/etl_pipeline.py` — ETL pipeline (PySpark) to transform raw CSVs into partitioned Parquet
- `data/raw/` — Raw CSVs and downloaded datasets
- `data/processed/sofia_air_quality_weather/` — Partitioned Parquet output (year/month)
- `storage/upload_s3.py` — Helper to upload processed files to S3
- `dashboard/app.py` — Streamlit dashboard for visualization
- `dashboard/kaggle_downloader_app.py` — Streamlit helper to download Kaggle datasets

## How to run

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the ETL pipeline locally:

```bash
python run_pipeline.py
```

Start the Streamlit dashboard:

```bash
cd dashboard
python -m streamlit run app.py
```

## Data paths

- Raw data: `data/raw/`
- Processed data: `data/processed/sofia_air_quality_weather/`

## Kaggle dataset & downloader

Use the included Streamlit helper to provide a `kaggle.json` and download the dataset `hmavrodiev/sofia-air-quality-dataset` into `data/raw/`:

```bash
python -m streamlit run dashboard/kaggle_downloader_app.py
```

Alternatively, place `kaggle.json` at `%USERPROFILE%/.kaggle/kaggle.json` (Windows) or `~/.kaggle/kaggle.json` and use the Kaggle CLI:

```bash
kaggle datasets download -d hmavrodiev/sofia-air-quality-dataset -p data/raw --unzip
```

## S3 sync

The dashboard's `sync_data_from_s3()` downloads objects from the configured S3 `bucket_name`/`prefix` into `data/processed/sofia_air_quality_weather/` so the app can read partitioned Parquet. Configure credentials via environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) or `~/.aws/credentials`.

Note: currently `bucket_name`/`prefix` are configured in the dashboard code and the notebook upload cell; consider replacing with env vars or UI inputs.

## Requirements

See `requirements.txt` for required Python packages (pinned versions not set).

## License

MIT License

## Storage and deployment

This project supports multiple storage and deployment options. Choose the option that matches your environment and scale requirements.

- Local filesystem (default, easiest):
	- Raw inputs are stored in `data/raw/` (CSV files, downloaded Kaggle datasets).
	- Processed outputs are written as partitioned Parquet under `data/processed/sofia_air_quality_weather/` with `year` and `month` partitions. This layout is what the dashboard expects.
	- Pros: simple, no cloud credentials required, fast iteration on small data.
	- Cons: not suitable for very large datasets or team sharing.

- AWS S3 (recommended for production or sharing):
	- Use `boto3` to upload processed Parquet files to an S3 bucket. The notebook and `storage/upload_s3.py` include example upload logic.
	- Directory layout on S3 should mirror the local processed path so you can point the dashboard at S3 and preserve partition discovery.
	- Provide AWS credentials via `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` environment variables or configure `~/.aws/credentials`.
	- Pros: scalable storage, easy sharing and integration with AWS analytics tools.
	- Cons: requires AWS account and network access; permissions must be set up correctly.

- Alternative object stores / S3-compatible services:
	- The code uses `boto3` but can work with S3-compatible endpoints by configuring the client (endpoint_url) or swapping in `s3fs` for some notebook workflows.


## Notebook (Colab) instructions — run the pipeline end-to-end

This repository contains `NoteBook.ipynb` that demonstrates a Colab-friendly flow to download the Kaggle dataset, run the PySpark ETL, and optionally upload processed files to S3.

Quick steps (Colab / Jupyter):

1. Open the notebook (`NoteBook.ipynb`) in Colab or Jupyter.
2. Run the dependency install cell to install `pyspark`, `kaggle`, and other utilities. Example cell installs:

```python
!pip install -q pyspark plotly streamlit boto3 kaggle pyarrow s3fs
```

3. Provide Kaggle credentials:
	 - Upload `kaggle.json` using the notebook UI (the notebook sets `KAGGLE_CONFIG_DIR` and authenticates), or manually place `kaggle.json` at `~/.kaggle/kaggle.json`.
4. Run the download cell (uses KaggleApi) to fetch `hmavrodiev/sofia-air-quality-dataset` into `data/raw/`.
5. Run the ETL cell which calls `processing.etl_pipeline.run_etl(input_path='data/raw', output_path='data/processed/sofia_air_quality_weather')`. This runs a local PySpark job and writes partitioned Parquet.
6. (Optional) Run the S3 upload cell: provide `bucket_name` and `prefix` and the cell will upload processed files using `boto3`.

Notes:
- The notebook uses a local PySpark runtime in Colab which may be heavy on resources. For large data or production, prefer a Spark cluster.
- The S3 upload cell uses `boto3` and requires AWS credentials in the environment.


## Alternative: run the pipeline from the command line / Spark cluster

If you prefer not to use the notebook, run the pipeline with the project scripts. Two options:

- Lightweight local run (Python wrapper):

```bash
python run_pipeline.py --input data/raw --output data/processed/sofia_air_quality_weather
```

This runs the ETL using the Python entrypoint in the repo (it will create a SparkSession locally via pyspark). This is suitable for development and small datasets.

- Submit to a Spark cluster (production-scale):

Package the code and submit with `spark-submit` to your cluster. Example:

```bash
spark-submit \
	--master yarn \
	--deploy-mode cluster \
	processing/etl_pipeline.py \
	--input s3a://my-bucket/raw/ \
	--output s3a://my-bucket/processed/sofia_air_quality_weather/
```

Notes for cluster runs:
- Use `s3a://` or your cluster's configured Hadoop filesystem for S3 access. Set AWS credentials either in the cluster configuration or via environment variables where the driver runs.
- Ensure PySpark package versions on the cluster match the `pyspark` version you develop against.

---

If you'd like, I can now:
- Replace hard-coded `bucket_name`/`prefix` in `dashboard/app.py` and the notebook with environment variables and/or UI inputs (recommended), or
- Add a small notebook cell that prompts for `bucket_name` interactively before uploading.

Mark the README update as complete and let me know which follow-up you want next.


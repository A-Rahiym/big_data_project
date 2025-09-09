# Big Data Pipeline & Dashboard

This project provides a data pipeline for processing Sofia air quality and weather data, and a dashboard for visualizing the results.

## Project Structure

- `run_pipeline.py`: Main script to run the ETL pipeline.
- `processing/etl_pipeline.py`: ETL pipeline for processing raw data.
- `data/raw/`: Contains raw CSV data files.
- `data/processed/sofia_air_quality_weather/`: Processed data in partitioned Parquet format.
- `storage/upload_s3.py`: Script to upload processed data to AWS S3.
- `dashboard/app.py`: Streamlit dashboard for data visualization.
- `dashboard/start.bat`: Batch file to start the dashboard.

## How to Run

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the ETL Pipeline

```bash
python run_pipeline.py
```

### 3. Start the Dashboard

```bash
cd dashboard
python -m streamlit run app.py
```

## Data
- Raw data: `data/raw/`
- Processed data: `data/processed/sofia_air_quality_weather/`

## AWS S3 Upload
- Use `storage/upload_s3.py` to upload processed data to S3.

## Requirements
See `requirements.txt` for required Python packages.

## License
MIT License.

---

## Additional setup: Kaggle dataset & S3 sync (expanded)

This project includes a Streamlit helper app `dashboard/kaggle_downloader_app.py` that accepts an uploaded `kaggle.json` and downloads `hmavrodiev/sofia-air-quality-dataset` into `data/raw/`.

Kaggle download options
- Use the Streamlit uploader (recommended): run `python -m streamlit run dashboard/kaggle_downloader_app.py`, upload `kaggle.json` from your Kaggle account and click Download.
- Or place `kaggle.json` at `%USERPROFILE%\\.kaggle\\kaggle.json` (Windows) or `~/.kaggle/kaggle.json` and use the Kaggle CLI:
	```bash
	kaggle datasets download -d hmavrodiev/sofia-air-quality-dataset -p data/raw --unzip
	```

S3 sync details
- The dashboard `sync_data_from_s3()` function downloads objects from the configured S3 `bucket_name` and `prefix` into `data/processed/sofia_air_quality_weather/` so the dashboard can read partitioned parquet.
- Set AWS credentials by environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) or via the AWS CLI credentials file.


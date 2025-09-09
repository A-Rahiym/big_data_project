from processing.etl_pipeline import run_etl
# from storage.upload_s3 import upload_folder

# Run ETL
run_etl(input_path="data/raw", output_path="data/processed")

# Upload to S3
# upload_folder("data/processed", "my-sofia-air-quality", "processed-data")

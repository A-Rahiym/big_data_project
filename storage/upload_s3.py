import boto3 , os

def upload_folder(local_dir, bucket, prefix):
    s3 = boto3.client("s3")
    for root, dirs, files in os.walk(local_dir):
        for file in files:
            local_file = os.path.join(root, file)
            relative_path = os.path.relpath(local_file, local_dir)
            s3_key = f"{prefix}/{relative_path}"
            s3.upload_file(local_file, bucket, s3_key)
            print(f"📤 Uploaded {s3_key} to s3://{bucket}/{s3_key}")

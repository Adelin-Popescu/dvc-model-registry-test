import sys
import yaml

def trace_dvc_file_to_s3(dvc_file):
    with open(dvc_file, 'r') as f:
        data = yaml.safe_load(f)

    try:
        md5_hash = data['outs'][0]['md5']
    except (KeyError, IndexError):
        print("❌ Could not find 'md5' in the DVC file.")
        return

    folder = md5_hash[:2]
    rest = md5_hash[2:]

    s3_path = f"files/md5/{folder}/{rest}"
    print(f"📦 S3 storage path for this file is:\n{s3_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python trace_dvc_file_to_s3.py <file.dvc>")
        sys.exit(1)

    dvc_file_path = sys.argv[1]
    trace_dvc_file_to_s3(dvc_file_path)

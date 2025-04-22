
import os
import yaml
import subprocess
import argparse

def run(cmd):
    print(f"🛠️ Running: {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        raise RuntimeError(f"❌ Command failed: {cmd}")

def load_registry(registry_file="model_registry.yaml"):
    with open(registry_file, "r") as f:
        return yaml.safe_load(f)

def write_dvc_file(folder, hash_val):
    dvc_content = {
        'outs': [{
            'md5': hash_val,
            'path': folder
        }]
    }
    with open(f"{folder}.dvc", "w") as f:
        yaml.dump(dvc_content, f, sort_keys=False)

def check_s3_object_exists(bucket, base_path, md5_hash):
    subdir = md5_hash[:2]
    obj_path = f"{base_path}/files/md5/{subdir}/{md5_hash}"
    s3_uri = f"s3://{bucket}/{obj_path}"
    result = subprocess.run(
        ["aws", "s3", "ls", s3_uri],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL
    )
    return result.returncode == 0

def main(model, version, bucket, s3_path):
    registry = load_registry()

    if model not in registry:
        print(f"❌ Model '{model}' not found.")
        return
    if version not in registry[model]:
        print(f"❌ Version '{version}' not found for model '{model}'.")
        return

    entry = registry[model][version]
    hash_val = entry["hash"] if isinstance(entry, dict) else entry

    print(f"🔁 Switching to version {version} of {model}")
    print(f"📦 Hash: {hash_val}")

    print("🔍 Checking S3 for dataset...")
    if not check_s3_object_exists(bucket, s3_path, hash_val):
        print("⚠️  Data not found on S3. Attempting to push it from local cache...")
        try:
            run(f"dvc push {model}.dvc")
        except RuntimeError:
            print("❌ Could not push missing version to remote. Aborting.")
            return

    write_dvc_file(model, hash_val)

    run(f"rm -rf {model}/")
    run(f"dvc pull {model}.dvc")

    print(f"✅ {model} is now at version {version}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("model", help="Model/folder name (e.g. pose_dataset)")
    parser.add_argument("version", help="Version to restore (e.g. v1.0)")
    parser.add_argument("--bucket", required=True, help="S3 bucket name")
    parser.add_argument("--s3_path", required=True, help="Path inside the S3 bucket (e.g. public/debug/dvc-test)")
    args = parser.parse_args()

    try:
        main(args.model, args.version, args.bucket, args.s3_path)
    except Exception as e:
        print(str(e))

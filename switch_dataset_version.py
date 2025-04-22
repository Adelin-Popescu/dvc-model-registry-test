import yaml
import argparse
import os
import subprocess
import sys

def run(cmd, check=True):
    print(f"🛠️ Running: {cmd}")
    result = subprocess.run(cmd, shell=True)
    if check and result.returncode != 0:
        print(f"❌ Command failed: {cmd}")
        sys.exit(1)
    return result.returncode

def load_registry():
    with open("model_registry.yaml", "r") as f:
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
    base_path = base_path.rstrip("/")  # remove trailing slash if any
    subdir = md5_hash[:2]
    rest = md5_hash[2:]
    s3_uri = f"s3://{bucket}/{base_path}/files/md5/{subdir}/{rest}"
    print(f"🔎 Checking: {s3_uri}")
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
        sys.exit(1)
    if version not in registry[model]:
        print(f"❌ Version '{version}' not found for model '{model}'.")
        sys.exit(1)

    entry = registry[model][version]
    hash_val = entry["hash"] if isinstance(entry, dict) else entry

    print(f"🔁 Switching to version {version} of {model}")
    print(f"📦 Hash: {hash_val}")

    # Check if data is available remotely
    print("🔍 Checking S3 for dataset...")
    if not check_s3_object_exists(bucket, s3_path, hash_val):
        print("❌ Remote S3 data not found. Aborting to avoid data loss.")
        sys.exit(1)

    # Prepare .dvc file for the new version
    write_dvc_file(model, hash_val)

    # Protect current folder
    backup = f"{model}__backup"
    if os.path.exists(model):
        os.rename(model, backup)
        print(f"🛡️  Backed up existing folder to: {backup}")

    # Try to pull
    pull_ok = run(f"dvc pull {model}.dvc", check=False)
    if pull_ok != 0:
        print("❌ Pull failed — restoring previous folder.")
        if os.path.exists(model):
            os.rmdir(model)
        if os.path.exists(backup):
            os.rename(backup, model)
        sys.exit(1)

    # Pull succeeded — clean and checkout
    if os.path.exists(backup):
        run(f"rm -rf {backup}")
    run(f"dvc checkout {model}.dvc")

    print(f"✅ {model} is now at version {version}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("model", help="Model/folder name (e.g. pose_dataset)")
    parser.add_argument("version", help="Version to restore (e.g. v1.0)")
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--s3_path", required=True)
    args = parser.parse_args()

    main(args.model, args.version, args.bucket, args.s3_path)

import yaml
import argparse
import os
import subprocess
import sys

def run(cmd, check=True, env=None):
    print(f"🛠️ Running: {cmd}")
    env = env or os.environ.copy()
    env["DVC_CACHE_VERSION"] = "dir"
    result = subprocess.run(cmd, shell=True, env=env)
    if check and result.returncode != 0:
        print(f"❌ Command failed: {cmd}")
        sys.exit(1)
    return result.returncode

def load_registry():
    with open("model_registry.yaml", "r") as f:
        return yaml.safe_load(f)

def write_dvc_file(folder, hash_val):
    with open(f"{folder}.dvc", "w") as f:
        yaml.dump({
            "outs": [{"md5": hash_val, "path": folder}]
        }, f, sort_keys=False)

def check_s3_object_exists(bucket, s3_base, md5_hash):
    s3_path = f"s3://{bucket}/{s3_base}/files/md5/{md5_hash[:2]}/{md5_hash[2:]}"
    print(f"🔎 Checking: {s3_path}")
    result = subprocess.run(["aws", "s3", "ls", s3_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return result.returncode == 0

def main(model, version, bucket, s3_path):
    registry = load_registry()
    if model not in registry or version not in registry[model]:
        print(f"❌ Model '{model}' or version '{version}' not found in registry.")
        sys.exit(1)

    hash_val = registry[model][version]["hash"]
    print(f"🔁 Switching to version {version} of {model}")
    print(f"📦 Hash: {hash_val}")

    # Check S3
    print("🔍 Checking S3 for dataset...")
    if not check_s3_object_exists(bucket, s3_path, hash_val):
        print("❌ Remote S3 data not found. Aborting.")
        sys.exit(1)

    # Write .dvc file
    write_dvc_file(model, hash_val)

    # Backup
    backup = f"{model}__backup"
    if os.path.exists(model):
        os.rename(model, backup)
        print(f"🛡️  Backed up existing folder to: {backup}")

    # Create temporary remote
    remote_name = f"tempremote_{model}"
    temp_url = f"s3://{bucket}/{s3_path}/files/md5"
    run(f"dvc remote add -f {remote_name} {temp_url}")
    run(f"dvc remote modify {remote_name} region eu-north-1")

    # Pull using temporary remote
    pull_ok = run(f"dvc pull {model}.dvc -v --remote {remote_name}", check=False)

    # Cleanup temp remote
    run(f"dvc remote remove {remote_name}")

    if pull_ok != 0:
        print("❌ Pull failed — restoring previous folder.")
        if os.path.exists(model):
            os.rmdir(model)
        if os.path.exists(backup):
            os.rename(backup, model)
        sys.exit(1)

    if os.path.exists(backup):
        run(f"rm -rf {backup}")

    run(f"dvc checkout {model}.dvc")
    print(f"✅ {model} is now at version {version}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("model")
    parser.add_argument("version")
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--s3_path", required=True)
    args = parser.parse_args()

    main(args.model, args.version, args.bucket, args.s3_path)

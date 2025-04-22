
import argparse
import subprocess
import os
import sys
import yaml
import time
import shutil
from pathlib import Path

def run(cmd, capture_output=False, check=True):
    print(f"🛠️ Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=capture_output)
    if check and result.returncode != 0:
        print(f"❌ Command failed: {cmd}")
        sys.exit(1)
    return result.stdout.decode().strip() if capture_output else ""

def dvc_add(path):
    # Normalize and resolve dvc file path
    norm_path = os.path.normpath(path)
    dvc_file = f"{norm_path}.dvc" if os.path.isfile(path) else f"{os.path.basename(norm_path)}.dvc"

    # Clean state: remove .dvc, .dvc/tmp
    if os.path.exists(dvc_file):
        os.remove(dvc_file)
    if os.path.exists(".dvc/tmp"):
        shutil.rmtree(".dvc/tmp")

    # Trigger a file change
    trigger_path = os.path.join(path, ".dvc_trigger")
    with open(trigger_path, "w") as f:
        f.write(str(time.time()))

    # Add + commit
    run(f"dvc add {path}")
    os.remove(trigger_path)
    run(f"dvc commit {dvc_file}")

    # Parse the new hash
    with open(dvc_file) as f:
        data = yaml.safe_load(f)
        md5 = data['outs'][0]['md5']

    return dvc_file, md5

def verify_local_cache(md5):
    old_path = Path(f".dvc/cache/{md5[:2]}/{md5[2:]}")
    new_path = Path(f".dvc/cache/files/md5/{md5[:2]}/{md5[2:]}")
    if not old_path.exists() and not new_path.exists():
        print(f"❌ DVC cache file missing: {old_path} or {new_path}")
        sys.exit(1)

def git_commit(dvc_file, model_name, version):
    run(f"git add {dvc_file}")
    run(f"git commit -m 'Add {model_name} version {version}'")

def push_to_dvc_and_git(model_name, version, dvc_file, md5, metrics, update_registry, bucket, s3_path):
    if update_registry:
        run("dvc push")
        cmd = f"python3 update_registry.py --model {model_name} --version {version} --file {dvc_file}"
        if metrics:
            cmd += f" --metrics '{metrics}'"
        run(cmd)
        run(f"git add model_registry.yaml {dvc_file}")
        run(f"git commit -m 'Update model registry: {model_name} {version}'")
        run("git push")

def main():
    parser = argparse.ArgumentParser(description="Forceful DVC add and registry update with S3 integrity check.")
    parser.add_argument("--model", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--path", required=True)
    parser.add_argument("--metrics", help="YAML-style string")
    parser.add_argument("--update_registry", action="store_true")
    args = parser.parse_args()

    print(f"📦 Adding {args.path} to DVC...")
    dvc_file, md5 = dvc_add(args.path)

    verify_local_cache(md5)

    print("📚 Committing DVC metadata to Git...")
    git_commit(dvc_file, args.model, args.version)

    print("🗂️ Pushing and updating registry...")
    push_to_dvc_and_git(args.model, args.version, dvc_file, md5, args.metrics, args.update_registry, args.bucket, args.s3_path)

    print("✅ Done!")

if __name__ == "__main__":
    main()

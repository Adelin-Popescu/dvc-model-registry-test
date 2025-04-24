# add_model.py
import argparse
import subprocess
import os
import sys
import yaml
from pathlib import Path


def run(cmd, capture_output=False, check=True):
    print(f"⚒️ Running: {cmd}")
    env = os.environ.copy()
    env["DVC_CACHE_VERSION"] = "dir"
    result = subprocess.run(cmd, shell=True, capture_output=capture_output, env=env)
    if check and result.returncode != 0:
        print(f"❌ Command failed: {cmd}")
        sys.exit(1)
    return result.stdout.decode().strip() if capture_output else ""


def dvc_add(path):
    run(f"dvc add {path}")
    dvc_file = f"{os.path.basename(path.rstrip('/'))}.dvc"
    with open(dvc_file, "r") as f:
        data = yaml.safe_load(f)
        md5 = data["outs"][0]["md5"]
    return dvc_file, md5


def verify_cache(md5):
    dir_cache = Path(f".dvc/cache/files/md5/{md5[:2]}/{md5[2:]}")
    if not dir_cache.exists():
        print(f"❌ DVC cache file not found: {dir_cache}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Add DVC model/dataset version")
    parser.add_argument("--model", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--path", required=True)
    parser.add_argument("--metrics", help="Optional metrics, YAML string")
    parser.add_argument("--update_registry", action="store_true")
    args = parser.parse_args()

    print(f"📦 Adding {args.path} to DVC...")
    dvc_file, md5 = dvc_add(args.path)
    verify_cache(md5)

    print("📚 Committing to Git...")
    run(f"git add {dvc_file} .gitignore")
    run(f"git commit -m 'Add {args.model} version {args.version}'")

    if args.update_registry:
        print("☁️ Pushing to remote and updating registry...")
        run("dvc push")
        cmd = f"python3 update_registry.py --model {args.model} --version {args.version} --file {dvc_file}"
        if args.metrics:
            cmd += f" --metrics '{args.metrics}'"
        run(cmd)
        run("git add model_registry.yaml")
        run(f"git commit -m 'Update registry for {args.model} {args.version}'")
        run("git push")

    print("✅ Done!")


if __name__ == "__main__":
    main()

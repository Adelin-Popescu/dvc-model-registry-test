import argparse
import subprocess
import os
import sys
import yaml

def run(cmd, capture_output=False):
    print(f"🛠️ Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=capture_output)
    if result.returncode != 0:
        print(f"❌ Command failed: {cmd}")
        sys.exit(1)
    return result.stdout.decode().strip() if capture_output else ""

def dvc_add(path):
    # Add file or directory to DVC
    run(f"dvc add {path}")
    # Determine DVC file path
    norm_path = os.path.normpath(path)
    dvc_file = f"{norm_path}.dvc" if os.path.isfile(path) else f"{os.path.basename(norm_path)}.dvc"
    return dvc_file

def git_commit(dvc_file, model_name, version):
    # Stage and commit DVC metadata file
    run(f"git add {dvc_file}")
    run(f"git commit -m 'Add {model_name} version {version}'")

def push_to_dvc_and_git(model_name, version, dvc_file, metrics, update_registry):
    # Optionally update model registry, push to DVC, and commit registry changes
    if update_registry:
        cmd = f"python3 update_registry.py --model {model_name} --version {version} --file {dvc_file}"
        if metrics:
            cmd += f" --metrics '{metrics}'"
        run(cmd)
        run("dvc push")
        run("git add model_registry.yaml")
        run(f"git commit -m 'Update model registry: {model_name} {version}'")
        run("git push")

def main():
    parser = argparse.ArgumentParser(description="Add model or dataset to DVC and optionally update registry.")
    parser.add_argument("--model", required=True, help="Model or dataset name")
    parser.add_argument("--version", required=True, help="Version identifier")
    parser.add_argument("--path", required=True, help="Path to the file or directory to track with DVC")
    parser.add_argument("--metrics", help="Optional metrics in YAML format, e.g. 'accuracy: 0.92, size_mb: 42'")
    parser.add_argument("--update_registry", action="store_true", help="Flag to push and update registry")

    args = parser.parse_args()

    print(f"📦 Adding {args.path} to DVC...")
    dvc_file = dvc_add(args.path)

    print("📚 Committing DVC metadata to Git...")
    git_commit(dvc_file, args.model, args.version)

    print("🗂️ Evaluating registry and remote updates...")
    push_to_dvc_and_git(args.model, args.version, dvc_file, args.metrics, args.update_registry)

    print("✅ Done!")

if __name__ == "__main__":
    main()

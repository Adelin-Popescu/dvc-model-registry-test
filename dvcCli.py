import os
import sys
import yaml
import shutil
from pathlib import Path
from dvc.repo import Repo

REGISTRY_FILE = "model_registry.yaml"
DVC_REMOTE_NAME = os.getenv("DVC_REMOTE", "s3remote")


def load_registry():
    if not Path(REGISTRY_FILE).exists():
        return {}
    with open(REGISTRY_FILE, "r") as f:
        return yaml.safe_load(f) or {}


def save_registry(registry):
    with open(REGISTRY_FILE, "w") as f:
        yaml.dump(registry, f, sort_keys=False)


def add_model_version(model_name: str, version: str):
    repo = Repo(os.getcwd())

    print(f"🔍 Adding model '{model_name}' as version '{version}'")
    repo.add(model_name)

    # Get the hash from the .dvc file
    dvc_file = Path(f"{model_name}.dvc")
    dvc_data = yaml.safe_load(dvc_file.read_text())
    hash_val = dvc_data["outs"][0]["md5"]

    registry = load_registry()
    registry.setdefault(model_name, {})[version] = {
        "hash": hash_val,
        "author": os.getenv("USER", "unknown"),
    }
    save_registry(registry)
    print(f"✅ Added version '{version}' with hash {hash_val}")


def push_model(model_name: str):
    repo = Repo(os.getcwd())
    print(f"📤 Pushing {model_name}.dvc to remote '{DVC_REMOTE_NAME}'")
    repo.push(targets=[f"{model_name}.dvc"], remote=DVC_REMOTE_NAME)


def switch_model_version(model_name: str, version: str):
    registry = load_registry()
    if model_name not in registry or version not in registry[model_name]:
        print(f"❌ Model/version not found in registry")
        return

    print(f"🔁 Switching {model_name} to version {version}")
    hash_val = registry[model_name][version]["hash"]

    # Backup current folder
    if Path(model_name).exists():
        backup = Path(f"{model_name}__backup")
        if backup.exists():
            shutil.rmtree(backup)
        shutil.move(model_name, backup)

    # Write a .dvc file to match this version
    with open(f"{model_name}.dvc", "w") as f:
        yaml.dump({
            "outs": [{
                "md5": hash_val,
                "path": model_name
            }]
        }, f, sort_keys=False)

    repo = Repo(os.getcwd())
    try:
        repo.pull(targets=[f"{model_name}.dvc"], remote=DVC_REMOTE_NAME)
        repo.checkout(targets=[f"{model_name}.dvc"])
        print(f"✅ Switched {model_name} to version {version}")
    except Exception as e:
        print(f"❌ Pull or checkout failed: {e}")
        if Path(model_name).exists():
            shutil.rmtree(model_name)
        if Path(f"{model_name}__backup").exists():
            shutil.move(f"{model_name}__backup", model_name)
        print("🛠️  Restored backup")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")

    add = subparsers.add_parser("add")
    add.add_argument("model")
    add.add_argument("version")

    push = subparsers.add_parser("push")
    push.add_argument("model")

    switch = subparsers.add_parser("switch")
    switch.add_argument("model")
    switch.add_argument("version")

    args = parser.parse_args()

    if args.command == "add":
        add_model_version(args.model, args.version)
    elif args.command == "push":
        push_model(args.model)
    elif args.command == "switch":
        switch_model_version(args.model, args.version)
    else:
        parser.print_help()

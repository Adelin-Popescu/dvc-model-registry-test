import yaml
import argparse
import os
import subprocess

def run(cmd):
    print(f"🛠️ Running: {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print("❌ Command failed.")
        exit(1)

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

def main(model, version):
    registry = load_registry()

    if model not in registry:
        print(f"❌ Model '{model}' not found.")
        return
    if version not in registry[model]:
        print(f"❌ Version '{version}' not found for model '{model}'.")
        return

    hash_val = registry[model][version]['hash'] if isinstance(registry[model][version], dict) else registry[model][version]
    print(f"🔁 Switching to version {version} of {model}")
    print(f"📦 Hash: {hash_val}")

    write_dvc_file(model, hash_val)

    run(f"rm -rf {model}/")  # optional: clean current folder
    run(f"dvc pull {model}.dvc")

    print(f"✅ {model} is now at version {version}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("model", help="Model/folder name (e.g. pose_dataset)")
    parser.add_argument("version", help="Version to restore (e.g. v1.0)")
    args = parser.parse_args()
    main(args.model, args.version)

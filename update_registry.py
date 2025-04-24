# --- update_registry.py ---
import yaml
import argparse
import os
import subprocess
from datetime import datetime, timezone

def extract_hash(dvc_file):
    with open(dvc_file, 'r') as f:
        data = yaml.safe_load(f)
    return data['outs'][0]['md5']

def get_git_author():
    try:
        return subprocess.check_output(["git", "config", "user.name"]).decode().strip()
    except:
        return "unknown"

def update_registry(model, version, dvc_file, metrics, registry_file="model_registry.yaml"):
    hash_val = extract_hash(dvc_file)
    author = get_git_author()
    now = datetime.now(timezone.utc).isoformat()

    if os.path.exists(registry_file):
        with open(registry_file, 'r') as f:
            registry = yaml.safe_load(f) or {}
    else:
        registry = {}

    entry = {
        "hash": hash_val,
        "date": now,
        "author": author
    }
    if metrics:
        try:
            metrics_dict = yaml.safe_load(metrics)
            if isinstance(metrics_dict, dict):
                entry["metrics"] = metrics_dict
        except Exception as e:
            print(f"⚠️ Failed to parse metrics: {e}")

    registry.setdefault(model, {})[version] = entry

    with open(registry_file, 'w') as f:
        yaml.dump(registry, f, sort_keys=False)

    print(f"✅ Registered {model} v{version} with metadata")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--file', required=True)
    parser.add_argument('--metrics', help='YAML-style string, e.g. "accuracy: 0.92"')
    parser.add_argument('--registry', default='model_registry.yaml')
    args = parser.parse_args()
    try:
        update_registry(args.model, args.version, args.file, args.metrics, args.registry)
    except Exception as e:
        print(e)
        sys.exit(1)

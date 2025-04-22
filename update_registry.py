import yaml
import argparse
import os
import sys
import subprocess
from datetime import datetime, timezone


def extract_hash(dvc_file):
    with open(dvc_file, 'r') as f:
        dvc_data = yaml.safe_load(f)

    try:
        md5 = dvc_data['outs'][0]['md5']
        if md5.lower() == "md5" or len(md5) < 10:
            raise ValueError(f"❌ Invalid hash in {dvc_file}: {md5}")
        return md5
    except Exception:
        raise ValueError("❌ Could not find a valid md5 hash in the DVC file.")



def get_git_author():
    try:
        name = subprocess.check_output(["git", "config", "user.name"]).decode().strip()
        return name
    except:
        return "unknown"

def update_registry(model, version, dvc_file, metrics, registry_file="model_registry.yaml"):
    if not os.path.exists(dvc_file):
        raise FileNotFoundError(f"❌ DVC file not found: {dvc_file}")

    hash_val = extract_hash(dvc_file)
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    author = get_git_author()

    # Load current registry
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

    # Add metrics if provided
    if metrics:
        try:
            metrics_dict = yaml.safe_load(metrics)
            if isinstance(metrics_dict, dict):
                entry["metrics"] = metrics_dict
        except Exception as e:
            print(f"⚠️ Failed to parse metrics: {e}")

    # Update model + version entry
    if model not in registry:
        registry[model] = {}
    registry[model][version] = entry

    # Write it back
    with open(registry_file, 'w') as f:
        yaml.dump(registry, f, sort_keys=False)

    print(f"✅ Registered {model} v{version} with metadata")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--file', required=True)
    parser.add_argument('--metrics', help='YAML-style string, e.g. "accuracy: 0.92, size_mb: 42"')
    parser.add_argument('--registry', default='model_registry.yaml')
    args = parser.parse_args()

    try:
        update_registry(args.model, args.version, args.file, args.metrics, args.registry)
    except Exception as e:
        print(e)
        sys.exit(1)

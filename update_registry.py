import yaml
import argparse
import os
import sys

def extract_hash(dvc_file):
    with open(dvc_file, 'r') as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if line.strip().startswith('md5:'):
            return line.strip().split('md5: ')[1]
        if line.strip().startswith('hash:'):
            return line.strip().split('hash: ')[1]
    raise ValueError("Could not find hash (md5 or hash) in the DVC file.")


def update_registry(model, version, dvc_file, registry_file="model_registry.yaml"):
    if not os.path.exists(dvc_file):
        raise FileNotFoundError(f"DVC file not found: {dvc_file}")
    
    hash_val = extract_hash(dvc_file)

    if os.path.exists(registry_file):
        with open(registry_file, 'r') as f:
            registry = yaml.safe_load(f) or {}
    else:
        registry = {}

    if model not in registry:
        registry[model] = {}
    registry[model][version] = hash_val

    with open(registry_file, 'w') as f:
        yaml.dump(registry, f, sort_keys=False)

    print(f"✅ Registered {model} version {version} with hash {hash_val}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--file', required=True)
    parser.add_argument('--registry', default='model_registry.yaml')
    args = parser.parse_args()

    try:
        update_registry(args.model, args.version, args.file, args.registry)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

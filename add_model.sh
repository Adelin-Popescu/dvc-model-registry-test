#!/bin/bash
MODEL_NAME=$1
VERSION=$2
FILE_PATH=$3

if [ -z "$MODEL_NAME" ] || [ -z "$VERSION" ] || [ -z "$FILE_PATH" ]; then
  echo "Usage: ./add_model.sh <model_name> <version> <file_path>"
  exit 1
fi

echo "Adding model to DVC..."
dvc add "$FILE_PATH"

echo "Committing to Git..."
git add "$FILE_PATH.dvc"
git commit -m "Add model $MODEL_NAME version $VERSION"

echo "Updating registry..."
python3 update_registry.py --model "$MODEL_NAME" --version "$VERSION" --file "$FILE_PATH.dvc"

echo "Pushing to DVC remote..."
dvc push

echo "Committing updated registry..."
git add model_registry.yaml
git commit -m "Update model registry: $MODEL_NAME $VERSION"

echo "✅ Done!"

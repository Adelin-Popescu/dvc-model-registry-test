#!/bin/bash

MODEL_NAME=$1
VERSION=$2
FILE_PATH=$3
METRICS=$4  # Optional, e.g. "accuracy: 0.92, size_mb: 42"

if [ -z "$MODEL_NAME" ] || [ -z "$VERSION" ] || [ -z "$FILE_PATH" ]; then
  echo "Usage: ./add_model.sh <model_name> <version> <file_path> [metrics]"
  echo "Example: ./add_model.sh ball_detector v0.4 ball_detector/model.pt \"accuracy: 0.91, size_mb: 42\""
  exit 1
fi

echo "📦 Adding $FILE_PATH to DVC..."
dvc add "$FILE_PATH"

echo "📚 Committing .dvc metadata to Git..."
git add "$FILE_PATH.dvc"
git commit -m "Add model $MODEL_NAME version $VERSION"

echo "🧾 Updating registry..."
if [ -n "$METRICS" ]; then
  python3 update_registry.py --model "$MODEL_NAME" --version "$VERSION" --file "$FILE_PATH.dvc" --metrics "$METRICS"
else
  python3 update_registry.py --model "$MODEL_NAME" --version "$VERSION" --file "$FILE_PATH.dvc"
fi

echo "☁️ Pushing data to DVC remote..."
dvc push

echo "🗃️ Committing updated registry..."
git add model_registry.yaml
git commit -m "Update model registry: $MODEL_NAME $VERSION"

echo "✅ Done!"

#!/bin/bash

# Configuration
SOURCE="install/example_data"
DEST="main/data"

# Check if source exists
if [ ! -d "$SOURCE" ]; then
  echo "Error: Source directory $SOURCE does not exist."
  exit 1
fi

# Copy data if destination doesn't exist
if [ -d "$DEST" ]; then
  echo "Directory $DEST already exists. Skipping copy to avoid overwriting data."
else
  echo "Creating $DEST from $SOURCE..."
  mkdir -p "main"
  cp -r "$SOURCE" "$DEST"
  echo "Setup complete."
fi
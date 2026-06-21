#!/bin/bash

# --------------------------------------------- data ----------------------------------------------
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

# -------------------------------------------- config ---------------------------------------------
SOURCE="install/config_antenna.env.example"
DEST="main/config/config_antenna.env"

# Check if source exists (using -f for file)
if [ ! -f "$SOURCE" ]; then
  echo "Error: Source file $SOURCE does not exist."
  exit 1
fi

# Copy data if destination file doesn't exist
if [ -f "$DEST" ]; then
  echo "File $DEST already exists. Skipping copy."
else
  echo "Creating $DEST from $SOURCE..."
  mkdir -p "main/config"
  cp "$SOURCE" "$DEST"
  echo "Setup complete."
fi

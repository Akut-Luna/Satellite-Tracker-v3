#!/bin/bash

DIRS=("data" "config")

for DIR in "${DIRS[@]}"; do
  SOURCE="install/example_$DIR"
  DEST="main/$DIR"

  if [ ! -d "$SOURCE" ]; then
    echo "Error: Source directory $SOURCE does not exist."
    continue
  fi

  if [ -d "$DEST" ]; then
    echo "Directory $DEST already exists. Skipping copy."
  else
    echo "Creating $DEST from $SOURCE..."
    mkdir -p "main"
    cp -r "$SOURCE" "$DEST"
    echo "$DIR setup complete."
  fi
done
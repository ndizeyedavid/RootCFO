#!/bin/bash

ARCHIVE_DIR="archive"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
ARCHIVE_NAME="reports_$TIMESTAMP.tar.gz"

mkdir -p "$ARCHIVE_DIR"

if ! ls *.csv >/dev/null 2>&1; then
    echo "No CSV reports found."
    exit 0
fi

tar -czf "$ARCHIVE_DIR/$ARCHIVE_NAME" *.csv

if [ $? -eq 0 ]; then
    echo "Reports archived successfully!"
    echo "Archive saved as: $ARCHIVE_DIR/$ARCHIVE_NAME"

else
    echo "Failed to archive reports."
    exit 1
fi

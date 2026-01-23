#!/bin/bash
# generic create_package.sh
PACKAGE_NAME="battery-aggregator"
VERSION="v1.2.0"
OUTPUT_FILE="$PACKAGE_NAME-$VERSION.tar.gz"

echo "Creating package $OUTPUT_FILE..."
tar --exclude=.git --exclude=.gitignore --exclude=create_package.sh --exclude=*.tar.gz -czf "$OUTPUT_FILE" .
echo "Done. You can copy $OUTPUT_FILE to your USB stick for installation."

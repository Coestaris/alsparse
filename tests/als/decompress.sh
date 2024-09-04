#!/bin/bash

# This script decompresses the ALS data files in the current directory.
for file in *.als; do
    echo "Decompressing $file..."
    cat $file | gzip -d > ${file}.xml
done
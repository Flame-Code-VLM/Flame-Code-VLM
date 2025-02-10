#!/bin/bash

if [ -z "$1" ]; then
    echo "Error: Log file path is required."
    echo "Usage: $0 <log_file_path>"
    exit 1
fi
echo "Log file path: $1"

LOG_FILE="$1"

rm -rf $LOG_FILE

exec > >(tee -a "$LOG_FILE") 2>&1

echo "Step 1: Collecting repositories..."
python3 -B data_collect/repo_collector/collect_info.py \
  --language JavaScript \
  --start_date 2024-02-01 \
  --end_date 2024-02-20 \
  --per_page 100 \
  --sleep_time 3 \
  --star 5 \
  --time_range 30 \
  --kw react \
  --output_repo_path data/original_repo &
wait $!
if [ $? -ne 0 ]; then
    echo "Error: collect_info failed."
    exit 1
fi

echo "Step 2: Collecting components..."
python3 -B data_collect/component_collector/distiller/distiller_cls.py \
  --threads 10 \
  --repo_path data/original_repo \
  --output_path data/original_repo_components &
wait $!
if [ $? -ne 0 ]; then
    echo "Error: distiller_cls failed."
    exit 1
fi

echo "Step 3: Extracting images..."
node data_collect/component_collector/distiller/img_distiller.js \
  data/original_repo \
  data/original_repo_components &
wait $!
if [ $? -ne 0 ]; then
    echo "Error: img_distiller failed."
    exit 1
fi

echo "All steps completed."
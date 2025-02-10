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

ROOT_DIR=$(pwd)
DEPENDENCY_OUTPUT_PATH="render_templates/empty/dependencies.json"
SHARED_NODE_MODULES="$ROOT_DIR/render_templates/empty/node_modules"
TARGET_RENDER_TEMPLATE_DIR="$ROOT_DIR/render_templates/linked"
CODE_DIR="data/original_repo_components"
SCREENSHOT_DIR="data/original_repo_components_images"

TARGET_NUM=50

echo "Step 1: Running extractDependencies"
node data_collect/component_collector/renderer/extractDependencies.js $CODE_DIR $DEPENDENCY_OUTPUT_PATH &
wait $!
if [ $? -ne 0 ]; then
    echo "Error: extractDependencies failed."
    exit 1
fi
echo "Step 1 extractDependencies completed"

echo "Step 2: Running install..."
node render_templates/empty/install_all.js &
wait $!
if [ $? -ne 0 ]; then
    echo "Error: install failed."
    exit 1
fi
echo "Step 2 install completed."

echo "Step 3: Starting file copy and creating symbolic links..."
echo "Starting file copy..."
if [ ! -d "$TARGET_RENDER_TEMPLATE_DIR" ]; then
    mkdir "$TARGET_RENDER_TEMPLATE_DIR"
    echo "Directory '$TARGET_RENDER_TEMPLATE_DIR' created."
fi
rm -rf $TARGET_RENDER_TEMPLATE_DIR/*
echo "Removed existing files in $TARGET_RENDER_TEMPLATE_DIR."
seq 1 $TARGET_NUM | xargs -I {} -P 128 cp -r $ROOT_DIR/render_templates/template "$TARGET_RENDER_TEMPLATE_DIR/t-{}" &
wait $!
echo "File copy completed."

for i in $(seq 1 $TARGET_NUM); do
    PROJECT_DIR="$TARGET_RENDER_TEMPLATE_DIR/t-$i"

    if [ -d "$PROJECT_DIR" ]; then
        echo "Processing $PROJECT_DIR..."

        if [ -d "$PROJECT_DIR/node_modules" ]; then
            rm -rf "$PROJECT_DIR/node_modules"
            echo "Deleted existing node_modules in $PROJECT_DIR."
        fi

        ln -s "$SHARED_NODE_MODULES" "$PROJECT_DIR/node_modules" &
        wait $!
        echo "Created symbolic link for node_modules in $PROJECT_DIR."
    else
        echo "Directory $PROJECT_DIR does not exist, skipping..."
    fi
done

echo "Step 3 completed."

echo "Step 4: Running render..."
node --max-old-space-size=20480 data_collect/component_collector/renderer/render_gen_cls.js $TARGET_NUM $CODE_DIR $TARGET_RENDER_TEMPLATE_DIR $SCREENSHOT_DIR &
wait $!
if [ $? -ne 0 ]; then
    echo "Error: render failed."
    exit 1
fi
echo "Step 4 render completed."

echo "Completed processing for MODEL_NAME: $MODEL_NAME"

echo "All done!"

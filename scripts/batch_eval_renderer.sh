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
TARGET_DIR="$ROOT_DIR/render_templates/linked"
GEN_CODE_DIR="<DIR_OF_GENERATED_CODE>"
SCREENSHOT_DIR="<DIR_TO_SAVE_SCREENSHOTS>"

TARGET_NUM=50

MODEL_NAMES=(
    "<NAMES_OF_MODELS_TO_EVALUATE>"
)

for MODEL_NAME in "${MODEL_NAMES[@]}"; do
    echo "Processing model: $MODEL_NAME"

    echo "Step 1: Running extractDependencies for $MODEL_NAME..."
    node evaluator/gen_v2/extractDependencies.js $MODEL_NAME $GEN_CODE_DIR $DEPENDENCY_OUTPUT_PATH &
    wait $!
    if [ $? -ne 0 ]; then
        echo "Error: extractDependencies failed for $MODEL_NAME."
        exit 1
    fi
    echo "Step 1 extractDependencies completed for $MODEL_NAME."

    echo "Step 2: Running install for $MODEL_NAME..."
    node render_templates/empty/install_all.js &
    wait $!
    if [ $? -ne 0 ]; then
        echo "Error: install failed for $MODEL_NAME."
        exit 1
    fi
    echo "Step 2 install completed for $MODEL_NAME."

    echo "Step 3: Starting file copy and creating symbolic links for $MODEL_NAME..."

    echo "Starting file copy for $MODEL_NAME..."
    rm -rf $TARGET_DIR/*
    echo "Removed existing files in $TARGET_DIR."
    seq 1 $TARGET_NUM | xargs -I {} -P 128 cp -r $ROOT_DIR/render_templates/template "$TARGET_DIR/t-{}" &
    wait $!
    echo "File copy completed for $MODEL_NAME."

    for i in $(seq 1 $TARGET_NUM); do
        PROJECT_DIR="$TARGET_DIR/t-$i"

        if [ -d "$PROJECT_DIR" ]; then
            echo "Processing $PROJECT_DIR for $MODEL_NAME..."

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

    echo "Step 3 completed for $MODEL_NAME."

    echo "Step 4: Running render for $MODEL_NAME..."
    node --max-old-space-size=20480 evaluator/gen_code_renderer/render_gen_cls.js $ROOT_DIR $MODEL_NAME $TARGET_NUM $GEN_CODE_DIR $SCREENSHOT_DIR &
    wait $!
    if [ $? -ne 0 ]; then
        echo "Error: render failed for $MODEL_NAME."
        exit 1
    fi
    echo "Step 4 render completed for $MODEL_NAME."

    echo "Completed processing for MODEL_NAME: $MODEL_NAME"
done

echo "All done!"

#!/bin/bash 
# 首先取消任何可能影响conda环境的变量 
source activate /root/nfs/envs/llavanext
conda activate /root/nfs/envs/llavanext
export PYTHONPATH="/root/nfs/LLM4CodeBeta/LLaVA-NeXT-FLAME:$PYTHONPATH"

# Function to get the first available GPU
get_first_available_gpu() {
    nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits | awk '$2 < 1000 {print $1; exit}' | tr -d '\n\r,'
}

# Function to wait for a free GPU
wait_for_free_gpu() {
    while true; do
        gpu_id=$(get_first_available_gpu)
        if [[ "$gpu_id" =~ ^[0-9]+$ ]]; then
            echo "Debug: Selected GPU ID: '$gpu_id'" >&2
            echo "$gpu_id"
            return
        else
            echo "No GPUs available. Waiting for 60 seconds..." >&2
            sleep 60
        fi
    done
}

GPU_ID=$(wait_for_free_gpu)
OUTPUT_DIR="/root/nfs3/flame_ft/gen_res"
LOG_DIR="/root/nfs3/flame_ft/eval_logs"
MODEL_PATH="Directory_To_Your_Model"
TEST_DATA_PATH="Directory_To_Your_Testing_Data/testData.jsonl" 
TEST_DATA_IMG_PATH="Directory_To_Your_Testing_Data/images"
OUTPUT_FILE="Directory_To_Your_Output"
PROMPT_VER="v3"
DOSAMPLE=True
MAX_NEW_TOKENS=4096
BATCH_SIZE=4

nohup bash -c "
    python /root/nfs/LLM4CodeBeta/LLaVA-NeXT-FLAME/scripts/eval/eval_flame.py \
        --model_path $MODEL_PATH \
        --output_file $OUTPUT_FILE \
        --gpu_id ${GPU_ID} \
        --test_data_path $TEST_DATA_PATH \
        --test_data_img_path $TEST_DATA_IMG_PATH \
        --batch_size $BATCH_SIZE \
        --do_sample ${DOSAMPLE} \
        --prompt_ver $PROMPT_VER \
        --max_new_tokens ${MAX_NEW_TOKENS} \
        --pen 1.05
"
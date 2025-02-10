#!/bin/bash
# This shell script is for training on AI Studio
source activate
conda activate /root/nfs/envs/llavanext
export PYTHONPATH="/root/nfs/LLaVA-NeXT-FLAME:$PYTHONPATH"

export NCCL_SOCKET_IFNAME=eth0
export NCCL_IB_GID_INDEX=3
export NCCL_IB_DISABLE=0
export NCCL_IB_HCA=mlx5_bond_0,mlx5_bond_1,mlx5_bond_2,mlx5_bond_3,mlx5_bond_4,mlx5_bond_5,mlx5_bond_6,mlx5_bond_7
export NCCL_NET_GDR_LEVEL=2
export NCCL_IB_QPS_PER_CONNECTION=4
export NCCL_IB_TC=160
export NCCL_IB_TIMEOUT=22

MASTER_IP=$(cat /etc/aistudio/masteraddr)
export MASTER_ADDR=$MASTER_IP   
export WORLD_SIZE=$WORLD_SIZE
export NODE_RANK=$RANK
export NNODES=$WORLD_SIZE
export GPU_PER_NODE=8
export NCCL_DEBUG=INFO
nodenum=3

PROMPT_VERSION="v0" 
VISION_MODEL_VERSION="google/siglip-so400m-patch14-384"
LLM_VERSION="deepseek-ai/deepseek-coder-6.7b-instruct" 

NUM_EPOCH=2
MODEL_PATH=/root/nfs/models/DeepSeek_Models/${LLM_VERSION}
DEEPSPPED_CONFIG=/root/nfs/LLaVA-NeXT-FLAME/scripts/zero1.json
DATA_FOLDER=Directory_To_Your_Data
IMAGE_FOLDER=Directory_To_Your_Data_Image
LAYER_NUM=-1
PROJECTOR_TYPE="mlp2x_gelu"
DATA_PATH=/root/nfs2/flame_ft/datasets/${DATA_FOLDER}/inst_data.jsonl
IMAGE_PATH=/root/nfs2/flame_ft/datasets/${IMAGE_FOLDER}/
PROJECTOR_PATH=/root/nfs3/flame_ft/checkpoints/projectors/
VISION_TOWER_PATH=/root/nfs/models/${VISION_MODEL_VERSION}
OUTPUT_FILE=Drirectory_To_Your_Output_File
RECIPE="v9"    #
RUN_NAME="flame_stage2"

# v0: instruction + image => css + js/ts
# v1: instruction + layout desc + image   ==> css + js/ts
# v2: instruction + image ==> layout desc + css + js/ts
# v3: layout desc + image  ==> css + js/ts
# v4: css + js/ts + image ==> layout desc
# v5: image ==> layout desc + css + js/ts
# v6: image ==> css + js/ts
# v7: image ==> layout desc
# v8: image ==> instruction
# v9: image ==> instruction + layout desc

ACCELERATE_CPU_AFFINITY=1 torchrun --nproc_per_node 8 --nnodes $nodenum --master_addr $MASTER_ADDR --node_rank $NODE_RANK --master_port 14545 \
    /root/nfs/LLM4CodeBeta/LLaVA-NeXT-FLAME/llava/train/train_mem.py \
    --deepspeed ${DEEPSPPED_CONFIG} \
    --model_name_or_path ${MODEL_PATH} \
    --version ${PROMPT_VERSION} \
    --data_path="${DATA_PATH}${DATA_NAME}" \
    --image_folder ${IMAGE_PATH} \
    --pretrain_mm_mlp_adapter="${PROJECTOR_PATH}/mm_projector.bin" \
    --mm_tunable_parts="mm_vision_tower,mm_mlp_adapter" \
    --mm_vision_select_layer ${LAYER_NUM} \
    --mm_projector_type ${PROJECTOR_TYPE} \
    --sft_tasks ${RECIPE} \
    --mm_vision_tower_lr=2e-6 \
    --vision_tower ${VISION_TOWER_PATH} \
    --mm_use_im_start_end False \
    --mm_use_im_patch_token False \
    --group_by_modality_length True \
    --image_aspect_ratio anyres_max_9 \
    --image_grid_pinpoints "(1x1),...,(6x6)" \
    --mm_patch_merge_type spatial_unpad \
    --bf16 True \
    --run_name $RUN_NAME \
    --output_dir ${OUTPUT_FILE} \
    --num_train_epochs ${NUM_EPOCH} \
    --per_device_train_batch_size 2 \
    --per_device_eval_batch_size 4 \
    --gradient_accumulation_steps 32 \
    --evaluation_strategy "no" \
    --save_strategy "steps" \
    --save_steps 1000 \
    --save_total_limit 1 \
    --learning_rate 2.5e-5 \
    --weight_decay 0. \
    --warmup_ratio 0.03 \
    --lr_scheduler_type "cosine" \
    --logging_steps 1 \
    --tf32 False \
    --model_max_length 16384 \
    --gradient_checkpointing True \
    --dataloader_num_workers 16 \
    --lazy_preprocess True \
    --report_to none \
    --torch_compile True \
    --torch_compile_backend "inductor" \
    --dataloader_drop_last True \
    --attn_implementation sdpa

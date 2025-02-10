#!/bin/bash
# source activate 2>&1 | tee -a "$LOG_FILE"

# This shell script is for training on AI Studio
source activate
conda activate /root/nfs/envs/llavanext
 
export PYTHONPATH="/root/nfs/LLM4CodeBeta/LLaVA-NeXT-FLAME:$PYTHONPATH"

# NUM_GPUS=8
# NNODES=1
# RANK=0
# ADDR='localhost'
# PORT=29501

export NCCL_SOCKET_IFNAME=eth0
export NCCL_IB_GID_INDEX=3
export NCCL_IB_DISABLE=0
export NCCL_IB_HCA=mlx5_bond_0,mlx5_bond_1,mlx5_bond_2,mlx5_bond_3,mlx5_bond_4,mlx5_bond_5,mlx5_bond_6,mlx5_bond_7
export NCCL_NET_GDR_LEVEL=2
export NCCL_IB_QPS_PER_CONNECTION=4
export NCCL_IB_TC=160
export NCCL_IB_TIMEOUT=22

# export NCCL_DEBUG=INFO
MASTER_IP=$(cat /etc/aistudio/masteraddr)
export MASTER_ADDR=$MASTER_IP   
export WORLD_SIZE=$WORLD_SIZE
export NODE_RANK=$RANK
export NNODES=$WORLD_SIZE
export GPU_PER_NODE=8
export NCCL_DEBUG=INFO
nodenum=3

# ############### Pretrain ################
PROMPT_VERSION="v0" 

VISION_MODEL_VERSION="google/siglip-so400m-patch14-384"
LLM_VERSION="deepseek-ai/deepseek-coder-6.7b-instruct" 

NUM_EPOCH=2

MODEL_PATH=/root/nfs/models/DeepSeek_Models/${LLM_VERSION}
DEEPSPPED_CONFIG=/root/nfs/LLM4CodeBeta/LLaVA-NeXT-FLAME/scripts/zero1.json 
DATA_FOLDER=data_1220/no_code_v1
DATA_FOLDER_CLEAN=data_1220_no_code_v1
IMAGE_FOLDER=data_1220/no_code_v1/inst_178k/ori_images
LAYER_NUM=-1
PROJECTOR_TYPE="mlp2x_gelu"
DATA_PATH=/root/nfs2/flame_ft/datasets/${DATA_FOLDER}/
IMAGE_PATH=/root/nfs2/flame_ft/datasets/${IMAGE_FOLDER}/
PROJECTOR_PATH=/root/nfs3/flame_ft/checkpoints/projectors/
VISION_TOWER_PATH=/root/nfs/LLM4CodeBeta/FLAME_MD/models/${VISION_MODEL_VERSION}

BASE_PROJECTOR=("flame-google_siglip-so400m-patch14-384-deepseek-ai_deepseek-coder-6.7b-instruct-mlp2x_gelu-selectlayer-1-onevision-1-pretrain_mmcoder-3NODE-Date1212" 
"flame-google_siglip-so400m-patch14-384-deepseek-ai_deepseek-coder-6.7b-instruct-mlp2x_res2x_gelu-selectlayer-1-onevision-1-pretrain_mmcoder-3NODE-Date1212" ) 
 
DATA_POOL=("inst_data")

# RECIPE_POOL=("v0" "v1" "v2" "v3" "v5" "v6" "v5_v6" "v5_v6_v7_v8_v9" "v3_v4_v5_v6_v7_v8_v9" "v0_v1_v2_v3_v4_v5_v6_v7_v8_v9" "v0_v1_v2" "v5_v6_v7_v8_v9")

RECIPE_POOL=("v0" "v6" "v0_v1_v6" "v5_v6")    #

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

# for BASE_RUN_NAME in "${BASE_PROJECTOR[@]}"; do
#     for DATA_NAME in "${DATA_POOL[@]}"; do
#         for RECIPE in "${RECIPE_POOL[@]}"; do
#             MID_RUN_NAME=${BASE_RUN_NAME}-FINETUNE-${NUM_EPOCH}-${DATA_FOLDER}-${DATA_NAME}-${RECIPE}-eos-16k-1223

#             LOG_FILE="/root/nfs3/flame_ft/logs/run_${MID_RUN_NAME}_$(date +%Y%m%d_%H%M%S).log"

#             ACCELERATE_CPU_AFFINITY=1 torchrun --nproc_per_node 8 --nnodes $nodenum --master_addr $MASTER_ADDR --node_rank $NODE_RANK --master_port 14545 \
#                 /root/nfs/LLM4CodeBeta/LLaVA-NeXT-FLAME/llava/train/train_mem.py \
#                 --deepspeed ${DEEPSPPED_CONFIG} \
#                 --model_name_or_path ${MODEL_PATH} \
#                 --version ${PROMPT_VERSION} \
#                 --data_path="${DATA_PATH}${DATA_NAME}.jsonl" \
#                 --image_folder ${IMAGE_PATH} \
#                 --pretrain_mm_mlp_adapter="${PROJECTOR_PATH}${BASE_RUN_NAME}/mm_projector.bin" \
#                 --mm_tunable_parts="mm_vision_tower,mm_mlp_adapter,mm_language_model" \
#                 --mm_vision_select_layer ${LAYER_NUM} \
#                 --mm_projector_type ${PROJECTOR_TYPE} \
#                 --sft_tasks ${RECIPE} \
#                 --mm_vision_tower_lr=2e-6 \
#                 --vision_tower ${VISION_TOWER_PATH} \
#                 --mm_use_im_start_end False \
#                 --mm_use_im_patch_token False \
#                 --group_by_modality_length True \
#                 --image_aspect_ratio anyres_max_9 \
#                 --image_grid_pinpoints "(1x1),...,(6x6)" \
#                 --mm_patch_merge_type spatial_unpad \
#                 --bf16 True \
#                 --run_name $MID_RUN_NAME \
#                 --output_dir "/root/nfs3/flame_ft/res/checkpoints/${MID_RUN_NAME}" \
#                 --num_train_epochs ${NUM_EPOCH} \
#                 --per_device_train_batch_size 2 \
#                 --per_device_eval_batch_size 4 \
#                 --gradient_accumulation_steps 32 \
#                 --evaluation_strategy "no" \
#                 --save_strategy "steps" \
#                 --save_steps 1000 \
#                 --save_total_limit 1 \
#                 --learning_rate 2.5e-5 \
#                 --weight_decay 0. \
#                 --warmup_ratio 0.03 \
#                 --lr_scheduler_type "cosine" \
#                 --logging_steps 1 \
#                 --tf32 False \
#                 --model_max_length 16384 \
#                 --gradient_checkpointing True \
#                 --dataloader_num_workers 16 \
#                 --lazy_preprocess True \
#                 --report_to none \
#                 --torch_compile True \
#                 --torch_compile_backend "inductor" \
#                 --dataloader_drop_last True \
#                 --attn_implementation sdpa | tee -a "$LOG_FILE"
#         done
#     done
# done

# # You can delete the sdpa attn_implementation if you want to use flash attn


RECIPE_POOL=("v6" "v5_v6" "v0_v1_v6" "v0" )
RECIPE_POOL=("v3" )
LAYER_NUM=-2
NUM_EPOCH=2
BASE_PROJECTOR=("flame-google_siglip-so400m-patch14-384-deepseek-ai_deepseek-coder-6.7b-instruct-mlp2x_gelu-selectlayer-2-onevision-1-pretrain_mmcoder-3NODE-Date1212" ) 

# "flame-google_siglip-so400m-patch14-384-deepseek-ai_deepseek-coder-6.7b-instruct-mlp2x_res2x_gelu-selectlayer-2-onevision-1-pretrain_mmcoder-3NODE-Date1212"
for BASE_RUN_NAME in "${BASE_PROJECTOR[@]}"; do
    for DATA_NAME in "${DATA_POOL[@]}"; do
        for RECIPE in "${RECIPE_POOL[@]}"; do
            MID_RUN_NAME=${BASE_RUN_NAME}-FINETUNE-${NUM_EPOCH}-${DATA_FOLDER}-${DATA_NAME}-${RECIPE}-eos-16k-1223

            LOG_FILE="/root/nfs3/flame_ft/logs/run_${MID_RUN_NAME}_$(date +%Y%m%d_%H%M%S).log"

            ACCELERATE_CPU_AFFINITY=1 torchrun --nproc_per_node 8 --nnodes $nodenum --master_addr $MASTER_ADDR --node_rank $NODE_RANK --master_port 14545 \
                /root/nfs/LLM4CodeBeta/LLaVA-NeXT-FLAME/llava/train/train_mem.py \
                --deepspeed ${DEEPSPPED_CONFIG} \
                --model_name_or_path ${MODEL_PATH} \
                --version ${PROMPT_VERSION} \
                --data_path="${DATA_PATH}${DATA_NAME}.jsonl" \
                --image_folder ${IMAGE_PATH} \
                --pretrain_mm_mlp_adapter="${PROJECTOR_PATH}${BASE_RUN_NAME}/mm_projector.bin" \
                --mm_tunable_parts="mm_vision_tower,mm_mlp_adapter,mm_language_model" \
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
                --run_name $MID_RUN_NAME \
                --output_dir "/root/nfs3/flame_ft/res/checkpoints/${MID_RUN_NAME}" \
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
                --attn_implementation sdpa | tee -a "$LOG_FILE"
        done
    done
done

# # # You can delete the sdpa attn_implementation if you want to use flash attn



# NUM_EPOCH=3

# LAYER_NUM=-1
# BASE_PROJECTOR=("flame-google_siglip-so400m-patch14-384-deepseek-ai_deepseek-coder-6.7b-instruct-mlp2x_gelu-selectlayer-1-onevision-1-pretrain_mmcoder-3NODE-Date1212" 
# "flame-google_siglip-so400m-patch14-384-deepseek-ai_deepseek-coder-6.7b-instruct-mlp2x_res2x_gelu-selectlayer-1-onevision-1-pretrain_mmcoder-3NODE-Date1212" ) 
 
# for BASE_RUN_NAME in "${BASE_PROJECTOR[@]}"; do
#     for DATA_NAME in "${DATA_POOL[@]}"; do
#         for RECIPE in "${RECIPE_POOL[@]}"; do
#             MID_RUN_NAME=${BASE_RUN_NAME}-FINETUNE-${NUM_EPOCH}-${DATA_FOLDER}-${DATA_NAME}-${RECIPE}-eos-16k-1223

#             LOG_FILE="/root/nfs3/flame_ft/logs/run_${MID_RUN_NAME}_$(date +%Y%m%d_%H%M%S).log"

#             ACCELERATE_CPU_AFFINITY=1 torchrun --nproc_per_node 8 --nnodes $nodenum --master_addr $MASTER_ADDR --node_rank $NODE_RANK --master_port 14545 \
#                 /root/nfs/LLM4CodeBeta/LLaVA-NeXT-FLAME/llava/train/train_mem.py \
#                 --deepspeed ${DEEPSPPED_CONFIG} \
#                 --model_name_or_path ${MODEL_PATH} \
#                 --version ${PROMPT_VERSION} \
#                 --data_path="${DATA_PATH}${DATA_NAME}.jsonl" \
#                 --image_folder ${IMAGE_PATH} \
#                 --pretrain_mm_mlp_adapter="${PROJECTOR_PATH}${BASE_RUN_NAME}/mm_projector.bin" \
#                 --mm_tunable_parts="mm_vision_tower,mm_mlp_adapter,mm_language_model" \
#                 --mm_vision_select_layer ${LAYER_NUM} \
#                 --mm_projector_type ${PROJECTOR_TYPE} \
#                 --sft_tasks ${RECIPE} \
#                 --mm_vision_tower_lr=2e-6 \
#                 --vision_tower ${VISION_TOWER_PATH} \
#                 --mm_use_im_start_end False \
#                 --mm_use_im_patch_token False \
#                 --group_by_modality_length True \
#                 --image_aspect_ratio anyres_max_9 \
#                 --image_grid_pinpoints "(1x1),...,(6x6)" \
#                 --mm_patch_merge_type spatial_unpad \
#                 --bf16 True \
#                 --run_name $MID_RUN_NAME \
#                 --output_dir "/root/nfs3/flame_ft/res/checkpoints/${MID_RUN_NAME}" \
#                 --num_train_epochs ${NUM_EPOCH} \
#                 --per_device_train_batch_size 2 \
#                 --per_device_eval_batch_size 4 \
#                 --gradient_accumulation_steps 32 \
#                 --evaluation_strategy "no" \
#                 --save_strategy "steps" \
#                 --save_steps 1000 \
#                 --save_total_limit 1 \
#                 --learning_rate 2.5e-5 \
#                 --weight_decay 0. \
#                 --warmup_ratio 0.03 \
#                 --lr_scheduler_type "cosine" \
#                 --logging_steps 1 \
#                 --tf32 False \
#                 --model_max_length 16384 \
#                 --gradient_checkpointing True \
#                 --dataloader_num_workers 16 \
#                 --lazy_preprocess True \
#                 --report_to none \
#                 --torch_compile True \
#                 --torch_compile_backend "inductor" \
#                 --dataloader_drop_last True \
#                 --attn_implementation sdpa | tee -a "$LOG_FILE"
#         done
#     done
# done

# # # You can delete the sdpa attn_implementation if you want to use flash attn


# LAYER_NUM=-2
# BASE_PROJECTOR=("flame-google_siglip-so400m-patch14-384-deepseek-ai_deepseek-coder-6.7b-instruct-mlp2x_gelu-selectlayer-2-onevision-1-pretrain_mmcoder-3NODE-Date1212" 
# "flame-google_siglip-so400m-patch14-384-deepseek-ai_deepseek-coder-6.7b-instruct-mlp2x_res2x_gelu-selectlayer-2-onevision-1-pretrain_mmcoder-3NODE-Date1212") 

# for BASE_RUN_NAME in "${BASE_PROJECTOR[@]}"; do
#     for DATA_NAME in "${DATA_POOL[@]}"; do
#         for RECIPE in "${RECIPE_POOL[@]}"; do
#             MID_RUN_NAME=${BASE_RUN_NAME}-FINETUNE-${NUM_EPOCH}-${DATA_FOLDER}-${DATA_NAME}-${RECIPE}-eos-16k-1223

#             LOG_FILE="/root/nfs3/flame_ft/logs/run_$(MID_RUN_NAME)_$(date +%Y%m%d_%H%M%S).log"

#             ACCELERATE_CPU_AFFINITY=1 torchrun --nproc_per_node 8 --nnodes $nodenum --master_addr $MASTER_ADDR --node_rank $NODE_RANK --master_port 14545 \
#                 /root/nfs/LLM4CodeBeta/LLaVA-NeXT-FLAME/llava/train/train_mem.py \
#                 --deepspeed ${DEEPSPPED_CONFIG} \
#                 --model_name_or_path ${MODEL_PATH} \
#                 --version ${PROMPT_VERSION} \
#                 --data_path="${DATA_PATH}${DATA_NAME}.jsonl" \
#                 --image_folder ${IMAGE_PATH} \
#                 --pretrain_mm_mlp_adapter="${PROJECTOR_PATH}${BASE_RUN_NAME}/mm_projector.bin" \
#                 --mm_tunable_parts="mm_vision_tower,mm_mlp_adapter,mm_language_model" \
#                 --mm_vision_select_layer ${LAYER_NUM} \
#                 --mm_projector_type ${PROJECTOR_TYPE} \
#                 --sft_tasks ${RECIPE} \
#                 --mm_vision_tower_lr=2e-6 \
#                 --vision_tower ${VISION_TOWER_PATH} \
#                 --mm_use_im_start_end False \
#                 --mm_use_im_patch_token False \
#                 --group_by_modality_length True \
#                 --image_aspect_ratio anyres_max_9 \
#                 --image_grid_pinpoints "(1x1),...,(6x6)" \
#                 --mm_patch_merge_type spatial_unpad \
#                 --bf16 True \
#                 --run_name $MID_RUN_NAME \
#                 --output_dir "/root/nfs3/flame_ft/res/checkpoints/${MID_RUN_NAME}" \
#                 --num_train_epochs ${NUM_EPOCH} \
#                 --per_device_train_batch_size 2 \
#                 --per_device_eval_batch_size 4 \
#                 --gradient_accumulation_steps 32 \
#                 --evaluation_strategy "no" \
#                 --save_strategy "steps" \
#                 --save_steps 1000 \
#                 --save_total_limit 1 \
#                 --learning_rate 2.5e-5 \
#                 --weight_decay 0. \
#                 --warmup_ratio 0.03 \
#                 --lr_scheduler_type "cosine" \
#                 --logging_steps 1 \
#                 --tf32 False \
#                 --model_max_length 16384 \
#                 --gradient_checkpointing True \
#                 --dataloader_num_workers 16 \
#                 --lazy_preprocess True \
#                 --report_to none \
#                 --torch_compile True \
#                 --torch_compile_backend "inductor" \
#                 --dataloader_drop_last True \
#                 --attn_implementation sdpa | tee -a "$LOG_FILE"
#         done
#     done
# done

# # # You can delete the sdpa attn_implementation if you want to use flash attn

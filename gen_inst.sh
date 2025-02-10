#!/bin/bash
INST_PATH='<PATH_TO_SAVE_INSTANCES>'

nohup python -B -u data_collect/component_collector/describer/gen_inst.py \
  --screenshot_path '<DIR_OF_GENERATED_SCREENSHOTS>' \
  --code_path '<DIR_OF_COMP_CODES>' \
  --inst_path $INST_PATH \
  --ori_img_path $INST_PATH/ori_images \
  --cropped_img_path $INST_PATH/cropped_images >log/batch_inst.log 2>&1 &
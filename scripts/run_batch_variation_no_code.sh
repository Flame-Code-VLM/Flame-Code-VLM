#!/bin/bash

nohup python3 -B -u data_collect/component_collector/variater/variation_waterfall_no_code.py \
    --iter_num=5 \
    --max_system_infer=6 \
    --screenshot_path='<DIR_OF_SCREENSHOTS_OF_COMP_SEEDS>' \
    --repo_path='<DIR_OF_REPOS_OF_COMP_SEEDS>' \
    --variation_path='<DIR_TO_SAVE_VARIATION_COMPS>'>log/comp_variation_waterfall.log 2>&1 &

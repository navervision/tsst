#!/usr/bin/env bash

set -x

EXP_DIR=exps/swin_small_deformable_detr_two_stage_combined_0_0_6
PY_ARGS=${@:1}

python -u main.py \
    --enc_layers 0 \
    --dec_layers 6 \
    --num_workers 2 \
    --batch_size 2 \
    --output_dir ${EXP_DIR} \
    --backbone SwinTransformerSmall \
    --resume ${EXP_DIR}/checkpoint.pth \
    --frozen_weights pretrained/swin_small_patch4_window7_224.pth\
    --with_box_refine \
    --two_stage \
    ${PY_ARGS}

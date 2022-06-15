#!/usr/bin/env bash

set -x

EXP_DIR=exps/swin_tiny_deformable_detr
PY_ARGS=${@:1}

python -u main.py \
    --enc_layers 0 \
    --dec_layers 6 \
    --lr_backbone 0.0001 \
    --lr 0.0002 \
    --weight_decay 0.05 \
    --num_workers 2 \
    --batch_size 3 \
    --output_dir ${EXP_DIR} \
    --backbone SwinTransformerTiny \
    --resume ${EXP_DIR}/checkpoint.pth \
    --frozen_weights pretrained/swin_tiny_patch4_window7_224.pth \
    --with_box_refine \
    ${PY_ARGS}

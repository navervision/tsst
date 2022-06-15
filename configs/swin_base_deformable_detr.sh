#!/usr/bin/env bash

set -x

EXP_DIR=exps/swin_base_deformable_detr_aug_tsd
PY_ARGS=${@:1}

python -u main.py \
    --enc_layers 6 \
    --dec_layers 6 \
    --num_workers 2 \
    --batch_size 1 \
    --lr_drop 30 \
    --epochs 40 \
    --output_dir ${EXP_DIR} \
    --backbone SwinTransformerBase \
    --resume ${EXP_DIR}/checkpoint.pth \
    --frozen_weights pretrained/swin_base_patch4_window7_224.pth \
    --with_box_refine \
    --two_stage \
    ${PY_ARGS}
    #--frozen_weights pretrained/csp_lcosine.pth.tar.76 \
    #--frozen_weights pretrained/imagenet_csp53.pth
    #--lr_backbone 0.0001 \
    #--weight_decay 0.01 \

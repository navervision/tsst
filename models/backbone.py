# ------------------------------------------------------------------------
# TSST
# Copyright (c) 2022-present NAVER Corp.
# Apache-2.0
# ------------------------------------------------------------------------
# Deformable DETR
# Copyright (c) 2020 SenseTime. All Rights Reserved.
# Licensed under the Apache License, Version 2.0 [see LICENSE for details]
# ------------------------------------------------------------------------
# Modified from DETR (https://github.com/facebookresearch/detr)
# Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved
# ------------------------------------------------------------------------

"""
Backbone modules.
"""
from collections import OrderedDict

import torch
import torch.nn.functional as F
import torchvision
from torch import nn
from torchvision.models._utils import IntermediateLayerGetter
from typing import Dict, List

from util.misc import NestedTensor, is_main_process

from .position_encoding import build_position_encoding
from .swin_transformer import _BuildSwinTransformerTiny
from .swin_transformer import _BuildSwinTransformerSmall
from .swin_transformer import _BuildSwinTransformerBase
from .swin_transformer import _BuildSwinTransformerLarge

CustomBackbones =  ['SwinTransformerTiny', 'SwinTransformerSmall','SwinTransformerBase', 'SwinTransformerLarge']
class FrozenBatchNorm2d(torch.nn.Module):
    """
    BatchNorm2d where the batch statistics and the affine parameters are fixed.

    Copy-paste from torchvision.misc.ops with added eps before rqsrt,
    without which any other models than torchvision.models.resnet[18,34,50,101]
    produce nans.
    """

    def __init__(self, n, eps=1e-5):
        super(FrozenBatchNorm2d, self).__init__()
        self.register_buffer("weight", torch.ones(n))
        self.register_buffer("bias", torch.zeros(n))
        self.register_buffer("running_mean", torch.zeros(n))
        self.register_buffer("running_var", torch.ones(n))
        self.eps = eps

    def _load_from_state_dict(self, state_dict, prefix, local_metadata, strict,
                              missing_keys, unexpected_keys, error_msgs):
        num_batches_tracked_key = prefix + 'num_batches_tracked'
        if num_batches_tracked_key in state_dict:
            del state_dict[num_batches_tracked_key]

        super(FrozenBatchNorm2d, self)._load_from_state_dict(
            state_dict, prefix, local_metadata, strict,
            missing_keys, unexpected_keys, error_msgs)

    def forward(self, x):
        # move reshapes to the beginning
        # to make it fuser-friendly
        w = self.weight.reshape(1, -1, 1, 1)
        b = self.bias.reshape(1, -1, 1, 1)
        rv = self.running_var.reshape(1, -1, 1, 1)
        rm = self.running_mean.reshape(1, -1, 1, 1)
        eps = self.eps
        scale = w * (rv + eps).rsqrt()
        bias = b - rm * scale
        return x * scale + bias


class BackboneBase(nn.Module):

    def __init__(self, backbone: nn.Module, backbone_name: str, train_backbone: bool, return_interm_layers: bool):
        super().__init__()
        for name, parameter in backbone.named_parameters():
            if (train_backbone and
                    'layer0' not in name):
                print("%s requires grad."%name)
            else:
                print("%s requires no grad."%name)
                parameter.requires_grad_(False)
        if return_interm_layers:
            if not backbone_name in CustomBackbones:
                return_layers = {"layer2": "0", "layer3": "1", "layer4": "2"}
                self.num_channels = [512, 1024, 2048]
            self.strides = [8, 16, 32]
        else:
            if not backbone_name in CustomBackbones:
                return_layers = {'layer4': "0"}
                self.strides = [32]
                self.num_channels = [2048]
            else:
                self.num_channels = [1024]

        if not backbone_name in CustomBackbones:
            self.body = IntermediateLayerGetter(backbone, return_layers=return_layers)
        else:
            self.body = backbone

    def forward(self, tensor_list: NestedTensor):
        xs = self.body(tensor_list.tensors)
        out: Dict[str, NestedTensor] = {}
        for name, x in xs.items():
            m = tensor_list.mask
            assert m is not None
            mask = F.interpolate(m[None].float(), size=x.shape[-2:]).to(torch.bool)[0]
            out[name] = NestedTensor(x, mask)
        return out


class Backbone(BackboneBase):
    """ResNet backbone with frozen BatchNorm."""
    def __init__(self, backbone_name: str,
                 train_backbone: bool,
                 return_interm_layers: bool,
                 dilation: bool):
        norm_layer = FrozenBatchNorm2d

    
        if backbone_name in 'SwinTransformerTiny':
            backbone, self.num_channels = _BuildSwinTransformerTiny()
        elif backbone_name in 'SwinTransformerSmall':
            backbone, self.num_channels = _BuildSwinTransformerSmall()
        elif backbone_name in 'SwinTransformerBase':
            backbone, self.num_channels = _BuildSwinTransformerBase()
        elif backbone_name in 'SwinTransformerLarge':
            backbone, self.num_channels = _BuildSwinTransformerLarge()
        else:
            backbone = getattr(torchvision.models, backbone_name)(
                replace_stride_with_dilation=[False, False, dilation],
                pretrained=is_main_process(), norm_layer=norm_layer)
            assert backbone_name not in ('resnet18', 'resnet34'), "number of channels are hard coded"

        super().__init__(backbone, backbone_name, train_backbone, return_interm_layers)
        if dilation:
            self.strides[-1] = self.strides[-1] // 2


class Joiner(nn.Sequential):
    def __init__(self, backbone, position_embedding):
        super().__init__(backbone, position_embedding)
        self.strides = backbone.strides
        self.num_channels = backbone.num_channels

    def forward(self, tensor_list: NestedTensor):
        xs = self[0](tensor_list)
        out: List[NestedTensor] = []
        pos = []
        # name is defined as "0", "1", "2", etc. but ignored(not used after).
        for name, x in sorted(xs.items()):
            out.append(x)

        # position encoding
        for x in out:
            pos.append(self[1](x).to(x.tensors.dtype))

        return out, pos


def build_backbone(args):
    position_embedding = build_position_encoding(args)
    train_backbone = getattr(args,'lr_backbone',0) > 0
    return_interm_layers = args.masks or (args.num_feature_levels > 1)
    backbone = Backbone(args.backbone, train_backbone, return_interm_layers, args.dilation)
    model = Joiner(backbone, position_embedding)
    return model
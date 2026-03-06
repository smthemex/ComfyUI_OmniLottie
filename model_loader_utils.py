# !/usr/bin/env python
# -*- coding: UTF-8 -*-
import os
import torch
import gc
from PIL import Image
import numpy as np
from comfy.utils import common_upscale
import comfy.model_management as mm
import json
cur_path = os.path.dirname(os.path.abspath(__file__))

def load_lottie_json_from_path(json_path):
    """
    从文件路径加载 Lottie JSON 数据。
    
    参数:
        json_path: Lottie JSON 文件的路径。
        
    返回:
        包含 Lottie 动画数据的字典。
    """
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Lottie JSON file not found: {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        lottie_data = json.load(f)
        
    #调用 fix_lottie_json 确保数据结构完整
    from .app import fix_lottie_json
    lottie_data = fix_lottie_json(lottie_data)
    
    return lottie_data

def clear_comfyui_cache():
    cf_models=mm.loaded_models()
    try:
        for pipe in cf_models:
            pipe.unpatch_model(device_to=torch.device("cpu"))
            print(f"Unpatching models.{pipe}")
    except: pass
    mm.soft_empty_cache()
    torch.cuda.empty_cache()
    max_gpu_memory = torch.cuda.max_memory_allocated()
    print(f"After Max GPU memory allocated: {max_gpu_memory / 1000 ** 3:.2f} GB")


def gc_cleanup():
    gc.collect()
    torch.cuda.empty_cache()


def phi2narry(img):
    img = torch.from_numpy(np.array(img).astype(np.float32) / 255.0).unsqueeze(0)
    return img

def tensor2image(tensor):
    tensor = tensor.cpu()
    image_np = tensor.squeeze().mul(255).clamp(0, 255).byte().numpy()
    image = Image.fromarray(image_np, mode='RGB')
    return image

def tensor2pillist(tensor_in):
    d1, _, _, _ = tensor_in.size()
    if d1 == 1:
        img_list = [tensor2image(tensor_in)]
    else:
        tensor_list = torch.chunk(tensor_in, chunks=d1)
        img_list=[tensor2image(i) for i in tensor_list]
    return img_list

def tensor2pillist_upscale(tensor_in,width,height):
    d1, _, _, _ = tensor_in.size()
    if d1 == 1:
        img_list = [tensor2pil_upscale(tensor_in,width,height)]
    else:
        tensor_list = torch.chunk(tensor_in, chunks=d1)
        img_list=[tensor2pil_upscale(i,width,height) for i in tensor_list]
    return img_list

def tensor2list(tensor_in,width,height):
    if tensor_in is None:
        return None
    d1, _, _, _ = tensor_in.size()
    if d1 == 1:
        tensor_list = [tensor_upscale(tensor_in,width,height)]
    else:
        tensor_list_ = torch.chunk(tensor_in, chunks=d1)
        tensor_list=[tensor_upscale(i,width,height) for i in tensor_list_]
    return tensor_list


def tensor_upscale(tensor, width, height):
    samples = tensor.movedim(-1, 1)
    samples = common_upscale(samples, width, height, "bilinear", "center")
    samples = samples.movedim(1, -1)
    return samples

def tensor2pil_upscale(img, width, height):
    samples = img.movedim(-1, 1)
    img = common_upscale(samples, width, height, "bilinear", "center")
    samples = img.movedim(1, -1)
    img = tensor2image(samples)
    return img

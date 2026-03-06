 # !/usr/bin/env python
# -*- coding: UTF-8 -*-

import numpy as np
import torch
import os
from omegaconf import OmegaConf
import folder_paths
from typing_extensions import override
from .inference import run_single_inference,load_model
from .model_loader_utils import tensor2pillist_upscale,tensor2pil_upscale
from .app import create_lottie_html,save_lottie_html
from comfy_api.latest import ComfyExtension, io

MAX_SEED = np.iinfo(np.int32).max

device = torch.device(
    "cuda:0") if torch.cuda.is_available() else torch.device(
    "mps") if torch.backends.mps.is_available() else torch.device("cpu")

node_cr_path = os.path.dirname(os.path.abspath(__file__))



class OmniLottie_SM_Model(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        
        return io.Schema(
            node_id="OmniLottie_SM_Model",
            display_name="OmniLottie_SM_Model",
            category="OmniLottie",
            inputs=[
                io.Combo.Input("ckpt",options= ["none"] +folder_paths.get_filename_list("diffusion_models") ), 
                io.Int.Input("pix_len", default=1500, min=1, max=1000000,step=1,display_mode=io.NumberDisplay.number),
                io.Int.Input("text_len", default=4096, min=1, max=1000000,step=1,display_mode=io.NumberDisplay.number),
            ],
            outputs=[
                io.Model.Output(display_name="model"),
                ],
            )
    @classmethod
    def execute(cls,ckpt,pix_len,text_len) -> io.NodeOutput:
        sketch_weight=folder_paths.get_full_path("diffusion_models", ckpt) if ckpt != "none" else None
        model=load_model(sketch_weight,pix_len,text_len,node_cr_path,device)
        return io.NodeOutput(model)
    
class OmniLottie_SM_KSampler(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="OmniLottie_SM_KSampler",
            display_name="OmniLottie_SM_KSampler",
            category="OmniLottie",
            inputs=[
                io.Model.Input("model"),
                io.String.Input("prompt",multiline=True, default="a light blue piggy bank with a darker blue outline, with a single light blue coin with a dark blue yen symbol (Â£) appears above the piggy bank, then starts descending towards the piggy bank's opening"),
                io.Float.Input("temperature", default=0.9, min=0.00, max=1.0,step=0.01,display_mode=io.NumberDisplay.number),
                io.Float.Input("top_p", default=0.25, min=0.01, max=1.0,step=0.01,display_mode=io.NumberDisplay.number),
                io.Int.Input("top_k", default=5, min=1, max=100,step=1,display_mode=io.NumberDisplay.number),
                io.Image.Input("images",optional=True), 
            ],
            outputs=[
                io.String.Output(display_name="path"),
                io.String.Output(display_name="html"),
            ],
        ) 
    @classmethod
    def execute(cls, model,prompt,temperature, top_p,top_k,images=None) -> io.NodeOutput: 
        single_video,single_image=False,False
        if images is not None:
            d1, _, _, _ = images.size()
            if d1>1:
                images=tensor2pillist_upscale(images, 336,336)
                single_video=True
            else:
                images=tensor2pil_upscale(images,448,448)
                single_image=True
        params={"sketch_weight":"sketch_weight",
                "tokenizer_name": "Qwen/Qwen2.5-VL-3B-Instruct",
                "text_len": 4096,
                "maxlen": 1500,
                "num_candidates": 1,
                "output_dir":folder_paths.get_output_directory(),
                "single_text": prompt,
                "single_image":single_image,
                "single_video":single_video,
                "use_sampling": True,   
                "temperature": temperature,
                "top_p": top_p,
                "top_k": top_k,
                "repetition_penalty": 1.01,
                }
        args = OmegaConf.create(params)
        cfg= {
            'tokenizer_name': args.tokenizer_name,
            'text_len': model.text_len,
            'pix_len': model.pix_len,
            'num_candidates': args.num_candidates,  
            }

        path,lottie_json=run_single_inference(model,args,cfg,images,node_cr_path,device)
        html_path=path.replace(".json",".html")
        if lottie_json is not None:
            save_lottie_html(lottie_json,html_path)
        return io.NodeOutput(path,html_path)

class OmniLottie_SM_Extension(ComfyExtension):
    @override
    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        return [
            OmniLottie_SM_Model,
            OmniLottie_SM_KSampler,
        ]


async def comfy_entrypoint() -> OmniLottie_SM_Extension:  # ComfyUI calls this to load your extension and its nodes.
    return OmniLottie_SM_Extension()

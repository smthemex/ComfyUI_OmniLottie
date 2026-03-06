import torch
import torch.nn as nn
from transformers import Qwen2_5_VLForConditionalGeneration, AutoConfig
from transformers.models.qwen2_5_vl.modeling_qwen2_5_vl import Qwen2_5_VLCausalLMOutputWithPast
from typing import Any, Dict, List, Optional, Tuple, Union
from accelerate import init_empty_weights

import transformers.models.qwen2_5_vl.modeling_qwen2_5_vl as qwen_modeling



class LottieDecoder(nn.Module):
    """
    Autoregressive generative model for OmniLottie
    """

    def __init__(self,
                 pix_len,
                 text_len,
                 model_path="Qwen/Qwen2.5-VL-3B-Instruct", 
                 **kwargs):
        super().__init__()
        
        self.pix_len = pix_len
        self.text_len = text_len
        
        self.vocab_size = 192400
        self.bos_token_id = 192398
        self.eos_token_id = 192399
        self.pad_token_id = 151643
        
        print(f"Loading model from {model_path}...")
        
        config = AutoConfig.from_pretrained(
            model_path,
            vocab_size=self.vocab_size,
            bos_token_id=self.bos_token_id,
            eos_token_id=self.eos_token_id,
            pad_token_id=self.pad_token_id,
            trust_remote_code=True
        )
        with init_empty_weights():
            self.transformer = Qwen2_5_VLForConditionalGeneration(config)
        # self.transformer = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        #     model_path,
        #     config=config,
        #     torch_dtype=torch.bfloat16,
        #     attn_implementation="eager",  
        #     ignore_mismatched_sizes=True
        # )

        self.transformer.resize_token_embeddings(self.vocab_size)
        
        #self.train()

    def forward(self, 
                    input_ids=None,
                    attention_mask=None,
                    pixel_values=None,
                    image_grid_thw=None,
                    pixel_values_videos = None,
                    video_grid_thw = None, 
                    labels=None,
                    past_key_values=None,
                    use_cache=False,
                    **kwargs):

            return NotImplementedError
# !/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
OmniLottie on ComfyUI text-encoder core inference flow.

Replaces the HF transformers modeling stack (Qwen2_5_VLForConditionalGeneration
+ accelerate + qwen_vl_utils) with ComfyUI's own text-encoder core:

  - comfy.text_encoders.llama.Llama2_        : Qwen2.5 LLM body (state-dict keys
                                               identical to HF Qwen2.5-VL)
  - comfy.text_encoders.llama.BaseGenerate   : core autoregressive decode loop
                                               (KV cache, temperature / top_p /
                                               top_k / repetition_penalty, seed,
                                               stop tokens, progress bar)
  - comfy.text_encoders.qwen_vl              : Qwen2-VL vision tower +
                                               image preprocessing + MRoPE ids

No ComfyUI source files are modified; everything here subclasses / imports
from the `comfy` package.

Model = Qwen2.5-VL-3B backbone with vocab extended to 192400
(151936 Qwen tokens + ~40k Lottie command tokens + Lottie BOS/EOS),
`tie_word_embeddings=True` so logits come straight from embed_tokens
(handled by BaseGenerate.logits).
"""

import math

import numpy as np
import torch
from dataclasses import dataclass
from typing import List, Optional, Tuple

import comfy.model_management as mm
import comfy.model_patcher
import comfy.ops
import comfy.utils
from comfy.text_encoders import llama as comfy_llama
from comfy.text_encoders import qwen_vl

LOTTIE_BOS = 192398
LOTTIE_EOS = 192399
PAD_TOKEN = 151643
OMNILOTTIE_IMAGE_PAD_TOKEN = 151655
OMNILOTTIE_VIDEO_PAD_TOKEN = 151656
# '/end' (animation terminator) = LottieTensor.COMMANDS[248] + COMMAND_OFFSET(151936);
# used to truncate a candidate when EOS was missed by sampling
LOTTIE_END_END = 152184


@dataclass
class OmniLottieTEConfig:
    """Qwen2.5-VL-3B dims with the OmniLottie extended vocab."""
    vocab_size: int = 192400
    hidden_size: int = 2048
    intermediate_size: int = 11008
    num_hidden_layers: int = 36
    num_attention_heads: int = 16
    num_key_value_heads: int = 2
    max_position_embeddings: int = 128000
    rms_norm_eps: float = 1e-6
    rope_theta: float = 1000000.0
    transformer_type: str = "llama"
    head_dim = 128
    rms_norm_add = False
    mlp_activation = "silu"
    qkv_bias = True
    rope_dims = [16, 24, 24]        # Qwen2.5-VL 3D MRoPE section layout
    q_norm = None
    k_norm = None
    rope_scale = None
    final_norm: bool = True
    lm_head: bool = False           # tied embeddings -> BaseGenerate.logits uses embed_tokens
    stop_tokens = [LOTTIE_EOS]


class OmniLottieTE(comfy_llama.BaseLlama, comfy_llama.BaseGenerate, torch.nn.Module):
    """
    OmniLottie generator on the ComfyUI TE core.

    Skeleton mirrors comfy.text_encoders.llama.Qwen25_7BVLI (the official
    Qwen2.5-VL + BaseGenerate reference), resized to the 3B config.
    """

    def __init__(self, config_dict=None, dtype=None, device=None, operations=None):
        super().__init__()
        config = OmniLottieTEConfig(**(config_dict or {}))
        self.config = config
        self.num_layers = config.num_hidden_layers

        operations = operations or comfy.ops.manual_cast
        self.model = comfy_llama.Llama2_(config, device=device, dtype=dtype, ops=operations)
        self.visual = qwen_vl.Qwen2VLVisionTransformer(
            hidden_size=1280, output_hidden_size=config.hidden_size,
            device=device, dtype=dtype, ops=operations)
        self.dtype = dtype

    # ------------------------------------------------------------------ #
    # vision helpers
    # ------------------------------------------------------------------ #
    def encode_image(self, image: torch.Tensor, device) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        image: (1, H, W, 3) float32 in [0, 1].
        Returns (image_embeds (n_tokens, hidden), grid_thw (1, 3)).
        """
        patches, grid = qwen_vl.process_qwen2vl_images(image)
        return self.visual(patches.to(device, dtype=torch.float32), grid), grid

    def encode_video(self, patches: torch.Tensor, grid: torch.Tensor, device) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        patches: (grid_t * grid_h * grid_w, 1176) float32, built by video_to_patches.
        grid:    (1, 3) tensor [grid_t, grid_h, grid_w].
        Returns (video_embeds (n_tokens, hidden), grid_thw).
        """
        return self.visual(patches.to(device, dtype=torch.float32), grid), grid


# ---------------------------------------------------------------------- #
# video preprocessing (core only ships the single-image variant)
# ---------------------------------------------------------------------- #
QWEN_IMAGE_MEAN = [0.48145466, 0.4578275, 0.40821073]
QWEN_IMAGE_STD = [0.26862954, 0.26130258, 0.27577711]


def video_to_patches(frames: List, patch_size: int = 14, temporal_patch_size: int = 2,
                     merge_size: int = 2, target_size: int = 336) -> Tuple[torch.Tensor, torch.Tensor]:
    """
    frames: list of PIL RGB images (already sampled, e.g. 8 frames).
    Mirrors the HF Qwen2.5-VL video patchify + the patch layout produced by
    comfy's qwen_vl.process_qwen2vl_images, so the core VisionTransformer
    consumes it unchanged:
      - sequence order: (grid_t, grid_h // merge, grid_w // merge)
      - per-patch layout: (merge_pos(4), channel(3), temporal(2), 14, 14)
    Returns (pixel_values (N, 1176) float32, grid_thw (1, 3)).
    """
    import PIL.Image
    if frames[0].size != (target_size, target_size):
        # caller normally resizes; do a plain resize fallback here
        frames = [f.convert("RGB").resize((target_size, target_size), PIL.Image.LANCZOS) for f in frames]
    arr = np.stack([np.asarray(f.convert("RGB"), dtype=np.float32) / 255.0 for f in frames])  # (t, H, W, C)
    t = arr.shape[0]
    if t % temporal_patch_size != 0:
        # HF behavior: repeat the last frame to reach an even count
        repeats = np.repeat(arr[-1][np.newaxis], temporal_patch_size - (t % temporal_patch_size), axis=0)
        arr = np.concatenate([arr, repeats], axis=0)
        t = arr.shape[0]

    for c in range(3):
        arr[..., c] = (arr[..., c] - QWEN_IMAGE_MEAN[c]) / QWEN_IMAGE_STD[c]

    grid_t = t // temporal_patch_size
    grid_h = target_size // patch_size
    grid_w = target_size // patch_size

    # (t, H, W, C) -> (t, C, H, W) then patchify exactly like the core image path
    arr = arr.transpose(0, 3, 1, 2)
    patches = arr.reshape(
        grid_t, temporal_patch_size, 3,
        grid_h // merge_size, merge_size, patch_size,
        grid_w // merge_size, merge_size, patch_size,
    )
    patches = patches.transpose(0, 3, 6, 4, 7, 2, 1, 5, 8)
    patches = patches.reshape(grid_t * grid_h * grid_w, 3 * temporal_patch_size * patch_size * patch_size)

    grid = torch.tensor([[grid_t, grid_h, grid_w]], dtype=torch.long)
    return torch.from_numpy(patches.copy()), grid


# ---------------------------------------------------------------------- #
# MRoPE position ids (3D) for the prefill
# ---------------------------------------------------------------------- #
def build_mrope_position_ids(seq_len: int, span: Tuple[int, int], grid: torch.Tensor,
                             is_video: bool, device) -> torch.Tensor:
    """
    Build (3, seq_len) T/H/W MRoPE position ids for a single vision span.

    Image semantics follow comfy's qwen_vl.qwen2vl_mrope_position_ids.
    Video semantics follow the transformers 4.51.3 get_rope_index the original
    OmniLottie inference ran on (second_per_grid_ts=None, and the bundled
    Qwen2.5-VL config sets tokens_per_second=2):
        t-axis positions = arange(grid_t) * 2 + start
        text resumes at start + max((grid_t-1)*2, llm_h-1, llm_w-1) + 1
    """
    start, end = span
    pos = torch.zeros((3, seq_len), dtype=torch.long, device=device)
    pos[:, :start] = torch.arange(0, start, device=device).unsqueeze(0)

    g = grid[0]
    llm_h = int(g[1]) // 2
    llm_w = int(g[2]) // 2
    n = end - start

    if is_video:
        t = int(g[0])
        tps = 2  # vision_config.tokens_per_second of the bundled config
        pos_t = (torch.arange(t, device=device) * tps).view(t, 1, 1).expand(t, llm_h, llm_w).reshape(-1)
        pos_h = torch.arange(llm_h, device=device).view(1, llm_h, 1).expand(t, llm_h, llm_w).reshape(-1)
        pos_w = torch.arange(llm_w, device=device).view(1, 1, llm_w).expand(t, llm_h, llm_w).reshape(-1)
        pos[0, start:end] = pos_t + start
        pos[1, start:end] = pos_h + start
        pos[2, start:end] = pos_w + start
        after = max((t - 1) * tps, llm_h - 1, llm_w - 1) + 1
    else:
        pos[0, start:end] = start
        # H axis: each h value held for a full llm_w run; W axis: cycles 0..llm_w-1
        pos[1, start:end] = (torch.arange(llm_h, device=device)
                             .view(-1, 1).expand(llm_h, llm_w).reshape(-1)[:n] + start)
        pos[2, start:end] = (torch.arange(llm_w, device=device)
                             .repeat(math.ceil(n / llm_w))[:n] + start)
        after = max(llm_h, llm_w)

    pos[:, end:] = torch.arange(start + after, start + after + (seq_len - end),
                                device=device).unsqueeze(0)
    return pos


# ---------------------------------------------------------------------- #
# checkpoint loading through the ComfyUI model-management stack
# ---------------------------------------------------------------------- #
class OmniLottieWrapper:
    """What the loader node hands to the sampler node."""

    def __init__(self, te: OmniLottieTE, patcher: comfy.model_patcher.ModelPatcher,
                 pix_len: int, text_len: int, missing_keys: List[str], unexpected_keys: List[str]):
        self.te = te
        self.patcher = patcher
        self.pix_len = pix_len
        self.text_len = text_len
        self.missing_keys = missing_keys
        self.unexpected_keys = unexpected_keys

    @property
    def device(self):
        return mm.text_encoder_device()

    def execution_dtype(self) -> torch.dtype:
        device = self.device
        if mm.should_use_bf16(device):
            return torch.bfloat16
        return torch.float32


def load_omnilottie_model(checkpoint_path: str, pix_len: int = 1500, text_len: int = 4096) -> OmniLottieWrapper:
    """
    Load the OmniLottie safetensors checkpoint into OmniLottieTE and register it
    with comfy model management (VRAM offload / weight casting).

    Key mapping vs the original HF checkpoint:
      - a leading "transformer." prefix (saved from the old LottieDecoder wrapper)
        is stripped;
      - "model.*" and "visual.*" map 1:1 onto comfy Llama2_ / VisionTransformer;
      - "lm_head.weight" is dropped (tied embeddings).
    """
    sd = comfy.utils.load_torch_file(checkpoint_path)

    first_key = next(iter(sd))
    if first_key.startswith("transformer."):
        prefix = "transformer."
        sd = {k[len(prefix):]: v for k, v in sd.items() if k.startswith(prefix)}
    sd.pop("lm_head.weight", None)  # tied to embed_tokens on the 3B model

    # storage dtype straight from the checkpoint (no silent upcast)
    storage_dtype = torch.bfloat16
    for v in sd.values():
        if v.is_floating_point():
            storage_dtype = v.dtype
            break

    te = OmniLottieTE(dtype=storage_dtype, device="cpu", operations=comfy.ops.manual_cast)
    missing, unexpected = te.load_state_dict(sd, strict=False)
    del sd

    # keep genuinely-absent weights visible; ignore tied/unexpected buffer noise
    missing = [k for k in missing if "lm_head" not in k]

    load_device = mm.text_encoder_device()
    offload_device = mm.text_encoder_offload_device()
    patcher = comfy.model_patcher.ModelPatcher(te, load_device=load_device, offload_device=offload_device)
    mm.load_models_gpu([patcher])

    return OmniLottieWrapper(te, patcher, pix_len, text_len, missing, unexpected)

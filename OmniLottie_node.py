# !/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
OmniLottie nodes on the ComfyUI text-encoder core inference flow.

  OmniLottie_SM_Model   : loads the safetensors checkpoint into an
                          OmniLottieTE (comfy TE core) and returns a
                          VRAM-managed ModelPatcher wrapper.
  OmniLottie_SM_KSampler: builds the chat prompt, runs vision encoding on the
                          core Qwen2-VL tower, decodes Lottie tokens with the
                          core BaseGenerate loop, detokenizes to Lottie JSON
                          and renders an HTML preview.

The old wrapper path (decoder.py / inference.py) is kept only for
`tokens_to_lottie_json` (detokenization) which is model-independent.
"""

import os
import time

import numpy as np
import torch

import folder_paths
import comfy.model_management as mm
from comfy_api.latest import  io


from .app import save_lottie_html
from .model_loader_utils import tensor2pil_upscale, tensor2pillist_upscale
from .omnilottie_te import (
    LOTTIE_EOS,
    LOTTIE_END_END,
    OMNILOTTIE_IMAGE_PAD_TOKEN,
    OMNILOTTIE_VIDEO_PAD_TOKEN,
    OmniLottieWrapper,
    build_mrope_position_ids,
    load_omnilottie_model,
    video_to_patches,
)

MAX_SEED = np.iinfo(np.int32).max
omnilottie_node_cr_path = os.path.dirname(os.path.abspath(__file__))

# verified against the bundled Qwen2.5-VL-3B-Instruct chat template
OMNILOTTIE_SYSTEM_PROMPT = "You are a Lottie animation expert."
OMNILOTTIE_VIDEO_PROMPT = "Turn this video into Lottie code."
OMNILOTTIE_IMG_RES = 448    # 16 x 28 -> 256 merged vision tokens
OMNILOTTIE_VID_RES = 336    # 8 frames -> grid [4, 24, 24] -> 576 merged vision tokens
OMNILOTTIE_NUM_FRAMES = 8

OMNILOTTIE_TOKENIZER_DIR = os.path.join(omnilottie_node_cr_path, "Qwen2.5-VL-3B-Instruct")
omnilottie_tokenizer = None


def get_tokenizer():
    global omnilottie_tokenizer
    if omnilottie_tokenizer is None:
        from transformers import AutoTokenizer
        omnilottie_tokenizer = AutoTokenizer.from_pretrained(OMNILOTTIE_TOKENIZER_DIR, local_files_only=True)
    return omnilottie_tokenizer


OMNILOTTIE_MODEL_CACHE = {}


def _get_model(ckpt: str, pix_len: int, text_len: int) -> OmniLottieWrapper:
    full_path = folder_paths.get_full_path("text_encoders", ckpt)
    mtime = os.path.getmtime(full_path)
    key = (full_path, mtime, pix_len, text_len)
    wrapper = OMNILOTTIE_MODEL_CACHE.get(key)
    if wrapper is None:
        OMNILOTTIE_MODEL_CACHE.clear()
        wrapper = load_omnilottie_model(full_path, pix_len=pix_len, text_len=text_len)
        OMNILOTTIE_MODEL_CACHE[key] = wrapper
    return wrapper


def _vision_embeds(wrapper: OmniLottieWrapper, images: torch.Tensor):
    """
    Returns (embeds_span (n, hidden), grid, n_pad_tokens, is_video).
    """
    device = wrapper.device
    te = wrapper.te
    d1 = images.size(0)
    if d1 > 1:  # video: sample OMNILOTTIE_NUM_FRAMES frames, 336x336
        frames = tensor2pillist_upscale(images, OMNILOTTIE_VID_RES, OMNILOTTIE_VID_RES)
        total = len(frames)
        idx = list(range(total)) if total <= OMNILOTTIE_NUM_FRAMES else \
            np.linspace(0, total - 1, OMNILOTTIE_NUM_FRAMES).astype(int).tolist()
        frames = [frames[i] for i in idx]
        patches, grid = video_to_patches(frames, target_size=OMNILOTTIE_VID_RES)
        span_embeds, grid = te.encode_video(patches, grid, device)
        return span_embeds, grid, span_embeds.size(0), True
    else:  # single image, 448x448
        img = tensor2pil_upscale(images, OMNILOTTIE_IMG_RES, OMNILOTTIE_IMG_RES)
        arr = torch.from_numpy(np.asarray(img, dtype=np.float32) / 255.0)  # (H, W, C)
        image = arr.unsqueeze(0)  # (1, H, W, 3)
        span_embeds, grid = te.encode_image(image, device)
        return span_embeds, grid, span_embeds.size(0), False


def _build_prompt(prompt: str, n_pad_tokens: int, is_video: bool) -> str:
    media = "<|vision_start|>" + "<|image_pad|>" if not is_video else \
        "<|vision_start|>" + "<|video_pad|>"
    media = media + ("<|video_pad|>" if is_video else "<|image_pad|>") * (n_pad_tokens - 1)
    media += "<|vision_end|>"
    if is_video:
        user_content = media + OMNILOTTIE_VIDEO_PROMPT
    else:
        user_content = media + f"Animate this image: {prompt}"
    return (f"<|im_start|>system\n{OMNILOTTIE_SYSTEM_PROMPT}<|im_end|>\n"
            f"<|im_start|>user\n{user_content}<|im_end|>\n"
            f"<|im_start|>assistant\n")


def _text_prompt(prompt: str) -> str:
    return (f"<|im_start|>system\n{OMNILOTTIE_SYSTEM_PROMPT}<|im_end|>\n"
            f"<|im_start|>user\nGenerate Lottie code: {prompt}<|im_end|>\n"
            f"<|im_start|>assistant\n")


def _find_span(input_ids: torch.Tensor, pad_token: int) -> tuple:
    ids = input_ids[0]
    idx = (ids == pad_token).nonzero(as_tuple=True)[0]
    if idx.numel() == 0:
        raise ValueError(f"No {pad_token} placeholder tokens found in prompt")
    return int(idx[0]), int(idx[-1]) + 1


def generate_candidates(wrapper: OmniLottieWrapper, prompt: str, images=None,
                        temperature=0.9, top_p=0.25, top_k=5,
                        repetition_penalty=1.01, num_candidates=1, seed=0,
                        max_retries=4, stop_on_eos=False):
    """
    Returns a list of generated token-id lists (one per candidate).
    """
    device = wrapper.device
    te = wrapper.te
    tok = get_tokenizer()

    vision = None
    if images is not None:
        span_embeds, grid, n_pad, is_video = _vision_embeds(wrapper, images)
        vision = (span_embeds, grid, n_pad, is_video)

    if vision is not None:
        span_embeds, grid, n_pad, is_video = vision
        text = _build_prompt(prompt, n_pad, is_video)
        pad_token = OMNILOTTIE_VIDEO_PAD_TOKEN if is_video else OMNILOTTIE_IMAGE_PAD_TOKEN
    else:
        text = _text_prompt(prompt)

    input_ids = tok(text, add_special_tokens=False, return_tensors="pt").input_ids.to(device)

    embeds = te.model.embed_tokens(input_ids).to(wrapper.execution_dtype())

    position_ids = None
    if vision is not None:
        span_embeds, grid, n_pad, is_video = vision
        span = _find_span(input_ids, pad_token)
        if span[1] - span[0] != n_pad:
            raise ValueError(f"Span size {span[1] - span[0]} != vision embeds {n_pad}")
        embeds[0, span[0]:span[1]] = span_embeds.to(embeds.dtype)
        position_ids = build_mrope_position_ids(embeds.shape[1], span, grid, is_video, device)

    mm.load_models_gpu([wrapper.patcher])

    do_sample = temperature > 0.0
    candidates = []
    for i in range(num_candidates):
        base_seed = seed + i * 1009
        for attempt in range(max_retries):
            ids = te.generate(
                embeds=embeds,
                position_ids=position_ids,
                do_sample=do_sample,
                max_length=wrapper.pix_len,
                temperature=temperature,
                top_k=top_k,
                top_p=top_p,
                min_p=0.0,
                repetition_penalty=repetition_penalty,
                seed=base_seed + attempt,
                stop_tokens=[LOTTIE_EOS],
                execution_dtype=wrapper.execution_dtype(),
            )
            if not _is_degenerate(ids):
                break
            print(f"[OmniLottie] degenerate sample (seed {base_seed + attempt}), "
                  f"retrying with a new seed ({attempt + 1}/{max_retries})...")
        candidates.append(ids)
        if stop_on_eos and LOTTIE_EOS in ids:
            remaining = num_candidates - i - 1
            if remaining > 0:
                print(f"[OmniLottie] EOS-terminated candidate found -> "
                      f"skipping {remaining} remaining candidate(s)")
            break
    return candidates


LOTTIE_CMD_LO = 151936
LOTTIE_CMD_HI = LOTTIE_CMD_LO + 282


def _command_count(ids):
    return sum(1 for t in ids if LOTTIE_CMD_LO <= t < LOTTIE_CMD_HI)


def _is_degenerate(ids):
    """
    Some seeds collapse into a parameter loop: no command tokens (or no '/end'
    terminator) in the whole stream -> conversion would fail. Healthy streams
    emit the animation header within the first tokens and end with '/end'+EOS.
    """
    if LOTTIE_EOS in ids or LOTTIE_END_END in ids:
        return False
    return _command_count(ids) < 5


def _normalize_candidate(ids):
    """
    When EOS was missed after the animation's '/end' terminator, truncate at
    the last '/end' so no extra (half-generated) object follows.
    """
    n_cmd = _command_count(ids)
    if LOTTIE_EOS in ids:
        print(f"[OmniLottie] candidate: {len(ids)} tokens, {n_cmd} commands, EOS ok")
        return ids
    for i in range(len(ids) - 1, -1, -1):
        if ids[i] == LOTTIE_END_END:
            print(f"[OmniLottie] candidate: {len(ids)} tokens, {n_cmd} commands, "
                  f"EOS MISSED -> truncated at '/end' (kept {i + 1})")
            return ids[:i + 1]
    print(f"[OmniLottie] candidate: {len(ids)} tokens, {n_cmd} commands, no terminator")
    return ids


def _score_lottie(lottie_json, has_eos):
    """
    Best-of-N quality score (higher = better):
      1. EOS-terminated streams beat truncated ones (weight 10)
      2. fraction of layers positioned inside the canvas (weight 1) —
         unlucky seeds often park extra layers off-canvas
    """
    w = lottie_json.get("w", 512)
    h = lottie_json.get("h", 512)
    margin = 64
    layers = lottie_json.get("layers", [])
    on_canvas = 0
    for l in layers:
        p = (l.get("ks") or {}).get("p")
        if isinstance(p, dict):
            k = p.get("k")
        else:
            k = p
        if isinstance(k, list) and k and isinstance(k[0], (int, float)) and len(k) >= 2:
            x, y = k[0], k[1]
            if -margin <= x <= w + margin and -margin <= y <= h + margin:
                on_canvas += 1
        else:
            on_canvas += 1  # animated position: assume valid
    ratio = on_canvas / len(layers) if layers else 0.0
    return (10 if has_eos else 0) + ratio


class OmniLottie_SM_Model(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="OmniLottie_SM_Model",
            display_name="OmniLottie_SM_Model",
            category="OmniLottie",
            inputs=[
                io.Combo.Input("ckpt", options=["none"] + folder_paths.get_filename_list("text_encoders")),
                io.Int.Input("pix_len", default=1500, min=1, max=1000000, step=1,
                             display_mode=io.NumberDisplay.number),
                io.Int.Input("text_len", default=4096, min=1, max=1000000, step=1,
                             display_mode=io.NumberDisplay.number),
            ],
            outputs=[
                io.Model.Output(display_name="model"),
            ],
        )

    @classmethod
    def execute(cls, ckpt, pix_len, text_len) -> io.NodeOutput:
        if ckpt == "none":
            raise ValueError("Select an OmniLottie checkpoint (Lottie_weight.safetensors)")
        wrapper = _get_model(ckpt, pix_len, text_len)
        if wrapper.missing_keys:
            print(f"[OmniLottie] missing keys: {wrapper.missing_keys[:8]}"
                  f"{' ...' if len(wrapper.missing_keys) > 8 else ''}")
        if wrapper.unexpected_keys:
            print(f"[OmniLottie] unexpected keys: {wrapper.unexpected_keys[:8]}"
                  f"{' ...' if len(wrapper.unexpected_keys) > 8 else ''}")
        print(f"[OmniLottie] loaded {ckpt} (pix_len={pix_len}) on comfy TE core")
        return io.NodeOutput(wrapper)


class OmniLottie_SM_KSampler(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="OmniLottie_SM_KSampler",
            display_name="OmniLottie_SM_KSampler",
            category="OmniLottie",
            inputs=[
                io.Model.Input("model"),
                io.String.Input("prompt", multiline=True,
                                default="a light blue piggy bank with a darker blue outline, "
                                        "with a single light blue coin with a dark blue yen symbol "
                                        "appears above the piggy bank, then starts descending "
                                        "towards the piggy bank's opening"),
                io.Int.Input("seed", default=0, min=0, max=MAX_SEED,
                             control_after_generate="randomize"),
                io.Int.Input("num_candidates", default=1, min=1, max=8, step=1,
                             display_mode=io.NumberDisplay.number),
                io.Int.Input("max_retries", default=4, min=1, max=10, step=1,
                             tooltip="Auto-retries with a new seed when a sample degenerates "
                                     "(no command tokens / no terminator in the stream)"),
                io.Boolean.Input("stop_on_eos", default=False,
                                 tooltip="Stop generating further candidates as soon as one ends "
                                         "with EOS (saves time; disables cross-candidate quality "
                                         "selection for the remaining slots)"),
                io.Float.Input("temperature", default=0.9, min=0.0, max=1.0, step=0.01,
                               display_mode=io.NumberDisplay.number),
                io.Float.Input("top_p", default=0.25, min=0.01, max=1.0, step=0.01,
                               display_mode=io.NumberDisplay.number),
                io.Int.Input("top_k", default=5, min=1, max=100, step=1,
                             display_mode=io.NumberDisplay.number),
                io.Float.Input("repetition_penalty", default=1.01, min=1.0, max=2.0, step=0.01,
                               display_mode=io.NumberDisplay.number),
                io.Image.Input("images", optional=True),
            ],
            outputs=[
                io.String.Output(display_name="path"),
                io.String.Output(display_name="html"),
            ],
        )

    @classmethod
    def execute(cls, model, prompt, seed, num_candidates, max_retries, stop_on_eos,
                temperature, top_p, top_k, repetition_penalty, images=None) -> io.NodeOutput:
        candidates = generate_candidates(
            model, prompt, images=images,
            temperature=temperature, top_p=top_p, top_k=top_k,
            repetition_penalty=repetition_penalty,
            num_candidates=num_candidates, seed=seed, max_retries=max_retries,
            stop_on_eos=stop_on_eos)
        candidates = [_normalize_candidate(ids) for ids in candidates]

        # detokenize: lightweight module (no pandas/datasets/decord/etc.)
        # LottieTensor.init_tokenizer() defaults to the HF Hub repo id; pre-seed
        # it with the local tokenizer dir so detokenization never touches network.
        from .lottie.objects.lottie_tokenize import LottieTensor
        if LottieTensor.tokenizer is None:
            LottieTensor.init_tokenizer(OMNILOTTIE_TOKENIZER_DIR)
        from .lottie_detok import tokens_to_lottie_json

        output_dir = folder_paths.get_output_directory()
        os.makedirs(output_dir, exist_ok=True)
        prefix = time.strftime("%Y%m%d-%H%M%S")
        task = "video" if images is not None and images.size(0) > 1 else \
            "image" if images is not None else "text"
        out_path = os.path.join(output_dir, f"omnilottie_{task}_result_{prefix}.json")

        # convert every candidate and pick the best by quality, not the first
        # that parses (the model frequently produces extra/misplaced layers on
        # unlucky seeds; the original project did the same best-of-N selection)
        results = []  # (score, ids, lottie_json)
        errors = []
        for ci, ids in enumerate(candidates):
            try:
                lj = tokens_to_lottie_json(ids, verbose=False)
            except Exception as e:
                # single-line log: full traceback only when NOTHING decodes
                print(f"[OmniLottie] candidate {ci}: decode failed "
                      f"({type(e).__name__}: {e})")
                errors.append(f"candidate {ci} ({len(ids)} tokens): "
                              f"{type(e).__name__}: {e}")
                continue
            score = _score_lottie(lj, LOTTIE_EOS in ids)
            print(f"[OmniLottie] candidate {ci}: {len(ids)} tokens -> score {score}")
            results.append((score, ids, lj))

        if not results:
            import traceback
            traceback.print_exc()
            raise ValueError(f"OmniLottie: all {len(candidates)} candidates failed to decode:\n"
                             + "\n".join(errors))

        results.sort(key=lambda r: r[0], reverse=True)
        best_score, best_ids, lottie_json = results[0]
        print(f"[OmniLottie] selected candidate with score {best_score} "
              f"({len(results)} decoded)")

        with open(out_path, "w", encoding="utf-8") as f:
            import json
            json.dump(lottie_json, f, ensure_ascii=False, indent=2)
        # archive raw token streams for later diagnosis
        with open(out_path.replace(".json", ".ids.json"), "w", encoding="utf-8") as f:
            import json
            json.dump({"seed": seed, "best_ids": best_ids, "all_candidates": candidates},
                      f, ensure_ascii=False)

        html_path = out_path.replace(".json", ".html")
        save_lottie_html(lottie_json, html_path)
        print(f"[OmniLottie] saved {out_path}")
        return io.NodeOutput(out_path, html_path)


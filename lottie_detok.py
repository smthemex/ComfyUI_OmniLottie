# !/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
Lightweight detokenization for the ComfyUI node path.

`tokens_to_lottie_json` moved here from inference.py so the node no longer
pulls the old wrapper's heavy imports (pandas / datasets / decord /
qwen_vl_utils / accelerate / huggingface_hub) at conversion time.
Depends only on: torch, numpy, stdlib, and the vendored lottie package.
"""

from typing import List

from .lottie.objects.lottie_tokenize import LottieTensor
from .lottie.objects.lottie_param import (
    from_sequence, ShapeLayer, NullLayer, PreCompLayer, TextLayer,
    SolidColorLayer, Font, Chars,
    shape_layer_to_json, null_layer_to_json, precomp_layer_to_json,
    text_layer_to_json, solid_layer_to_json, font_to_json, char_to_json
)
from .app import fix_lottie_json


def tokens_to_lottie_json(generated_ids: List[int], default_json: dict = None, verbose: bool = True):
    if default_json is None:
        default_json = {
            "v": "5.5.2", "fr": 8, "ip": 0, "op": 16,
            "w": 512, "h": 512, "nm": "Animation", "ddd": 0
        }

    if verbose:
        print(f"  Converting {len(generated_ids)} tokens to Lottie JSON...")

    reconstructed_tensor = LottieTensor.from_list(generated_ids)
    reconstructed_sequence = reconstructed_tensor.to_sequence()
    reconstructed = from_sequence(reconstructed_sequence)

    json_animation = {
        "v": reconstructed.get("v", default_json.get("v", "5.5.2")),
        "fr": reconstructed.get("fr", default_json.get("fr", 8)),
        "ip": reconstructed.get("ip", default_json.get("ip", 0)),
        "op": reconstructed.get("op", default_json.get("op", 16)),
        "w": reconstructed.get("w", default_json.get("w", 512)),
        "h": reconstructed.get("h", default_json.get("h", 512)),
        "nm": reconstructed.get("nm", default_json.get("nm", "Animation")),
        "ddd": reconstructed.get("ddd", default_json.get("ddd", 0)),
        "assets": [],
        "layers": [],
    }

    if "markers" in reconstructed:
        json_animation["markers"] = reconstructed.get("markers", [])
    if "props" in reconstructed:
        json_animation["props"] = reconstructed.get("props", {})

    if "fonts" in reconstructed and reconstructed["fonts"]:
        fonts_data = reconstructed["fonts"]
        if isinstance(fonts_data, dict) and "list" in fonts_data:
            fonts_json = {"list": []}
            for font in fonts_data["list"]:
                if isinstance(font, Font):
                    fonts_json["list"].append(font_to_json(font))
                else:
                    fonts_json["list"].append(font)
            json_animation["fonts"] = fonts_json

    if "chars" in reconstructed and reconstructed["chars"]:
        chars_json = []
        for char in reconstructed["chars"]:
            if isinstance(char, Chars):
                chars_json.append(char_to_json(char))
            else:
                chars_json.append(char)
        json_animation["chars"] = chars_json

    for asset in reconstructed.get("assets", []):
        asset_json = dict(asset)
        if "layers" in asset:
            asset_json["layers"] = []
            for layer in asset["layers"]:
                if isinstance(layer, ShapeLayer):
                    asset_json["layers"].append(shape_layer_to_json(layer))
                elif isinstance(layer, NullLayer):
                    asset_json["layers"].append(null_layer_to_json(layer))
                elif isinstance(layer, PreCompLayer):
                    asset_json["layers"].append(precomp_layer_to_json(layer))
                elif isinstance(layer, TextLayer):
                    asset_json["layers"].append(text_layer_to_json(layer))
                elif isinstance(layer, SolidColorLayer):
                    asset_json["layers"].append(solid_layer_to_json(layer))
                else:
                    asset_json["layers"].append(layer)
        json_animation["assets"].append(asset_json)

    for layer in reconstructed.get("layers", []):
        if isinstance(layer, ShapeLayer):
            json_animation["layers"].append(shape_layer_to_json(layer))
        elif isinstance(layer, NullLayer):
            json_animation["layers"].append(null_layer_to_json(layer))
        elif isinstance(layer, PreCompLayer):
            json_animation["layers"].append(precomp_layer_to_json(layer))
        elif isinstance(layer, TextLayer):
            json_animation["layers"].append(text_layer_to_json(layer))
        elif isinstance(layer, SolidColorLayer):
            json_animation["layers"].append(solid_layer_to_json(layer))
        else:
            json_animation["layers"].append(layer)

    json_animation = fix_lottie_json(json_animation)

    return json_animation

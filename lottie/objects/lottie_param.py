from .layers import ShapeLayer, NullLayer, PreCompLayer, TextLayer, SolidColorLayer
from .properties import MultiDimensional, ColorValue
from .nvector import NVector
from .color import Color
from .shapes import *
import json
import re
import ast
import sys
import os
import threading
import concurrent.futures
import multiprocessing
import torch
from .effects import Effect, EffectValueSlider, EffectValueColor, EffectValueAngle, EffectValuePoint, EffectValueCheckbox, IgnoredValue, EffectValueDropDown, EffectValueLayer, EffectNoValue
from .assets import *
from .text import *


class ElementType:
    PRECOMP_LAYER = 0  
    SOLID_LAYER = 1  
    NULL_LAYER = 3 
    SHAPE_LAYER = 4
    TEXT_LAYER = 5  

    GROUP = "gr"
    PATH = "sh"
    STROKE = "st"
    FILL = "fl"
    TRANSFORM = "tr"
    TRIM = "tm"
    RECT = "rc"
    ELLIPSE = "el"
    STAR = "sr"
    REPEATER = "rp"
    GRADIENT_FILL = "gf"        
    GRADIENT_STROKE = "gs"       #
    MERGE = "mm"                 # 
    NO_STYLE = "no"              # 
    OFFSET_PATH = "op"           # 
    PUCKER_BLOAT = "pb"          # 
    ROUNDED_CORNERS = "rd"       # 
    TWIST = "tw"                 # 
    ZIG_ZAG = "zz"               # 

class Keyframe:
    """Represents a single keyframe in an animation"""
    def __init__(self, time, value):
        self.time = time
        self.value = value
        self.in_tan = None  # Incoming Bezier handle
        self.out_tan = None  # Outgoing Bezier handle
        self.h = None  # Hold keyframe flag
        self.to = None
        self.ti = None
        self.n = None  # 
        self.e = None  # 

class Value:
    """Class for single numeric values that can be animated"""
    def __init__(self, value):
        self.value = value
        self.keyframes = []
    
    def add_keyframe(self, time, value):
        """Add a keyframe to this property"""
        kf = Keyframe(time, value)
        self.keyframes.append(kf)
        return kf

# NullLayer

def solid_layer_to_json(layer):
    """SolidColorLayerJSON"""
    json_data = {
        "ddd": 0,
        "ind": layer.index,
        "ty": ElementType.SOLID_LAYER,
        "nm": layer.name,
        "sr": 1,
        "ks": {
            "o": property_to_json(layer.transform.opacity, 100, "ix", 11),
            "r": property_to_json(layer.transform.rotation, 0, "ix", 10),
            "p": property_to_json(layer.transform.position, [0, 0, 0], "ix", 2, "l", 2),
            "a": property_to_json(layer.transform.anchor, [0, 0], "ix", 1, "l", 2),
            "s": property_to_json(layer.transform.scale, [100, 100, 100], "ix", 6, "l", 2)
        },
        "ao": 0,
        "sc": layer.color,
        "sw": layer.width,
        "sh": layer.height,
        "ip": layer.in_point,
        "op": layer.out_point,
        "st": layer.start_time,
        "bm": 0
    }
    # FIX: Add hasMask and masksProperties
    if hasattr(layer, 'hasMask'):
        json_data["hasMask"] = layer.hasMask
    else:
        # Set default value if not present
        json_data["hasMask"] = False
    
    if hasattr(layer, 'masksProperties') and layer.masksProperties:
        json_data["masksProperties"] = layer.masksProperties
    
    # track matte
    if hasattr(layer, 'tt') and layer.tt is not None:
        json_data["tt"] = layer.tt
    if hasattr(layer, 'tp') and layer.tp is not None:
        json_data["tp"] = layer.tp
    if hasattr(layer, 'td') and layer.td is not None:
        json_data["td"] = layer.td
    
    if hasattr(layer, 'ef'):
        json_data["ef"] = effects_to_json(layer.ef)
    
    if hasattr(layer, 'tm'):
        json_data["tm"] = layer.tm
    
    # parent
    if hasattr(layer, 'parent_index') and layer.parent_index is not None:
        json_data["parent"] = layer.parent_index
    elif hasattr(layer, 'parent') and layer.parent is not None:
        if isinstance(layer.parent, (int, float)):
            json_data["parent"] = layer.parent
        elif hasattr(layer.parent, 'index'):
            json_data["parent"] = layer.parent.index
    
    return json_data


def text_layer_to_json(layer):
    """TextLayerJSON"""
    json_data = {
        "ddd": 0,
        "ind": layer.index,
        "ty": ElementType.TEXT_LAYER,
        "nm": layer.name,
        "sr": 1,
        "ks": {
            "o": property_to_json(layer.transform.opacity, 100, "ix", 11),
            "r": property_to_json(layer.transform.rotation, 0, "ix", 10),
            "p": property_to_json(layer.transform.position, [0, 0, 0], "ix", 2, "l", 2),
            "a": property_to_json(layer.transform.anchor, [0, 0], "ix", 1, "l", 2),
            "s": property_to_json(layer.transform.scale, [100, 100, 100], "ix", 6, "l", 2)
        },
        "ao": 0,
        "t": {
            "d": {"k": []},
            "p": {},
            "m": {"g": 1, "a": {"a": 0, "k": [0, 0], "ix": 2}},
            "a": []
        },
        "ip": layer.in_point,
        "op": layer.out_point,
        "st": layer.start_time,
        "bm": 0
    }
    
    # hasMaskTrue
    if hasattr(layer, 'hasMask') and layer.hasMask:
        json_data["hasMask"] = layer.hasMask

    if hasattr(layer, 'masksProperties') and layer.masksProperties:
        json_data["masksProperties"] = layer.masksProperties

    # Text LayerctctNone
    if hasattr(layer, 'ct'):
        json_data["ct"] = layer.ct
    
    #if hasattr(layer, 'ln') and layer.ln is not None:
    #    json_data["ln"] = layer.ln
    
    if hasattr(layer, 'ef'):
        json_data["ef"] = layer.ef
    if hasattr(layer.data, "document") and hasattr(layer.data.document, "value"):
        json_data["t"]["d"]["k"] = layer.data.document.value
    
    if hasattr(layer.data, "path_option") and layer.data.path_option:
        json_data["t"]["p"] = layer.data.path_option
    
    if hasattr(layer.data, "more_options") and layer.data.more_options:
        json_data["t"]["m"] = layer.data.more_options
    
    if hasattr(layer.data, "animators") and layer.data.animators:
        json_data["t"]["a"] = layer.data.animators
    
    # track matte
    if hasattr(layer, 'tt') and layer.tt is not None:
        json_data["tt"] = layer.tt
    if hasattr(layer, 'tp') and layer.tp is not None:
        json_data["tp"] = layer.tp
    if hasattr(layer, 'td') and layer.td is not None:
        json_data["td"] = layer.td
    
    # parent
    if hasattr(layer, 'parent_index') and layer.parent_index is not None:
        json_data["parent"] = layer.parent_index
    elif hasattr(layer, 'parent') and layer.parent is not None:
        if isinstance(layer.parent, (int, float)):
            json_data["parent"] = layer.parent
        elif hasattr(layer.parent, 'index'):
            json_data["parent"] = layer.parent.index
    
    return json_data


#  -
#  -
#  -
#  -
#  -
#  -
#  -
def shape_layer_to_json(layer):
    """Fixed version: All 2D layers should have 'l' parameter"""
    json_data = {
        "ddd": getattr(layer, 'ddd', 0),
        "ind": layer.index,
        "ty": ElementType.SHAPE_LAYER,
        "nm": layer.name,
        "sr": 1,
        "ks": {},
        "ao": getattr(layer, 'ao', 0),
        "shapes": [],
        "ip": layer.in_point,
        "op": layer.out_point,
        "st": layer.start_time,
        "bm": 0
    }
    # hd
    if hasattr(layer, 'hd') and layer.hd is not None:
        json_data["hd"] = layer.hd
    # cpFalse
    if hasattr(layer, 'cp') and layer.cp is not None and layer.cp is not False:
        json_data["cp"] = layer.cp
    # cl
    if hasattr(layer, 'cl') and layer.cl is not None:
        json_data["cl"] = layer.cl

    if hasattr(layer, 'ct'):
        json_data["ct"] = layer.ct

    if hasattr(layer, 'tm'):
        json_data["tm"] = layer.tm

    # hasMaskTrue
    if hasattr(layer, 'hasMask') and layer.hasMask:
        json_data["hasMask"] = layer.hasMask
    if hasattr(layer, 'masksProperties'):
        json_data["masksProperties"] = layer.masksProperties
        
    
    # Build ks with correct parameters based on 3D flag

    ks = {}

    # Check if this is a 3D layer
    is_3d = json_data["ddd"] == 1

    if is_3d:
        # For 3D layers - no ix or l parameters
        ks["o"] = property_to_json(layer.transform.opacity, 100)
        
        # For 3D layers, use separate rotation axes - FIX: Check for rx, ry, rz
        if hasattr(layer.transform, 'rx') and layer.transform.rx is not None:
            ks["rx"] = property_to_json(layer.transform.rx, 0)
        else:
            ks["rx"] = {"a": 0, "k": 0}
            
        if hasattr(layer.transform, 'ry') and layer.transform.ry is not None:
            ks["ry"] = property_to_json(layer.transform.ry, 0)
        else:
            ks["ry"] = {"a": 0, "k": 0}
            
        if hasattr(layer.transform, 'rz') and layer.transform.rz is not None:
            ks["rz"] = property_to_json(layer.transform.rz, 0)
        elif hasattr(layer.transform, 'rotation'):
            ks["rz"] = property_to_json(layer.transform.rotation, 0)
        else:
            ks["rz"] = {"a": 0, "k": 0}

            
        # Orientation for 3D
        if hasattr(layer.transform, 'orientation'):
            ks["or"] = property_to_json(layer.transform.orientation, [0, 0, 0])
        else:
            ks["or"] = {"a": 0, "k": [0, 0, 0]}
        
        # No 'l' parameter for 3D
        ks["p"] = property_to_json(layer.transform.position, [0, 0, 0], "ix", 2)
        ks["a"] = property_to_json(layer.transform.anchor, [0, 0, 0], "ix", 1)
        ks["s"] = property_to_json(layer.transform.scale, [100, 100, 100], "ix", 6)
    
    else:
        # For 2D layers - ALWAYS add ix and l parameters (regardless of asset or main layer)
        ks["o"] = property_to_json(layer.transform.opacity, 100, "ix", 11)
        ks["r"] = property_to_json(layer.transform.rotation, 0, "ix", 10)

        # Position and anchor should have 'l' parameter for 2D but keep 3 dimensions
        ks["p"] = property_to_json(layer.transform.position, [0, 0, 0], "ix", 2, "l", 2)
        ks["a"] = property_to_json(layer.transform.anchor, [0, 0, 0], "ix", 1, "l", 2)

        # Scale ALSO needs 'l' parameter for 2D layers and keeps 3 dimensions
        ks["s"] = property_to_json(layer.transform.scale, [100, 100, 100], "ix", 6, "l", 2)
        
        # Add skew and skew_axis for 2D layers
        if hasattr(layer.transform, 'skew'):
            ks["sk"] = property_to_json(layer.transform.skew, 0, "ix", 2)
        else:
            ks["sk"] = {"a": 0, "k": 0, "ix": 2}
            
        if hasattr(layer.transform, 'skew_axis'):
            ks["sa"] = property_to_json(layer.transform.skew_axis, 0, "ix", 2)
        else:
            ks["sa"] = {"a": 0, "k": 0, "ix": 2}

    #ks["ty"] = "tr"
    json_data["ks"] = ks

    
    # FIX: Always add ef if it exists, even if empty array
    if hasattr(layer, 'ef'):
        json_data["ef"] = layer.ef

    # matte
    if hasattr(layer, 'tt') and layer.tt is not None and layer.tt != 0:
        json_data["tt"] = layer.tt
    if hasattr(layer, 'tp') and layer.tp is not None and layer.tp != 0:
        json_data["tp"] = layer.tp
    if hasattr(layer, 'td') and layer.td is not None and layer.td != 0:
        json_data["td"] = layer.td
    
    # FIX: Handle parent index 0 properly
    if hasattr(layer, 'parent_index') and layer.parent_index is not None:
        json_data["parent"] = layer.parent_index
    elif hasattr(layer, 'parent') and layer.parent is not None:
        if isinstance(layer.parent, (int, float)):
            json_data["parent"] = layer.parent
        elif hasattr(layer.parent, 'index'):
            json_data["parent"] = layer.parent.index
    
    for shape in layer.shapes:
        json_shape = shape_to_json(shape)
        if json_shape:
            json_data["shapes"].append(json_shape)
    
    return json_data
 

def font_to_json(font):
    """FontJSON - Lottie"""
    font_json = {
        "fName": font.name,
        "fFamily": font.font_family,
        "fStyle": font.font_style
    }
    if hasattr(font, 'ascent') and font.ascent is not None:
        font_json["ascent"] = font.ascent
    return font_json


def char_to_json(char):
    """CharsJSON"""
    json_data = {
        "ch": char.character,
        "size": char.font_size,
        "style": char.font_style,
        "w": char.width,
        "fFamily": char.font_family
    }
    
    # shapesshapesdata{}
    if hasattr(char, 'data') and hasattr(char.data, 'shapes') and char.data.shapes:
        # shapesshapes
        json_data["data"] = {"shapes": []}
        for shape in char.data.shapes:
            shape_json = shape_to_json(shape)
            if shape_json:
                json_data["data"]["shapes"].append(shape_json)
    else:
        # shapesdata
        json_data["data"] = {}
    
    return json_data

def extract_string_value(line):
    """"""
    start = line.find('"') + 1
    end = line.rfind('"')
    if start > 0 and end > start:
        return line[start:end]
    return ""

def null_layer_to_json(layer):
    """NullLayerJSON"""
    json_data = {
        "nm": layer.name,
        "ddd": 1 if getattr(layer, 'threedimensional', False) else getattr(layer, 'ddd', 0),
        "ty": layer.type,
        "ind": layer.index,
        "sr": layer.stretch,
        "ip": layer.in_point,
        "op": layer.out_point,
        "st": layer.start_time,
        #"ao": getattr(layer, 'ao', 0),
        #"ao": layer.ao,
        "bm": 0
    }
    # hd
    if hasattr(layer, 'hd') and layer.hd is not None:
        json_data["hd"] = layer.hd
    
    # cl
    if hasattr(layer, 'cl') and layer.cl is not None:
        json_data["cl"] = layer.cl
    # Add ct if it exists
    if hasattr(layer, 'ct') and layer.ct is not None:
        json_data["ct"] = layer.ct
    if hasattr(layer, 'auto_orient') and layer.auto_orient is not None:
        json_data["ao"] = layer.auto_orient
        
    #if hasattr(layer, 'ln'):
    #    json_data["ln"] = layer.ln
    
    # FIX: Always add hasMask (default to False if not present)
    if hasattr(layer, 'hasMask'):
        json_data["hasMask"] = layer.hasMask
    if hasattr(layer, 'hd'):
        json_data["hd"] = layer.hd
    if hasattr(layer, 'cp'):
        json_data["cp"] = layer.cp    
  
    # parentparent
    if hasattr(layer, 'parent_index') and layer.parent_index is not None:
        json_data["parent"] = layer.parent_index
    elif hasattr(layer, 'parent') and layer.parent is not None:
        if isinstance(layer.parent, (int, float)):
            json_data["parent"] = layer.parent
        elif hasattr(layer.parent, 'index'):
            json_data["parent"] = layer.parent.index
    
    
    # track matte
    if hasattr(layer, 'td') and layer.td is not None:
        json_data["td"] = layer.td
    if hasattr(layer, 'tt') and layer.tt is not None:
        json_data["tt"] = layer.tt
    if hasattr(layer, 'tp') and layer.tp is not None:
        json_data["tp"] = layer.tp
    
    if hasattr(layer, 'ef'):
        json_data["ef"] = layer.ef  
          
    #  -
    ks = {}
    
    if layer.transform.anchor is not None:
        ks["a"] = property_to_json(layer.transform.anchor, [0, 0, 0], "ix", 1, "l", 2)
    
    if layer.transform.position is not None:
        # position
        pos_json = property_to_json(layer.transform.position, [0, 0, 0], "ix", 2, "l", 2)
        # positiona
        if hasattr(layer.transform.position, 'animated') and layer.transform.position.animated:
            pos_json["a"] = 1
        elif hasattr(layer.transform.position, 'keyframes') and layer.transform.position.keyframes:
            pos_json["a"] = 1
        ks["p"] = pos_json
    
    # ... rest of transform properties remain the same ...
    if hasattr(layer.transform, 'scale') and layer.transform.scale is not None:
        if hasattr(layer.transform.scale, 'separated') and layer.transform.scale.separated:
            scale_data = {"s": True}
            if hasattr(layer.transform.scale, 'x') and layer.transform.scale.x is not None:
                scale_data["x"] = property_to_json(layer.transform.scale.x, 100)
                if hasattr(layer.transform.scale, 'x_ix'):
                    scale_data["x"]["ix"] = layer.transform.scale.x_ix
            if hasattr(layer.transform.scale, 'y') and layer.transform.scale.y is not None:
                scale_data["y"] = property_to_json(layer.transform.scale.y, 100)
                if hasattr(layer.transform.scale, 'y_ix'):
                    scale_data["y"]["ix"] = layer.transform.scale.y_ix
            if hasattr(layer.transform.scale, 'z') and layer.transform.scale.z is not None:
                scale_data["z"] = property_to_json(layer.transform.scale.z, 100)
                if hasattr(layer.transform.scale, 'z_ix'):
                    scale_data["z"]["ix"] = layer.transform.scale.z_ix
            ks["s"] = scale_data
        else:
            ks["s"] = property_to_json(layer.transform.scale, [100, 100, 100], "ix", 6, "l", 2)
    
    if layer.transform.rotation is not None:
        ks["r"] = property_to_json(layer.transform.rotation, 0, "ix", 10)
    
    if layer.transform.opacity is not None:
        ks["o"] = property_to_json(layer.transform.opacity, 100, "ix", 11)
    
    if hasattr(layer.transform, 'skew') and layer.transform.skew is not None:
        ks["sk"] = property_to_json(layer.transform.skew, 0)
    
    if hasattr(layer.transform, 'skew_axis') and layer.transform.skew_axis is not None:
        ks["sa"] = property_to_json(layer.transform.skew_axis, 0)
    
    json_data["ks"] = ks
    
    return json_data

# PrecompLayer

def precomp_layer_to_json(layer):
    """Convert a PreCompLayer object to JSON format"""
    json_data = {
        "ddd": 0,
        "ind": layer.index,
        "ty": ElementType.PRECOMP_LAYER,
        "nm": layer.name,
        "sr": 1,
        "ks":{},
        "ao": 0,
        "ip": layer.in_point,
        "op": layer.out_point,
        "st": layer.start_time,
        "bm": 0,
        "refId": layer.reference_id
    }
    
    # FIX: Add ln property -
    #if hasattr(layer, 'ln'):
    #    json_data["ln"] = int(layer.ln)
    
    # FIX: Always add hasMask (default to False if not present)
    if hasattr(layer, 'hasMask'):
        json_data["hasMask"] = layer.hasMask
    if hasattr(layer, 'hd'):
        json_data["hd"] = layer.hd

    if hasattr(layer, 'cp'):
        json_data["cp"] = layer.cp
        
    # FIX: Add masksProperties if present
    if hasattr(layer, 'masksProperties') and layer.masksProperties:
        json_data["masksProperties"] = layer.masksProperties
    
    # FIX: Add tm (time remapping) property - None
    if hasattr(layer, 'tm'):
        json_data["tm"] = layer.tm
    
    # FIX: Add w and h if present
    if hasattr(layer, 'w'):
        json_data["w"] = layer.w
    if hasattr(layer, 'h'):
        json_data["h"] = layer.h
    
    # ct
    if hasattr(layer, 'ct') and layer.ct is not None:
        json_data["ct"] = layer.ct
    # effects
    if hasattr(layer, 'ef') and layer.ef is not None:
        json_data["ef"] = layer.ef
    
    # ks
    ks = {}
    
    # opacity
    ks["o"] = property_to_json(layer.transform.opacity, 100, "ix", 11)
    
    # rotation
    ks["r"] = property_to_json(layer.transform.rotation, 0, "ix", 10)
    
    # position - 3
    ks["p"] = property_to_json(layer.transform.position, [0, 0, 0], "ix", 2, "l", 2)
    
    # anchor - 3
    ks["a"] = property_to_json(layer.transform.anchor, [0, 0, 0], "ix", 1, "l", 2)
    
    # scale - 3
    ks["s"] = property_to_json(layer.transform.scale, [100, 100, 100], "ix", 6, "l", 2)
    
    json_data["ks"] = ks
    
    # Add track matte related attributes
    if hasattr(layer, 'tt') and layer.tt is not None:
        json_data["tt"] = layer.tt
    if hasattr(layer, 'tp') and layer.tp is not None:
        json_data["tp"] = layer.tp
    if hasattr(layer, 'td') and layer.td is not None:
        json_data["td"] = layer.td
    
    # Add parent info
    if hasattr(layer, 'parent_index') and layer.parent_index is not None:
        json_data["parent"] = layer.parent_index
    elif hasattr(layer, 'parent') and layer.parent is not None:
        if isinstance(layer.parent, (int, float)):
            json_data["parent"] = layer.parent
        elif hasattr(layer.parent, 'index'):
            json_data["parent"] = layer.parent.index
    
    return json_data
    

def zig_zag_to_json(shape):
    """JSON"""
    json_data = {
        "ty": "zz",
        "nm": shape.name if hasattr(shape, 'name') else "",
        "mn": "ADBE Vector Filter - Zigzag",
        "hd": getattr(shape, 'hd', False),
        "ix": shape.property_index if hasattr(shape, 'property_index') else 1
    }
    
    # ZigZag
    if hasattr(shape, 'frequency') and shape.frequency is not None:
        json_data["r"] = property_to_json(shape.frequency, 5)
    
    if hasattr(shape, 'amplitude') and shape.amplitude is not None:
        json_data["s"] = property_to_json(shape.amplitude, 10)
    
    if hasattr(shape, 'point_type') and shape.point_type is not None:
        json_data["pt"] = property_to_json(shape.point_type, 1)
    
    #
    if hasattr(shape, 'bm') and shape.bm is not None:
        json_data["bm"] = shape.bm
    
    if hasattr(shape, 'cl') and shape.cl is not None:
        json_data["cl"] = shape.cl
    
    #if hasattr(shape, 'ln') and shape.ln is not None:
    #    json_data["ln"] = shape.ln
    
    return json_data



def shape_to_json(shape):
    """JSON"""
    if isinstance(shape, Group):
        return group_to_json(shape)
    elif isinstance(shape, Path):
        return path_to_json(shape)
    elif isinstance(shape, Stroke):
        return stroke_to_json(shape)
    elif isinstance(shape, Fill):
        return fill_to_json(shape)
    elif isinstance(shape, Trim):
        return trim_to_json(shape)
    elif isinstance(shape, Rect):
        return rect_to_json(shape)
    elif isinstance(shape, Ellipse):
        return ellipse_to_json(shape)
    elif isinstance(shape, Star):
        return star_to_json(shape)
    elif isinstance(shape, Repeater):
        return repeater_to_json(shape)
    elif isinstance(shape, TransformShape):  
        return transform_shape_to_json(shape)  # Use the correct function for TransformShape
    elif isinstance(shape, GradientFill):
        return gradient_fill_to_json(shape)
    elif isinstance(shape, GradientStroke):
        return gradient_stroke_to_json(shape)
    elif isinstance(shape, Merge):
        return merge_to_json(shape)
    elif isinstance(shape, RoundedCorners):
        return rounded_corners_to_json(shape)
    elif isinstance(shape, Twist):
        return twist_to_json(shape)
    elif isinstance(shape, ZigZag):
        return zig_zag_to_json(shape)
    else:
        print(f"Warning: : {type(shape)}")
        return None

def group_to_json(group):
    """JSON - np"""
    #
    all_items = []
    
    for item in group.shapes:
        json_item = shape_to_json(item)
        if json_item:
            all_items.append(json_item)
    
    # group.nameNone
    group_name = group.name if group.name is not None else ""
    
    # npit
    if hasattr(group, 'number_of_properties') and group.number_of_properties is not None:
        np_value = group.number_of_properties
    else:
        # npit
        np_value = len(all_items)
    
    # JSON
    json_data = {
        "ty": ElementType.GROUP,
        "it": all_items,
        "nm": group_name,
        "np": int(np_value),  #
        "cix": getattr(group, 'cix', 2),
        "bm": 0,
        "ix": getattr(group, 'property_index', 1),
        "mn": getattr(group, 'mn', "ADBE Vector Group"),
        "hd": getattr(group, 'hd', False)
    }
    
    return json_data



def rect_to_json(rect):
    """JSON"""
    json_data = {
        "ty": ElementType.RECT,
        "nm": rect.name,
        "ix": rect.property_index,
        "d": getattr(rect, 'direction', 1),  #
        "mn": "ADBE Vector Shape - Rect",
        "hd": getattr(rect, 'hd', False)  # hd
    }
    
    #  - ix
    if hasattr(rect, "position") and rect.position:
        json_data["p"] = property_to_json(rect.position, [0, 0], "ix", 3)
    
    #  - ix
    if hasattr(rect, "size") and rect.size:
        json_data["s"] = property_to_json(rect.size, [100, 100], "ix", 2)
    
    #  - ix
    if hasattr(rect, "rounded") and rect.rounded:
        rounded_ix = getattr(rect, 'rounded_ix', 4)  # 41
        json_data["r"] = property_to_json(rect.rounded, 0, "ix", rounded_ix)
        
    return json_data
      

def path_to_json(path):
    """JSON - ind, mn, hd"""
    json_data = {
        "ty": ElementType.PATH,
        "nm": path.name,
    }

    # pathd
    if hasattr(path, 'd') and path.d is not None:
        json_data["d"] = path.d
    
    # ✅ ind
    if hasattr(path, 'ind') and path.ind is not None:
        json_data["ind"] = path.ind
    
    # ixNone
    if hasattr(path, 'property_index') and path.property_index is not None:
        json_data["ix"] = path.property_index
    
    # ✅ mn -
    if hasattr(path, 'mn') and path.mn is not None:
        json_data["mn"] = path.mn
    
    # ✅ hd -
    if hasattr(path, 'hd') and path.hd is not None:
        json_data["hd"] = path.hd
    
    # ks
    ks = {
        "a": 0  #
    }
    
    #
    if hasattr(path.shape, 'keyframes') and path.shape.keyframes:
        #
        ks["a"] = 1
        keyframes = []
        
        for kf in path.shape.keyframes:
            bezier = kf.value
            
            keyframe = {
                "t": kf.time,
                "s": [{
                    "i": [[t.x, t.y] for t in bezier.in_tangents],
                    "o": [[t.x, t.y] for t in bezier.out_tangents],
                    "v": [[v.x, v.y] for v in bezier.vertices],
                    "c": bezier.closed
                }]
            }
            
            # h
            if hasattr(kf, 'h') and kf.h is not None:
                keyframe["h"] = kf.h
            
            #
            if hasattr(kf, 'in_tan') and kf.in_tan:
                #  -
                x_val = kf.in_tan['x']
                y_val = kf.in_tan['y']
                
                #
                if isinstance(x_val, list) and len(x_val) == 1:
                    x_val = x_val[0]
                if isinstance(y_val, list) and len(y_val) == 1:
                    y_val = y_val[0]
                
                #
                if isinstance(x_val, list) or isinstance(y_val, list):
                    keyframe["i"] = {"x": x_val if isinstance(x_val, list) else [x_val], 
                                   "y": y_val if isinstance(y_val, list) else [y_val]}
                else:
                    #
                    keyframe["i"] = {"x": x_val, "y": y_val}
            
            if hasattr(kf, 'out_tan') and kf.out_tan:
                # out_tan
                x_val = kf.out_tan['x']
                y_val = kf.out_tan['y']
                
                #
                if isinstance(x_val, list) and len(x_val) == 1:
                    x_val = x_val[0]
                if isinstance(y_val, list) and len(y_val) == 1:
                    y_val = y_val[0]
                
                #
                if isinstance(x_val, list) or isinstance(y_val, list):
                    keyframe["o"] = {"x": x_val if isinstance(x_val, list) else [x_val],
                                   "y": y_val if isinstance(y_val, list) else [y_val]}
                else:
                    #
                    keyframe["o"] = {"x": x_val, "y": y_val}
            
            keyframes.append(keyframe)
        
        ks["k"] = keyframes
    else:
        #
        bezier = path.shape.value
        
        ks["k"] = {
            "i": [[t.x, t.y] for t in bezier.in_tangents],
            "o": [[t.x, t.y] for t in bezier.out_tangents],
            "v": [[v.x, v.y] for v in bezier.vertices],
            "c": bezier.closed
        }
    
    json_data["ks"] = ks
    
    return json_data



def ellipse_to_json(ellipse):
    """JSON"""
    json_data = {
        "ty": ElementType.ELLIPSE,
        "nm": ellipse.name,
        "ix": ellipse.property_index,
        "d": 1,
        "mn": "ADBE Vector Shape - Ellipse",
        "hd": False
    }
    
    #
    if hasattr(ellipse, "size") and ellipse.size is not None:
        #
        is_animated = hasattr(ellipse.size, 'animated') and ellipse.size.animated

        if is_animated and hasattr(ellipse.size, "value") and hasattr(ellipse.size.value, "components"):
            # keyframes
            components = ellipse.size.value.components
            if isinstance(components, list) and len(components) > 0 and isinstance(components[0], dict):
                json_data["s"] = {
                    "a": 1,
                    "k": components,  # componentskeyframe dict
                    "ix": 2
                }
            else:
                #
                size_value = [components[0], components[1]] if len(components) >= 2 else [723.001, 723.001]
                json_data["s"] = {
                    "a": 0,
                    "k": size_value,
                    "ix": 2
                }
        elif hasattr(ellipse.size, "value"):
            if hasattr(ellipse.size.value, "components"):
                components = ellipse.size.value.components
                size_value = [components[0], components[1]] if len(components) >= 2 else [723.001, 723.001]
            elif hasattr(ellipse.size.value, "x") and hasattr(ellipse.size.value, "y"):
                size_value = [ellipse.size.value.x, ellipse.size.value.y]
            else:
                size_value = [723.001, 723.001]
            json_data["s"] = {
                "a": 0,
                "k": size_value,
                "ix": 2
            }
        else:
            size_value = [723.001, 723.001]  #
            json_data["s"] = {
                "a": 0,
                "k": size_value,
                "ix": 2
            }
    else:
        #
        json_data["s"] = {
            "a": 0,
            "k": [723.001, 723.001],
            "ix": 2
        }
    
    #
    if hasattr(ellipse, "position") and ellipse.position is not None:
        #
        is_animated = hasattr(ellipse.position, 'animated') and ellipse.position.animated

        if is_animated and hasattr(ellipse.position, "value") and hasattr(ellipse.position.value, "components"):
            # keyframes
            components = ellipse.position.value.components
            if isinstance(components, list) and len(components) > 0 and isinstance(components[0], dict):
                json_data["p"] = {
                    "a": 1,
                    "k": components,
                    "ix": 3
                }
            else:
                #
                pos_value = [components[0], components[1]] if len(components) >= 2 else [0, 0]
                json_data["p"] = {
                    "a": 0,
                    "k": pos_value,
                    "ix": 3
                }
        elif hasattr(ellipse.position, "value"):
            if hasattr(ellipse.position.value, "components"):
                components = ellipse.position.value.components
                pos_value = [components[0], components[1]] if len(components) >= 2 else [0, 0]
            elif hasattr(ellipse.position.value, "x") and hasattr(ellipse.position.value, "y"):
                pos_value = [ellipse.position.value.x, ellipse.position.value.y]
            else:
                pos_value = [0, 0]
            json_data["p"] = {
                "a": 0,
                "k": pos_value,
                "ix": 3
            }
        else:
            pos_value = [0, 0]  #
            json_data["p"] = {
                "a": 0,
                "k": pos_value,
                "ix": 3
            }
    else:
        #
        json_data["p"] = {
            "a": 0,
            "k": [0, 0],
            "ix": 3
        }
    
    return json_data

def star_to_json(star):
    """JSON"""
    json_data = {
        "ty": ElementType.STAR,
        "nm": star.name,
        "ix": star.property_index,
        "mn": "ADBE Vector Shape - Star",
        "hd": False
    }
    
    # direction
    if hasattr(star, 'direction'):
        json_data["d"] = star.direction
    else:
        json_data["d"] = 1
    
    # star_type
    if hasattr(star, 'star_type'):
        json_data["sy"] = star.star_type.value if hasattr(star.star_type, 'value') else star.star_type
    else:
        json_data["sy"] = 1  # Star
    
    # ix
    if hasattr(star, "position") and star.position:
        p_json = property_to_json(star.position, [0, 0])
        if hasattr(star, "position_ix"):
            p_json["ix"] = star.position_ix
        else:
            p_json["ix"] = 3
        json_data["p"] = p_json
    
    # ix
    if hasattr(star, "inner_radius") and star.inner_radius:
        ir_json = property_to_json(star.inner_radius, 0)
        if hasattr(star, "inner_radius_ix"):
            ir_json["ix"] = star.inner_radius_ix
        else:
            ir_json["ix"] = 6
        json_data["ir"] = ir_json
    
    # ix
    if hasattr(star, "outer_radius") and star.outer_radius:
        or_json = property_to_json(star.outer_radius, 0)
        if hasattr(star, "outer_radius_ix"):
            or_json["ix"] = star.outer_radius_ix
        else:
            or_json["ix"] = 7
        json_data["or"] = or_json
    
    # ix
    if hasattr(star, "inner_roundness") and star.inner_roundness:
        is_json = property_to_json(star.inner_roundness, 0)
        if hasattr(star, "inner_roundness_ix"):
            is_json["ix"] = star.inner_roundness_ix
        else:
            is_json["ix"] = 10
        json_data["is"] = is_json
    
    # ix
    if hasattr(star, "outer_roundness") and star.outer_roundness:
        os_json = property_to_json(star.outer_roundness, 0)
        if hasattr(star, "outer_roundness_ix"):
            os_json["ix"] = star.outer_roundness_ix
        else:
            os_json["ix"] = 11
        json_data["os"] = os_json
    
    # ix
    if hasattr(star, "points") and star.points:
        pt_json = property_to_json(star.points, 5)
        if hasattr(star, "points_ix"):
            pt_json["ix"] = star.points_ix
        else:
            pt_json["ix"] = 1
        json_data["pt"] = pt_json
    
    # ix
    if hasattr(star, "rotation") and star.rotation:
        r_json = property_to_json(star.rotation, 0)
        if hasattr(star, "rotation_ix"):
            r_json["ix"] = star.rotation_ix
        else:
            r_json["ix"] = 4
        json_data["r"] = r_json
    
    return json_data

def repeater_to_json(repeater):
    """JSON - ix"""
    json_data = {
        "ty": ElementType.REPEATER,
        "nm": repeater.name,
        "ix": repeater.property_index,
        "mn": "ADBE Vector Filter - Repeater",
        "hd": False
    }
    
    #  - ix
    if hasattr(repeater, "copies") and repeater.copies:
        copies_json = property_to_json(repeater.copies, 1)
        if hasattr(repeater, "copies_ix"):
            copies_json["ix"] = repeater.copies_ix
        json_data["c"] = copies_json
    
    #  - ix
    if hasattr(repeater, "offset") and repeater.offset:
        offset_json = property_to_json(repeater.offset, 0)
        if hasattr(repeater, "offset_ix"):
            offset_json["ix"] = repeater.offset_ix
        json_data["o"] = offset_json
    
    # composite mode
    if hasattr(repeater, "composite"):
        json_data["m"] = repeater.composite
    
    #  - ix
    if hasattr(repeater, "transform") and repeater.transform:
        tr_json = {}
        
        # ty
        if hasattr(repeater.transform, "type"):
            tr_json["ty"] = repeater.transform.type
        else:
            tr_json["ty"] = "tr"
        
        # positionix
        if hasattr(repeater.transform, "position"):
            p_json = property_to_json(repeater.transform.position, [0, 0])
            if hasattr(repeater.transform, "position_ix"):
                p_json["ix"] = repeater.transform.position_ix
            tr_json["p"] = p_json
        
        # anchorix
        if hasattr(repeater.transform, "anchor_point"):
            a_json = property_to_json(repeater.transform.anchor, [0, 0])
            if hasattr(repeater.transform, "anchor_ix"):
                a_json["ix"] = repeater.transform.anchor_ix
            tr_json["a"] = a_json
        
        # scaleix
        if hasattr(repeater.transform, "scale"):
            s_json = property_to_json(repeater.transform.scale, [100, 100])
            if hasattr(repeater.transform, "scale_ix"):
                s_json["ix"] = repeater.transform.scale_ix
            tr_json["s"] = s_json
        
        # rotationix
        if hasattr(repeater.transform, "rotation"):
            r_json = property_to_json(repeater.transform.rotation, 0)
            if hasattr(repeater.transform, "rotation_ix"):
                r_json["ix"] = repeater.transform.rotation_ix
            tr_json["r"] = r_json
        
        # start_opacityix
        if hasattr(repeater.transform, "start_opacity"):
            so_json = property_to_json(repeater.transform.start_opacity, 100)
            if hasattr(repeater.transform, "start_opacity_ix"):
                so_json["ix"] = repeater.transform.start_opacity_ix
            tr_json["so"] = so_json
        
        # end_opacityix
        if hasattr(repeater.transform, "end_opacity"):
            eo_json = property_to_json(repeater.transform.end_opacity, 100)
            if hasattr(repeater.transform, "end_opacity_ix"):
                eo_json["ix"] = repeater.transform.end_opacity_ix
            tr_json["eo"] = eo_json
        
        # name
        if hasattr(repeater.transform, "name"):
            tr_json["nm"] = repeater.transform.name
        
        json_data["tr"] = tr_json
    
    return json_data


def property_to_json(prop, default_value, *args):
    """Fixed: Handle separated properties, expressions, spatial interpolation, and e field"""
    extra_params = {}
    for i in range(0, len(args), 2):
        if i + 1 < len(args):
            extra_params[args[i]] = args[i+1]
    
    # Handle separated properties
    if hasattr(prop, "separated") and prop.separated:
        json_data = {"s": True}
        
        # Check for expression on the separated property itself
        if hasattr(prop, "expression") and prop.expression:
            json_data["x"] = prop.expression
        
        # Calculate correct default values for separated components
        if isinstance(default_value, list):
            x_default = default_value[0] if len(default_value) > 0 else 0
            y_default = default_value[1] if len(default_value) > 1 else 0
            z_default = default_value[2] if len(default_value) > 2 else 0
        else:
            x_default = y_default = z_default = default_value
        
        # Process separated x component (only if it exists as a dict property)
        if hasattr(prop, "x") and prop.x is not None and not isinstance(prop.x, str):
            x_json = property_to_json(prop.x, x_default)
            if hasattr(prop, 'x_ix'):
                x_json["ix"] = prop.x_ix
            else:
                x_json["ix"] = 3
            json_data["x"] = x_json
            
        if hasattr(prop, "y") and prop.y is not None:
            y_json = property_to_json(prop.y, y_default)
            if hasattr(prop, 'y_ix'):
                y_json["ix"] = prop.y_ix
            else:
                y_json["ix"] = 4
            json_data["y"] = y_json
            
        if hasattr(prop, "z") and prop.z is not None:
            z_json = property_to_json(prop.z, z_default)
            if hasattr(prop, 'z_ix'):
                z_json["ix"] = prop.z_ix
            else:
                z_json["ix"] = 5
            json_data["z"] = z_json
        
        # Add animated flag if present
        if hasattr(prop, "animated") and prop.animated:
            json_data["a"] = 1
        
        # Preserve the main ix value
        if hasattr(prop, "ix") and prop.ix is not None:
            json_data["ix"] = prop.ix
        elif "ix" in extra_params:
            json_data["ix"] = extra_params["ix"]
        
        return json_data
    
    # Handle keyframe animation (non-separated)
    if hasattr(prop, "keyframes") and prop.keyframes:
        keyframes = []
        for kf in prop.keyframes:
            keyframe = {"t": kf.time}
            
            # Format value
            if isinstance(kf.value, list):
                keyframe["s"] = kf.value
            elif hasattr(kf.value, "components"):
                keyframe["s"] = list(kf.value.components)
            else:
                keyframe["s"] = [kf.value]
            
            # Add e field (end value) if it exists
            if hasattr(kf, "e") and kf.e is not None:
                if isinstance(kf.e, list):
                    keyframe["e"] = kf.e
                elif hasattr(kf.e, "components"):
                    keyframe["e"] = list(kf.e.components)
                else:
                    keyframe["e"] = [kf.e]
            
            # Add h attribute only if it exists and is not None
            if hasattr(kf, "h") and kf.h is not None:
                keyframe["h"] = kf.h
            
            # Add spatial interpolation (to/ti)
            if hasattr(kf, "to") and kf.to:
                keyframe["to"] = kf.to
            if hasattr(kf, "ti") and kf.ti:
                keyframe["ti"] = kf.ti
                
            # Add n attribute
            if hasattr(kf, "n") and kf.n is not None:
                keyframe["n"] = kf.n
            
            # Add easing - DO NOT wrap in list unless already a list
            if hasattr(kf, "in_tan") and kf.in_tan:
                x_val = kf.in_tan["x"]
                y_val = kf.in_tan["y"]
                # Only wrap in list if the value isn't already a list
                if not isinstance(x_val, list):
                    x_val = x_val
                if not isinstance(y_val, list):
                    y_val = y_val
                keyframe["i"] = {"x": x_val, "y": y_val}
                
            if hasattr(kf, "out_tan") and kf.out_tan:
                x_val = kf.out_tan["x"]
                y_val = kf.out_tan["y"]
                # Only wrap in list if the value isn't already a list
                if not isinstance(x_val, list):
                    x_val = x_val
                if not isinstance(y_val, list):
                    y_val = y_val
                keyframe["o"] = {"x": x_val, "y": y_val}
            

            keyframes.append(keyframe)
        
        json_data = {"a": 1, "k": keyframes}
    
    else:
        # Static property
        if hasattr(prop, "value"):
            value = prop.value
            
            if hasattr(value, "components"):
                k_value = list(value.components)
            elif hasattr(value, "r") and hasattr(value, "g") and hasattr(value, "b"):
                k_value = [value.r, value.g, value.b]
                if hasattr(value, "a"):
                    k_value.append(value.a)
            elif isinstance(value, list):
                k_value = value
            else:
                k_value = value
            
            # Check if animated flag is set
            is_animated = 0
            if hasattr(prop, 'animated') and prop.animated:
                is_animated = 1
            elif hasattr(prop, 'expression') and prop.expression:
                is_animated = 1
            
            json_data = {"a": is_animated, "k": k_value}
        else:
            json_data = {"a": 0, "k": default_value}
    
    # Add expression if exists (for non-separated properties)
    if hasattr(prop, "expression") and prop.expression and not hasattr(prop, "separated"):
        json_data["x"] = prop.expression
    
    # Add 'l' parameter for 2D layer transforms
    if "l" in extra_params:
        json_data["l"] = extra_params["l"]
    
    # Add 'ix' only if explicitly requested
    if "ix" in extra_params:
        json_data["ix"] = extra_params["ix"]
    
    # Add 'a' parameter if specified
    if "a" in extra_params:
        json_data["a"] = extra_params["a"]
    
    return json_data

def stroke_to_json(stroke):
    """JSON"""
    json_data = {
        "ty": ElementType.STROKE,
        "bm": 0,
        "nm": stroke.name,
        "mn": "ADBE Vector Graphic - Stroke",
        "hd": False,
    }
    
    # Color -

    # FIX: Color - properly handle animated colors with keyframes
    if hasattr(stroke.color, 'keyframes') and stroke.color.keyframes:
        # Animated color
        keyframes = []
        for kf in stroke.color.keyframes:
            # Respect original dimensions
            color_dim = getattr(stroke, 'color_dimensions', 4)
            if color_dim == 2:
                s_data = [kf.value.r, kf.value.g]
            elif color_dim == 3:
                s_data = [kf.value.r, kf.value.g, kf.value.b]
            else:
                s_data = [kf.value.r, kf.value.g, kf.value.b, 1]
            
            kf_data = {
                "s": s_data,
                "t": kf.time
            }
            
            # Add easing if present
            if hasattr(kf, 'in_tan') and kf.in_tan:
                kf_data["i"] = kf.in_tan
            if hasattr(kf, 'out_tan') and kf.out_tan:
                kf_data["o"] = kf.out_tan
            
            keyframes.append(kf_data)
        
        # Output with "k" containing keyframes array directly (no "a" field needed when animated)
        json_data["c"] = {"k": keyframes}
        
        # Add ix if originally present
        if hasattr(stroke, 'has_c_ix') and stroke.has_c_ix:
            json_data["c"]["ix"] = getattr(stroke, 'c_ix', 3)
    else:
        # Static color
        color_dim = getattr(stroke, 'color_dimensions', 3)
        has_c_a = getattr(stroke, 'has_c_a', False)
        has_c_ix = getattr(stroke, 'has_c_ix', False)
        
        color_array = []
        if color_dim == 1:
            color_array = [stroke.color.value.r]
        elif color_dim == 2:
            color_array = [stroke.color.value.r, stroke.color.value.g]
        elif color_dim == 3:
            color_array = [stroke.color.value.r, stroke.color.value.g, stroke.color.value.b]
        else:  # 4 or more
            color_array = [stroke.color.value.r, stroke.color.value.g, stroke.color.value.b, 1]
        
        json_data["c"] = {"k": color_array}
        if has_c_a:
            json_data["c"]["a"] = 0
        if has_c_ix:
            json_data["c"]["ix"] = getattr(stroke, 'c_ix', 3)
    

    # Opacity - FIX: Handle animated opacity
    if hasattr(stroke.opacity, 'keyframes') and stroke.opacity.keyframes:
        # Animated opacity
        keyframes = []
        for kf in stroke.opacity.keyframes:
            kf_data = {
                "t": kf.time,
                "s": [kf.value]  # Opacity value as single-element array
            }
            
            # Add easing parameters if present
            if hasattr(kf, 'in_tan') and kf.in_tan:
                if isinstance(kf.in_tan, dict):
                    kf_data["i"] = {
                        "x": [kf.in_tan.get('x', 0.833)],
                        "y": [kf.in_tan.get('y', 0.833)]
                    }
                else:
                    kf_data["i"] = kf.in_tan
            
            if hasattr(kf, 'out_tan') and kf.out_tan:
                if isinstance(kf.out_tan, dict):
                    kf_data["o"] = {
                        "x": [kf.out_tan.get('x', 0.167)],
                        "y": [kf.out_tan.get('y', 0.167)]
                    }
                else:
                    kf_data["o"] = kf.out_tan
            
            keyframes.append(kf_data)
        
        json_data["o"] = {
            "a": 1,
            "k": keyframes,
            "ix": 4
        }
    else:
        # Static opacity
        json_data["o"] = {
            "a": 0,
            "k": stroke.opacity.value,
            "ix": 4
        }
    
    # Width - FIX: Handle animated width
    if hasattr(stroke.width, 'keyframes') and stroke.width.keyframes:
        # Animated width
        keyframes = []
        for kf in stroke.width.keyframes:
            kf_data = {
                "t": kf.time,
                "s": [kf.value]  # Width value as single-element array
            }
            
            # Add easing parameters if present
            if hasattr(kf, 'in_tan') and kf.in_tan:
                if isinstance(kf.in_tan, dict):
                    kf_data["i"] = {
                        "x": [kf.in_tan.get('x', 0.833)],
                        "y": [kf.in_tan.get('y', 0.833)]
                    }
                else:
                    kf_data["i"] = kf.in_tan
            
            if hasattr(kf, 'out_tan') and kf.out_tan:
                if isinstance(kf.out_tan, dict):
                    kf_data["o"] = {
                        "x": [kf.out_tan.get('x', 0.167)],
                        "y": [kf.out_tan.get('y', 0.167)]
                    }
                else:
                    kf_data["o"] = kf.out_tan
            
            keyframes.append(kf_data)
        
        json_data["w"] = {
            "a": 1,
            "k": keyframes,
            "ix": 5
        }
    else:
        # Static width
        json_data["w"] = {
            "a": 0,
            "k": stroke.width.value,
            "ix": 5
        }
    
    # Line cap and join
    json_data["lc"] = stroke.line_cap.value if hasattr(stroke, "line_cap") and stroke.line_cap else 2
    json_data["lj"] = stroke.line_join.value if hasattr(stroke, "line_join") and stroke.line_join else 2
    
    # Miter limit - FIX: Output ml whenever it exists, regardless of line_join value
    if hasattr(stroke, "miter_limit") and stroke.miter_limit is not None:
        json_data["ml"] = stroke.miter_limit
    
    # ml2
    if hasattr(stroke, "ml2") and stroke.ml2 is not None:
        if isinstance(stroke.ml2, Value):
            if hasattr(stroke.ml2, 'keyframes') and stroke.ml2.keyframes:
                # Animated ml2
                keyframes = []
                for kf in stroke.ml2.keyframes:
                    kf_data = {
                        "t": kf.time,
                        "s": [kf.value] if not isinstance(kf.value, list) else kf.value
                    }
                    
                    if hasattr(kf, 'in_tan') and kf.in_tan:
                        kf_data["i"] = kf.in_tan
                    if hasattr(kf, 'out_tan') and kf.out_tan:
                        kf_data["o"] = kf.out_tan
                    
                    keyframes.append(kf_data)
                
                ml2_json = {"a": 1, "k": keyframes}
            else:
                ml2_json = {"a": 0, "k": stroke.ml2.value}
            
            if hasattr(stroke, 'ml2_ix') and stroke.ml2_ix is not None:
                ml2_json["ix"] = stroke.ml2_ix
            
            json_data["ml2"] = ml2_json
        else:
            json_data["ml2"] = stroke.ml2
    
    # Dashes - FIX: Handle animated dash lengths
    if hasattr(stroke, "dashes") and stroke.dashes:
        dash_array = []
        for i, dash in enumerate(stroke.dashes):
            dash_item = {"n": dash.type.value if hasattr(dash.type, 'value') else dash.type}
            
            # Check if dash length is animated
            if hasattr(dash.length, 'keyframes') and dash.length.keyframes:
                # Animated dash length
                keyframes = []
                for kf in dash.length.keyframes:
                    kf_data = {
                        "t": kf.time,
                        "s": [kf.value]
                    }
                    
                    # ADD: Include hold property if present
                    if hasattr(kf, 'hold'):
                        kf_data["h"] = kf.hold
                    
                    # Only add easing if not a hold keyframe
                    if not hasattr(kf, 'hold') or not kf.hold:
                        if hasattr(kf, 'in_tan') and kf.in_tan:
                            if isinstance(kf.in_tan, dict):
                                kf_data["i"] = {
                                    "x": [kf.in_tan.get('x', 0.833)],
                                    "y": [kf.in_tan.get('y', 0.833)]
                                }
                        
                        if hasattr(kf, 'out_tan') and kf.out_tan:
                            if isinstance(kf.out_tan, dict):
                                kf_data["o"] = {
                                    "x": [kf.out_tan.get('x', 0.167)],
                                    "y": [kf.out_tan.get('y', 0.167)]
                                }
                    
                    keyframes.append(kf_data)
                
                dash_item["v"] = {
                    "a": 1,
                    "k": keyframes
                }
            else:
                # Static dash length
                dash_item["v"] = {
                    "a": 0, 
                    "k": dash.length.value if hasattr(dash.length, 'value') else dash.length
                }
            
            # Add name
            if hasattr(dash, 'name') and dash.name:
                dash_item["nm"] = dash.name
            else:
                if dash.type == StrokeDashType.Dash or dash.type == "d":
                    dash_item["nm"] = "dash"
                elif dash.type == StrokeDashType.Gap or dash.type == "g":
                    dash_item["nm"] = "gap"
                elif dash.type == StrokeDashType.Offset or dash.type == "o":
                    dash_item["nm"] = "offset"
            
            if hasattr(dash, 'v_ix'):
                dash_item["v"]["ix"] = dash.v_ix
            else:
                dash_item["v"]["ix"] = i + 1
            
            dash_array.append(dash_item)
        
        json_data["d"] = dash_array
    
    # ix
    if hasattr(stroke, 'property_index') and stroke.property_index is not None:
        json_data["ix"] = stroke.property_index
    
    return json_data

def fill_to_json(fill):
    """Fixed: Support animated colors and variable color dimensions"""
    json_data = {
        "ty": ElementType.FILL,
        "bm": 0,
        "nm": fill.name,
        "mn": getattr(fill, 'mn', "ADBE Vector Graphic - Fill"),
        "hd": getattr(fill, 'hd', False)
    }
    
    # Color -
    if hasattr(fill.color, 'keyframes') and fill.color.keyframes:
        #
        keyframes = []
        for kf in fill.color.keyframes:
            #
            color_dim = getattr(fill, 'color_dimensions', 4)
            if color_dim == 2:
                s_data = [kf.value.r, kf.value.g]
            elif color_dim == 3:
                s_data = [kf.value.r, kf.value.g, kf.value.b]
            else:
                s_data = [kf.value.r, kf.value.g, kf.value.b, 1]
            
            kf_data = {
                "t": kf.time,
                "s": s_data
            }
            if hasattr(kf, 'in_tan') and kf.in_tan:
                kf_data["i"] = kf.in_tan
            if hasattr(kf, 'out_tan') and kf.out_tan:
                kf_data["o"] = kf.out_tan
            keyframes.append(kf_data)
        
        json_data["c"] = {"a": 1, "k": keyframes}
        
        # ix
        if hasattr(fill, 'has_c_ix') and fill.has_c_ix:
            json_data["c"]["ix"] = getattr(fill, 'c_ix', 4)
    else:
        # FIX: Respect actual color dimensions
        color_dim = getattr(fill, 'color_dimensions', 3)
        has_c_a = getattr(fill, 'has_c_a', False)
        has_c_ix = getattr(fill, 'has_c_ix', False)
        
        color_array = []
        if color_dim == 1:
            color_array = [fill.color.value.r]
        elif color_dim == 2:
            color_array = [fill.color.value.r, fill.color.value.g]
        elif color_dim == 3:
            color_array = [fill.color.value.r, fill.color.value.g, fill.color.value.b]
        else:  # 4 or more
            color_array = [fill.color.value.r, fill.color.value.g, fill.color.value.b, 1]
        
        json_data["c"] = {"k": color_array}
        if has_c_a:
            json_data["c"]["a"] = 0
        if has_c_ix:
            json_data["c"]["ix"] = getattr(fill, 'c_ix', 4)
    
    # Opacity
    json_data["o"] = {
        "a": 0,
        "k": fill.opacity.value,
        "ix": 5
    }
    
    # Check if opacity is animated
    if hasattr(fill.opacity, 'keyframes') and fill.opacity.keyframes:
        json_data["o"]["a"] = 1
        keyframes = []
        for kf in fill.opacity.keyframes:
            keyframe = {"t": kf.time, "s": [kf.value]}
            if hasattr(kf, 'in_tan') and kf.in_tan:
                keyframe["i"] = {"x": [kf.in_tan['x']], "y": [kf.in_tan['y']]}
            if hasattr(kf, 'out_tan') and kf.out_tan:
                keyframe["o"] = {"x": [kf.out_tan['x']], "y": [kf.out_tan['y']]}
            keyframes.append(keyframe)
        json_data["o"]["k"] = keyframes
    
    # Fill rule
    json_data["r"] = fill.fill_rule.value if hasattr(fill, "fill_rule") and fill.fill_rule is not None else 1
    
    # Add property index to fill element itself if it exists
    if hasattr(fill, 'property_index') and fill.property_index is not None:
        json_data["ix"] = fill.property_index
    
    return json_data


def gradient_fill_to_json(gradient_fill):
    """JSON - """
    json_data = {
        "ty": ElementType.GRADIENT_FILL,
        "nm": gradient_fill.name,
        "o": {"a": 0, "k": gradient_fill.opacity.value if hasattr(gradient_fill, "opacity") else 100, "ix": 10},
        "r": gradient_fill.fill_rule.value if hasattr(gradient_fill, "fill_rule") and gradient_fill.fill_rule is not None else 1,
        "bm": 0,
        "mn": "ADBE Vector Graphic - G-Fill",
        "hd": False
    }
    
    # Add property index if exists
    if hasattr(gradient_fill, 'property_index') and gradient_fill.property_index is not None:
        json_data["ix"] = gradient_fill.property_index
    
    # Start and end points
    if hasattr(gradient_fill, "start_point"):
        json_data["s"] = property_to_json(gradient_fill.start_point, [0, 0], "ix", 5)
    else:
        json_data["s"] = {"a": 0, "k": [0, 0], "ix": 5}
    
    if hasattr(gradient_fill, "end_point"):
        json_data["e"] = property_to_json(gradient_fill.end_point, [100, 100], "ix", 6)
    else:
        json_data["e"] = {"a": 0, "k": [100, 100], "ix": 6}
    
    # Gradient type
    gradient_type = 1  # Default linear
    if hasattr(gradient_fill, "gradient_type"):
        gradient_type = gradient_fill.gradient_type.value
        json_data["t"] = gradient_type
    else:
        json_data["t"] = 1
    
    # FIX: Always add h and a attributes if they exist
    if hasattr(gradient_fill, "highlight_length"):
        json_data["h"] = property_to_json(gradient_fill.highlight_length, 0, "ix", 7)
    
    if hasattr(gradient_fill, "highlight_angle"):
        json_data["a"] = property_to_json(gradient_fill.highlight_angle, 0, "ix", 8)
    
    #  -
    if hasattr(gradient_fill, "_original_color_array") and gradient_fill._original_color_array:
        #
        json_data["g"] = {
            "p": gradient_fill._color_points,
            "k": {
                "a": 0,
                "k": gradient_fill._original_color_array,
                "ix": 9
            }
        }
    elif hasattr(gradient_fill, "colors") and gradient_fill.colors is not None:
        #
        if hasattr(gradient_fill.colors, "colors"):
            colors_list = gradient_fill.colors.colors
            
            if isinstance(colors_list, list) and colors_list:
                flat_colors = []
                num_colors = len(colors_list)
                
                # 4rgb
                for pos, color in colors_list:
                    flat_colors.extend([pos, color.r, color.g, color.b])
                
                json_data["g"] = {
                    "p": num_colors,
                    "k": {
                        "a": 0,
                        "k": flat_colors,
                        "ix": 9
                    }
                }
            else:
                #
                json_data["g"] = {
                    "p": 3,
                    "k": {
                        "a": 0,
                        "k": [0.0, 0.85, 0.36, 0.33, 0.5, 0.84, 1.0, 0.0, 1.0, 0.85, 0.36, 0.33],
                        "ix": 9
                    }
                }
    else:
        #
        json_data["g"] = {
            "p": 3,
            "k": {
                "a": 0,
                "k": [0.0, 0.85, 0.36, 0.33, 0.5, 0.84, 1.0, 0.0, 1.0, 0.85, 0.36, 0.33],
                "ix": 9
            }
        }
    
    return json_data
    

def gradient_stroke_to_json(shape):
    """JSON - """
    json_data = {
        "ty": ElementType.GRADIENT_STROKE,
        "nm": shape.name,
        "bm": 0,
        "mn": "ADBE Vector Graphic - G-Stroke",
        "hd": False
    }
    
    # property_index
    if hasattr(shape, 'property_index') and shape.property_index is not None:
        json_data["ix"] = shape.property_index
    
    #  - ix
    json_data["o"] = {
        "a": 0,
        "k": shape.opacity.value if hasattr(shape, "opacity") else 100,
        "ix": 9  # ix
    }
    
    #  - ix
    json_data["w"] = {
        "a": 0,
        "k": shape.width.value if hasattr(shape, "width") else 14,  #
        "ix": 10  # ix
    }
    
    #  -
    json_data["lc"] = shape.line_cap.value if hasattr(shape, "line_cap") and shape.line_cap is not None else 1
    json_data["lj"] = shape.line_join.value if hasattr(shape, "line_join") and shape.line_join is not None else 1
    
    #
    if hasattr(shape, "miter_limit") and shape.miter_limit is not None:
        json_data["ml"] = shape.miter_limit
    
    # ml2
    if hasattr(shape, "ml2") and shape.ml2 is not None:
        if isinstance(shape.ml2, Value):
            ml2_json = {"a": 0, "k": shape.ml2.value}
            if hasattr(shape, 'ml2_ix'):
                ml2_json["ix"] = shape.ml2_ix
            json_data["ml2"] = ml2_json
        else:
            json_data["ml2"] = shape.ml2
    
    #  - ix
    if hasattr(shape, "start_point"):
        json_data["s"] = property_to_json(shape.start_point, [0, 0], "ix", 4)
    else:
        json_data["s"] = {"a": 0, "k": [0, 0], "ix": 4}
    
    #  - ix
    if hasattr(shape, "end_point"):
        json_data["e"] = property_to_json(shape.end_point, [100, 0], "ix", 5)  #
    else:
        json_data["e"] = {"a": 0, "k": [100, 0], "ix": 5}  #
    
    #
    json_data["t"] = shape.gradient_type.value if hasattr(shape, "gradient_type") else 1
    
    #
    if hasattr(shape, "highlight_length"):
        json_data["h"] = property_to_json(shape.highlight_length, 0, "ix", 7)
    else:
        json_data["h"] = {"a": 0, "k": 0, "ix": 7}
    
    if hasattr(shape, "highlight_angle"):
        json_data["a"] = property_to_json(shape.highlight_angle, 0, "ix", 8)
    else:
        json_data["a"] = {"a": 0, "k": 0, "ix": 8}
    
    #  -
    if hasattr(shape, "_original_g_data") and shape._original_g_data:
        #
        json_data["g"] = shape._original_g_data
    elif hasattr(shape, "_original_color_array") and shape._original_color_array:
        #
        json_data["g"] = {
            "p": shape._color_points,
            "k": {
                "a": 0,
                "k": shape._original_color_array,
                "ix": 8  # 89
            }
        }
    elif hasattr(shape, "colors") and shape.colors:
        # ...  ...
        json_data["g"] = {
            "p": len(colors_list) if 'colors_list' in locals() else 3,
            "k": {
                "a": 0,
                "k": flat_colors if 'flat_colors' in locals() else [0, 0, 0, 0, 0.5, 1, 1, 1, 1, 0, 0, 0],
                "ix": 8  # 89
            }
        }
    else:
        #  - 312
        json_data["g"] = {
            "p": 3,
            "k": {
                "a": 0,
                "k": [0, 0, 0, 0, 0.5, 1, 1, 1, 1, 0, 0, 0],
                "ix": 8  # 89
            }
        }
    
    #
    if hasattr(shape, "dashes") and shape.dashes:
        dash_array = []
        for dash in shape.dashes:
            dash_item = {
                "n": dash.type.value,
                "v": {"a": 0, "k": dash.length.value}
            }
            dash_array.append(dash_item)
        json_data["d"] = dash_array
    
    return json_data
    
#  - JSON
def merge_to_json(merge):
    """JSON"""
    json_data = {
        "ty": ElementType.MERGE,
        "nm": merge.name,
        "mm": merge.merge_mode,
        "mn": "ADBE Vector Filter - Merge",
        "hd": False
    }
    
    if hasattr(merge, "property_index") and merge.property_index is not None:
        json_data["ix"] = merge.property_index
    
    return json_data

#  - JSON
def rounded_corners_to_json(rounded_corners):
    """JSON"""
    json_data = {
        "ty": ElementType.ROUNDED_CORNERS,
        "nm": rounded_corners.name,
        "mn": "ADBE Vector Filter - RC",
        "hd": False
    }
    
    if hasattr(rounded_corners, "property_index") and rounded_corners.property_index is not None:
        json_data["ix"] = rounded_corners.property_index
    
    #
    if hasattr(rounded_corners, "radius"):
        json_data["r"] = property_to_json(rounded_corners.radius, 0, "ix", 1)
    
    return json_data

#  - JSON
def twist_to_json(twist):
    """JSON"""
    json_data = {
        "ty": ElementType.TWIST,
        "nm": twist.name,
        "mn": "ADBE Vector Filter - Twist",
        "hd": False
    }
    
    if hasattr(twist, "property_index") and twist.property_index is not None:
        json_data["ix"] = twist.property_index
    
    #
    if hasattr(twist, "angle"):
        json_data["a"] = property_to_json(twist.angle, 0, "ix", 1)
    
    #
    if hasattr(twist, "center"):
        json_data["c"] = property_to_json(twist.center, [0, 0], "ix", 2)
    
    return json_data


def trim_to_json(trim):
    """Convert a Trim object to JSON, properly handling animations"""
    json_data = {
        "ty": ElementType.TRIM,
        "nm": trim.name,
        "ix": trim.property_index,
        "mn": "ADBE Vector Filter - Trim",
        "hd": False
    }
    
    #
    if hasattr(trim, "multiple"):
        json_data["m"] = trim.multiple.value
    else:
        json_data["m"] = 1  #
        
    # Start value
    if hasattr(trim, "start") and trim.start:
        json_data["s"] = property_to_json(trim.start, 0, "ix", 1)
    
    # End value
    if hasattr(trim, "end") and trim.end:
        json_data["e"] = property_to_json(trim.end, 100, "ix", 2)
    
    # Offset value
    if hasattr(trim, "offset") and trim.offset:
        json_data["o"] = property_to_json(trim.offset, 0, "ix", 3)
    
    return json_data

def effects_to_json(effects):
    """JSON"""
    if not isinstance(effects, list):
        effects = [effects]  #
    
    json_effects = []
    
    for effect in effects:
        # effect
        if isinstance(effect, dict) and "ty" in effect:
            json_effect = {
                "ty": effect.get("ty", 5),
                "nm": effect.get("nm", ""),
                "mn": effect.get("mn", ""),
                "ix": effect.get("ix", 1),
                "en": effect.get("en", 1)
            }
            
            # np0
            if "np" in effect and effect["np"] > 0:
                json_effect["np"] = effect["np"]
            
            #
            if "ef" in effect:
                json_effect["ef"] = effect["ef"]
            
            json_effects.append(json_effect)
    
    return json_effects
    

# JSON
def transform_shape_to_json(transform):
    """Convert TransformShape to JSON with full separated properties support"""
    json_data = {
        "ty": "tr",
        "nm": transform.name if hasattr(transform, 'name') else "Transform Shape"
    }
    
    if hasattr(transform, 'property_index') and transform.property_index is not None:
        json_data["ix"] = transform.property_index
    
    if hasattr(transform, 'hd') and transform.hd is not None:
        json_data["hd"] = transform.hd
    # Process anchor
    if hasattr(transform, 'anchor') and transform.anchor is not None:
        json_data["a"] = property_to_json(transform.anchor, [0, 0])
        if not hasattr(transform, '_is_shape_transform'):
            json_data["a"]["ix"] = 1
    
    # Process position
    if hasattr(transform, 'position') and transform.position is not None:
        json_data["p"] = property_to_json(transform.position, [0, 0])
        if not hasattr(transform, '_is_shape_transform'):
            json_data["p"]["ix"] = 2
    
    # Process scale - FIXED: Properly output separated properties
    if hasattr(transform, 'scale') and transform.scale is not None:
        if hasattr(transform.scale, 'separated') and transform.scale.separated:
            # Output separated scale
            scale_json = {"s": True}
            
            if hasattr(transform.scale, 'x') and transform.scale.x is not None:
                scale_json["x"] = property_to_json(transform.scale.x, 100)
                if hasattr(transform.scale, 'x_ix'):
                    scale_json["x"]["ix"] = transform.scale.x_ix
                else:
                    scale_json["x"]["ix"] = 3
            
            if hasattr(transform.scale, 'y') and transform.scale.y is not None:
                scale_json["y"] = property_to_json(transform.scale.y, 100)
                if hasattr(transform.scale, 'y_ix'):
                    scale_json["y"]["ix"] = transform.scale.y_ix
                else:
                    scale_json["y"]["ix"] = 4
            
            if hasattr(transform.scale, 'z') and transform.scale.z is not None:
                scale_json["z"] = property_to_json(transform.scale.z, 100)
                if hasattr(transform.scale, 'z_ix'):
                    scale_json["z"]["ix"] = transform.scale.z_ix
                else:
                    scale_json["z"]["ix"] = 5
            
            if hasattr(transform.scale, 'ix'):
                scale_json["ix"] = transform.scale.ix
            elif not hasattr(transform, '_is_shape_transform'):
                scale_json["ix"] = 3
            
            json_data["s"] = scale_json
        else:
            scale_json = property_to_json(transform.scale, [100, 100, 100])
            if not hasattr(transform, '_is_shape_transform'):
                scale_json["ix"] = 3
            json_data["s"] = scale_json
    
    # Process rotation - FIXED: Handle separated rotation
    if hasattr(transform, 'rotation') and transform.rotation is not None:
        if hasattr(transform.rotation, 'separated') and transform.rotation.separated:
            # Output separated rotation
            rot_json = {"s": True}
            
            if hasattr(transform.rotation, 'x') and transform.rotation.x is not None:
                rot_json["x"] = property_to_json(transform.rotation.x, 0)
                if hasattr(transform.rotation, 'x_ix'):
                    rot_json["x"]["ix"] = transform.rotation.x_ix
            
            if hasattr(transform.rotation, 'y') and transform.rotation.y is not None:
                rot_json["y"] = property_to_json(transform.rotation.y, 0)
                if hasattr(transform.rotation, 'y_ix'):
                    rot_json["y"]["ix"] = transform.rotation.y_ix
            
            if hasattr(transform.rotation, 'z') and transform.rotation.z is not None:
                rot_json["z"] = property_to_json(transform.rotation.z, 0)
                if hasattr(transform.rotation, 'z_ix'):
                    rot_json["z"]["ix"] = transform.rotation.z_ix
            
            if hasattr(transform.rotation, 'ix'):
                rot_json["ix"] = transform.rotation.ix
            elif not hasattr(transform, '_is_shape_transform'):
                rot_json["ix"] = 6
            
            json_data["r"] = rot_json
        else:
            json_data["r"] = property_to_json(transform.rotation, 0)
            if not hasattr(transform, '_is_shape_transform'):
                json_data["r"]["ix"] = 6
    
    # Process opacity
    if hasattr(transform, 'opacity') and transform.opacity is not None:
        json_data["o"] = property_to_json(transform.opacity, 100)
        if not hasattr(transform, '_is_shape_transform'):
            json_data["o"]["ix"] = 7
    
    # Process skew
    if hasattr(transform, 'skew') and transform.skew is not None:
        json_data["sk"] = property_to_json(transform.skew, 0)
        if not hasattr(transform, '_is_shape_transform'):
            json_data["sk"]["ix"] = 4
    
    # Process skew axis
    if hasattr(transform, 'skew_axis') and transform.skew_axis is not None:
        json_data["sa"] = property_to_json(transform.skew_axis, 0)
        if not hasattr(transform, '_is_shape_transform'):
            json_data["sa"]["ix"] = 5
    
    return json_data

 
# To use the function:
def from_sequence(sequence_text):
    """

    Args:
        sequence_text
    Returns:
    """
    lines = sequence_text.strip().split('\n')

    idx = 0
    animation, idx = parse_animation_tag(lines, idx)
    return animation





def parse_asset_tag(lines, idx):
    """asset"""
    if not lines[idx].startswith('(asset'):
        raise ValueError(f"Expected asset tag, got: {lines[idx]}")
    
    asset_attrs = parse_tag_attrs(lines[idx])
    
    asset = {
        "id": asset_attrs.get("id", ""),
        "layers": []
    }
    
    #
    if "nm" in asset_attrs:
        asset["nm"] = asset_attrs["nm"]
    if "fr" in asset_attrs:
        asset["fr"] = float(asset_attrs["fr"])
    if "w" in asset_attrs:
        asset["w"] = float(asset_attrs["w"])
    if "h" in asset_attrs:
        asset["h"] = float(asset_attrs["h"])
    if "u" in asset_attrs:
        asset["u"] = asset_attrs["u"]
    if "p" in asset_attrs:
        asset["p"] = asset_attrs["p"]
    if "e" in asset_attrs:
        asset["e"] = int(asset_attrs["e"])
    
    idx += 1
    while idx < len(lines):
        if lines[idx].startswith('(layer') or lines[idx].startswith('(shape_layer'):
            layer, new_idx = parse_layer_tag(lines, idx)
            # assetlayer
            if hasattr(layer, '__dict__'):
                layer._is_asset_layer = True
            asset["layers"].append(layer)
            idx = new_idx
        elif lines[idx].startswith('(null_layer'):
            layer, new_idx = parse_layer_tag(lines, idx)
            if hasattr(layer, '__dict__'):
                layer._is_asset_layer = True
            asset["layers"].append(layer)
            idx = new_idx
        elif lines[idx].startswith('(precomp_layer'):
            layer, new_idx = parse_precomp_layer_tag(lines, idx)
            if hasattr(layer, '__dict__'):
                layer._is_asset_layer = True
            asset["layers"].append(layer)
            idx = new_idx
        elif lines[idx].startswith('(text_layer'):  # ADD THIS CASE FOR TEXT LAYERS
            layer, new_idx = parse_text_layer_tag(lines, idx)
            if hasattr(layer, '__dict__'):
                layer._is_asset_layer = True
            asset["layers"].append(layer)
            idx = new_idx
        elif lines[idx].startswith('(solid_layer'):
            layer, new_idx = parse_solid_layer_tag(lines, idx)
            if hasattr(layer, '__dict__'):
                layer._is_asset_layer = True
            asset["layers"].append(layer)
            idx = new_idx
        elif lines[idx].strip() == '(/asset)':
            idx += 1
            break
        else:
            idx += 1
    
    return asset, idx
   

def parse_animation_tag(lines, idx):
    """Parse animation tag and its contents"""
    if not lines[idx].startswith('(animation'):
        raise ValueError(f"Expected animation tag, got: {lines[idx]}")
    
    attrs = parse_tag_attrs(lines[idx])
    
    animation = {
        "v": attrs.get("v", "5.0.0"),
        "fr": float(attrs.get("fr", 30)),
        "ip": float(attrs.get("ip", 0)),
        "op": float(attrs.get("op", 30)),
        "w": float(attrs.get("w", 360)),
        "h": float(attrs.get("h", 360)),
        "nm": attrs.get("nm", "Animation"),
        "ddd": int(attrs.get("ddd", 0)),
        "assets": [],
        "layers": [],
        "markers": [],  # Initialize as empty list
        "props": {},     # Initialize as empty dict
        "fonts": None,  # fonts
        "chars": []     # chars
    }
    
    idx += 1
    while idx < len(lines):
        if lines[idx].startswith('(markers'):
            # Parse markers properly
            markers_line = lines[idx]
            start = markers_line.find(' ') + 1
            end = markers_line.rfind(')')
            if start > 0 and end > start:
                markers_content = markers_line[start:end].strip()
                if markers_content and markers_content != "[]":
                    try:
                        animation["markers"] = json.loads(markers_content)
                    except:
                        animation["markers"] = []
                else:
                    animation["markers"] = []
            idx += 1
        elif lines[idx].startswith('(props'):
            # Parse props properly
            props_line = lines[idx]
            start = props_line.find(' ') + 1
            end = props_line.rfind(')')
            if start > 0 and end > start:
                props_content = props_line[start:end].strip()
                if props_content and props_content != "{}":
                    try:
                        animation["props"] = json.loads(props_content)
                    except:
                        animation["props"] = {}
            idx += 1
        elif lines[idx].startswith('(fonts'):
            # fonts
            fonts_list = []
            idx += 1
            while idx < len(lines) and not lines[idx].startswith('(/fonts'):
                if lines[idx].startswith('(font'):
                    font_attrs = parse_tag_attrs(lines[idx])
                    font = Font(
                        font_family=font_attrs.get("family", ""),
                        font_style=font_attrs.get("style", "Regular"),
                        name=font_attrs.get("name", "")
                    )
                    if "ascent" in font_attrs:
                        font.ascent = float(font_attrs["ascent"])
                    if "path" in font_attrs:
                        font.path = font_attrs["path"]
                    if "weight" in font_attrs:
                        font.weight = font_attrs["weight"]
                    if "origin" in font_attrs:
                        font.origin = int(font_attrs["origin"])
                    fonts_list.append(font)
                idx += 1
            animation["fonts"] = {"list": fonts_list}
            if lines[idx].startswith('(/fonts'):
                idx += 1
        
        elif lines[idx].startswith('(chars'):
            # chars
            idx += 1
            while idx < len(lines) and not lines[idx].startswith('(/chars'):
                if lines[idx].startswith('(char '):
                    char_attrs = parse_tag_attrs(lines[idx])
                    char = Chars()
                    char.character = char_attrs.get("ch", "")
                    char.font_family = char_attrs.get("family", "")
                    char.font_size = float(char_attrs.get("size", 0))
                    char.font_style = char_attrs.get("style", "")
                    char.width = float(char_attrs.get("w", 0))
                    
                    idx += 1
                    # character shapes
                    if idx < len(lines) and lines[idx].startswith('(char_shapes'):
                        idx += 1
                        while idx < len(lines) and not lines[idx].startswith('(/char_shapes'):
                            # Parse shape elements for chars
                            if lines[idx].startswith('(group'):
                                shape, new_idx = parse_group_tag(lines, idx)
                                char.data.shapes.append(shape)
                                idx = new_idx
                            elif lines[idx].startswith('(path'):
                                shape, new_idx = parse_path_tag(lines, idx)
                                char.data.shapes.append(shape)
                                idx = new_idx
                            elif lines[idx].startswith('(fill'):
                                shape, new_idx = parse_fill_tag(lines, idx)
                                char.data.shapes.append(shape)
                                idx = new_idx
                            elif lines[idx].startswith('(stroke'):
                                shape, new_idx = parse_stroke_tag(lines, idx)
                                char.data.shapes.append(shape)
                                idx = new_idx
                            elif lines[idx].startswith('(rect'):
                                shape, new_idx = parse_rect_tag(lines, idx)
                                char.data.shapes.append(shape)
                                idx = new_idx
                            elif lines[idx].startswith('(ellipse'):
                                shape, new_idx = parse_ellipse_tag(lines, idx)
                                char.data.shapes.append(shape)
                                idx = new_idx
                            else:
                                idx += 1
                        if lines[idx].startswith('(/char_shapes'):
                            idx += 1
                    
                    animation["chars"].append(char)
                    
                    if idx < len(lines) and lines[idx].startswith('(/char'):
                        idx += 1
                else:
                    idx += 1
        
        elif lines[idx].startswith('(/chars'):
                idx += 1
       
        elif lines[idx].startswith('(asset'):
            asset, new_idx = parse_asset_tag(lines, idx)
            animation["assets"].append(asset)
            idx = new_idx
        elif lines[idx].startswith('(layer') or lines[idx].startswith('(shape_layer'):
            layer, new_idx = parse_layer_tag(lines, idx)
            animation["layers"].append(layer)
            idx = new_idx
        elif lines[idx].startswith('(null_layer'):
            layer, new_idx = parse_layer_tag(lines, idx)
            animation["layers"].append(layer)
            idx = new_idx
        elif lines[idx].startswith('(precomp_layer'):
            layer, new_idx = parse_precomp_layer_tag(lines, idx)
            animation["layers"].append(layer)
            idx = new_idx
        elif lines[idx].startswith('(text_layer'):
            layer, new_idx = parse_text_layer_tag(lines, idx)
            animation["layers"].append(layer)
            idx = new_idx
        elif lines[idx].startswith('(solid_layer'):  # Add this
            layer, new_idx = parse_solid_layer_tag(lines, idx)
            animation["layers"].append(layer)
            idx = new_idx
        else:
            idx += 1
    
    asset_map = {asset.get('id'): asset for asset in animation["assets"] if 'id' in asset}
    for layer in animation["layers"]:
        if isinstance(layer, PreCompLayer) and hasattr(layer, 'reference_id'):
            ref_id = layer.reference_id
            if ref_id in asset_map:
                layer.referenced_asset = asset_map[ref_id]
    
    # Build parent-child relationships
    layer_map = {layer.index: layer for layer in animation["layers"] if hasattr(layer, 'index')}
    for layer in animation["layers"]:
        if hasattr(layer, 'parent_index') and layer.parent_index is not None:
            parent_index = layer.parent_index
            if parent_index in layer_map:
                layer.parent = layer_map[parent_index]
    
    for asset in animation["assets"]:
        if "layers" in asset:
            layer_map = {layer.index: layer for layer in asset["layers"] if hasattr(layer, 'index')}
            for layer in asset["layers"]:
                if hasattr(layer, 'parent_index') and layer.parent_index is not None:
                    parent_index = layer.parent_index
                    if parent_index in layer_map:
                        layer.parent = layer_map[parent_index]

    return animation, idx


def parse_layer_tag(lines, idx):
    """"""
    if not (lines[idx].startswith('(layer') or lines[idx].startswith('(null_layer')):
        raise ValueError(f"Expected layer tag, got: {lines[idx]}")
    
    layer_attrs = parse_tag_attrs(lines[idx])
    
    #
    if 'null_layer' in lines[idx]:
        layer = NullLayer()
        layer.type = ElementType.NULL_LAYER
    else:
        layer = ShapeLayer()
    
    #
    layer.index = int(float(layer_attrs.get("index", 0)))
    layer.name = layer_attrs.get("name", "Layer")
    layer.in_point = float(layer_attrs.get("in_point", 0))
    layer.out_point = float(layer_attrs.get("out_point", 60))
    layer.start_time = float(layer_attrs.get("start_time", 0))

    # Parse optional ShapeLayer attributes - only set if present
    if "ddd" in layer_attrs:
        layer.ddd = int(layer_attrs["ddd"])

    if "hd" in layer_attrs:
        layer.hd = layer_attrs["hd"].lower() == 'true'

    if "cp" in layer_attrs:
        layer.cp = layer_attrs["cp"].lower() == 'true'

    if "cl" in layer_attrs:
        cl_value = layer_attrs["cl"]
        if cl_value and cl_value != '""':
            layer.cl = cl_value.strip('"')

    if "ao" in layer_attrs:
        layer.ao = int(layer_attrs["ao"])

    # Parse track matte attributes - only set if present
    if "tt" in layer_attrs:
        layer.tt = int(layer_attrs["tt"])

    if "tp" in layer_attrs:
        tp_value = layer_attrs["tp"]
        if tp_value and tp_value.isdigit():
            layer.tp = int(tp_value)
        else:
            layer.tp = tp_value

    if "td" in layer_attrs:
        layer.td = int(layer_attrs["td"])

    if "ct" in layer_attrs:
        layer.ct = int(layer_attrs["ct"])

    if "hasMask" in layer_attrs:
        layer.hasMask = layer_attrs["hasMask"].lower() == 'true'
        


    # is_asset
    if layer_attrs.get("is_asset", "").lower() == "true":
        layer._is_asset_layer = True
    
    idx += 1
    while idx < len(lines):
        line = lines[idx]
        if line.startswith('(parent'):
            # parent
            parent_index = extract_number(line)
            layer.parent_index = int(parent_index)  
            idx += 1
        elif line.strip() == '(transform)':
            transform, new_idx = parse_transform_tag(lines, idx)
            layer.transform = transform
            idx = new_idx
        #
        elif line.startswith('(group'):
            group, new_idx = parse_group_tag(lines, idx)
            if hasattr(layer, 'add_shape'):
                layer.add_shape(group)
            elif hasattr(layer, 'shapes'):
                layer.shapes.append(group)
            idx = new_idx
        elif line.startswith('(path'):
            path, new_idx = parse_path_tag(lines, idx)
            if hasattr(layer, 'add_shape'):
                layer.add_shape(path)
            elif hasattr(layer, 'shapes'):
                layer.shapes.append(path)
            idx = new_idx
        elif line.startswith('(fill'):
            fill, new_idx = parse_fill_tag(lines, idx)
            if hasattr(layer, 'add_shape'):
                layer.add_shape(fill)
            elif hasattr(layer, 'shapes'):
                layer.shapes.append(fill)
            idx = new_idx
        elif line.startswith('(stroke'):
            stroke, new_idx = parse_stroke_tag(lines, idx)
            if hasattr(layer, 'add_shape'):
                layer.add_shape(stroke)
            elif hasattr(layer, 'shapes'):
                layer.shapes.append(stroke)
            idx = new_idx
        elif line.startswith('(rect'):
            rect, new_idx = parse_rect_tag(lines, idx)
            if hasattr(layer, 'add_shape'):
                layer.add_shape(rect)
            elif hasattr(layer, 'shapes'):
                layer.shapes.append(rect)
            idx = new_idx
        elif line.startswith('(ellipse'):
            ellipse, new_idx = parse_ellipse_tag(lines, idx)
            if hasattr(layer, 'add_shape'):
                layer.add_shape(ellipse)
            elif hasattr(layer, 'shapes'):
                layer.shapes.append(ellipse)
            idx = new_idx
        elif line.startswith('(star'):
            star, new_idx = parse_star_tag(lines, idx)
            if hasattr(layer, 'add_shape'):
                layer.add_shape(star)
            elif hasattr(layer, 'shapes'):
                layer.shapes.append(star)
            idx = new_idx
        elif line.startswith('(trim'):
            trim, new_idx = parse_trim_tag(lines, idx)
            if hasattr(layer, 'add_shape'):
                layer.add_shape(trim)
            elif hasattr(layer, 'shapes'):
                layer.shapes.append(trim)
            idx = new_idx
        elif line.startswith('(repeater'):
            repeater, new_idx = parse_repeater_tag(lines, idx)
            if hasattr(layer, 'add_shape'):
                layer.add_shape(repeater)
            elif hasattr(layer, 'shapes'):
                layer.shapes.append(repeater)
            idx = new_idx
        elif line.startswith('(gradient_fill'):
            gradient_fill, new_idx = parse_gradient_fill_tag(lines, idx)
            if hasattr(layer, 'add_shape'):
                layer.add_shape(gradient_fill)
            elif hasattr(layer, 'shapes'):
                layer.shapes.append(gradient_fill)
            idx = new_idx
        elif line.startswith('(gradient_stroke'):
            gradient_stroke, new_idx = parse_gradient_stroke_tag(lines, idx)
            if hasattr(layer, 'add_shape'):
                layer.add_shape(gradient_stroke)
            elif hasattr(layer, 'shapes'):
                layer.shapes.append(gradient_stroke)
            idx = new_idx
        elif line.startswith('(merge'):
            merge, new_idx = parse_merge_tag(lines, idx)
            if hasattr(layer, 'add_shape'):
                layer.add_shape(merge)
            elif hasattr(layer, 'shapes'):
                layer.shapes.append(merge)
            idx = new_idx
        elif line.startswith('(rounded_corners'):
            rounded_corners, new_idx = parse_rounded_corners_tag(lines, idx)
            if hasattr(layer, 'add_shape'):
                layer.add_shape(rounded_corners)
            elif hasattr(layer, 'shapes'):
                layer.shapes.append(rounded_corners)
            idx = new_idx
        elif line.startswith('(twist'):
            twist, new_idx = parse_twist_tag(lines, idx)
            if hasattr(layer, 'add_shape'):
                layer.add_shape(twist)
            elif hasattr(layer, 'shapes'):
                layer.shapes.append(twist)
            idx = new_idx
        
        elif lines[idx].startswith('(zig_zag'):
            zig_zag, new_idx = parse_zig_zag_tag(lines, idx)
            layer.shapes.append(zig_zag)
            idx = new_idx
        elif line.startswith('(tm '):
            # tm -
            tm_attrs = parse_tag_attrs(line)
            #print("tm_attrs", tm_attrs)
            tm_data = {}
            if 'a' in tm_attrs:
                tm_data['a'] = int(tm_attrs['a'])
            if 'ix' in tm_attrs:
                tm_data['ix'] = int(tm_attrs['ix'])
            
            # keyframes
            idx += 1
            keyframes = []
            while idx < len(lines):
                line = lines[idx]
                if line.startswith('(keyframe'):
                    kf_attrs = parse_tag_attrs(line)
                    kf = {}
                    if 't' in kf_attrs:
                        kf['t'] = float(kf_attrs['t'])
                    if 's' in kf_attrs:
                        kf['s'] = [float(kf_attrs['s'])]
                    if 'h' in kf_attrs:
                        kf['h'] = int(kf_attrs['h'])
                    
                    #
                    if 'i_x' in kf_attrs or 'i_y' in kf_attrs:
                        kf['i'] = {}
                        if 'i_x' in kf_attrs:
                            kf['i']['x'] = [float(kf_attrs['i_x'])]
                        if 'i_y' in kf_attrs:
                            kf['i']['y'] = [float(kf_attrs['i_y'])]
                    
                    if 'o_x' in kf_attrs or 'o_y' in kf_attrs:
                        kf['o'] = {}
                        if 'o_x' in kf_attrs:
                            kf['o']['x'] = [float(kf_attrs['o_x'])]
                        if 'o_y' in kf_attrs:
                            kf['o']['y'] = [float(kf_attrs['o_y'])]
                    
                    keyframes.append(kf)
                    idx += 1
                elif line.startswith('(value'):
                    #
                    val = extract_number(line)
                    tm_data['k'] = val
                    idx += 1
                elif line.strip() == '(/tm)':
                    if keyframes:
                        tm_data['k'] = keyframes
                    idx += 1
                    break
                else:
                    idx += 1
            
            layer.tm = tm_data
        
        elif lines[idx].startswith('(effects'):
            # effects
            effects, new_idx = parse_effects_tag(lines, idx)
            layer.ef = effects
            idx = new_idx
            
        
        elif line.startswith('(tt'):
            tt_value = extract_number(line)
            layer.tt = int(tt_value)
            idx += 1
        elif line.startswith('(tp'):
            tp_value = extract_number(line)
            layer.tp = int(tp_value)
            idx += 1
        elif line.startswith('(td'):
            td_value = extract_number(line)
            layer.td = int(td_value)
            idx += 1
        
        elif line.startswith('(masksProperties'):
            # masksProperties
            layer.masksProperties = []
            idx += 1
            
            while idx < len(lines) and not lines[idx].startswith('(/masksProperties)'):
                if lines[idx].startswith('(mask '):
                    # mask
                    mask_attrs = parse_tag_attrs(lines[idx])
                    mask = {}
                    
                    #
                    if "inv" in mask_attrs:
                        mask["inv"] = mask_attrs["inv"].lower() == "true"
                    if "mode" in mask_attrs:
                        mask["mode"] = mask_attrs["mode"]
                    if "nm" in mask_attrs:
                        mask["nm"] = mask_attrs["nm"]
                    
                    idx += 1
                    
                    # mask
                    while idx < len(lines) and not lines[idx].startswith('(/mask)'):
                        if lines[idx].startswith('(mask_pt '):
                            # pt ()
                            pt_attrs = parse_tag_attrs(lines[idx])
                            mask["pt"] = {}
                            if "a" in pt_attrs:
                                mask["pt"]["a"] = int(pt_attrs["a"])
                            if "ix" in pt_attrs:
                                mask["pt"]["ix"] = int(pt_attrs["ix"])
                            
                            idx += 1
                            
                            # pt.k ()
                            if idx < len(lines) and lines[idx].startswith('(mask_pt_k'):
                                if lines[idx].startswith('(mask_pt_k_array'):
                                    # k
                                    mask["pt"]["k"] = []
                                    idx += 1
                                    
                                    #
                                    while idx < len(lines) and not lines[idx].startswith('(/mask_pt_k_array)'):
                                        if lines[idx].startswith('(mask_pt_keyframe'):
                                            kf_attrs = parse_tag_attrs(lines[idx])
                                            keyframe = {}
                                            
                                            if "t" in kf_attrs:
                                                keyframe["t"] = float(kf_attrs["t"])
                                            
                                            idx += 1
                                            
                                            #
                                            while idx < len(lines) and not lines[idx].startswith('(/mask_pt_keyframe)'):
                                                if lines[idx].startswith('(mask_pt_kf_i'):
                                                    i_attrs = parse_tag_attrs(lines[idx])
                                                    keyframe["i"] = {
                                                        "x": float(i_attrs.get("x", 0)),
                                                        "y": float(i_attrs.get("y", 0))
                                                    }
                                                    idx += 1
                                                elif lines[idx].startswith('(mask_pt_kf_o'):
                                                    o_attrs = parse_tag_attrs(lines[idx])
                                                    keyframe["o"] = {
                                                        "x": float(o_attrs.get("x", 0)),
                                                        "y": float(o_attrs.get("y", 0))
                                                    }
                                                    idx += 1
                                                elif lines[idx].startswith('(mask_pt_kf_s'):
                                                    keyframe["s"] = []
                                                    idx += 1
                                                    while idx < len(lines) and not lines[idx].startswith('(/mask_pt_kf_s)'):
                                                        if lines[idx].startswith('(mask_pt_kf_shape'):
                                                            shape_attrs = parse_tag_attrs(lines[idx])
                                                            shape = {}
                                                            if "c" in shape_attrs:
                                                                shape["c"] = shape_attrs["c"].lower() == "true"
                                                            idx += 1
                                                            while idx < len(lines) and not lines[idx].startswith('(/mask_pt_kf_shape)'):
                                                                if lines[idx].startswith('(mask_pt_kf_shape_i'):
                                                                    values = extract_numbers(lines[idx])
                                                                    shape["i"] = []
                                                                    for i in range(0, len(values), 2):
                                                                        if i + 1 < len(values):
                                                                            shape["i"].append([values[i], values[i+1]])
                                                                    idx += 1
                                                                elif lines[idx].startswith('(mask_pt_kf_shape_o'):
                                                                    values = extract_numbers(lines[idx])
                                                                    shape["o"] = []
                                                                    for i in range(0, len(values), 2):
                                                                        if i + 1 < len(values):
                                                                            shape["o"].append([values[i], values[i+1]])
                                                                    idx += 1
                                                                elif lines[idx].startswith('(mask_pt_kf_shape_v'):
                                                                    values = extract_numbers(lines[idx])
                                                                    shape["v"] = []
                                                                    for i in range(0, len(values), 2):
                                                                        if i + 1 < len(values):
                                                                            shape["v"].append([values[i], values[i+1]])
                                                                    idx += 1
                                                                else:
                                                                    idx += 1
                                                            if lines[idx].startswith('(/mask_pt_kf_shape)'):
                                                                idx += 1
                                                            keyframe["s"].append(shape)
                                                        else:
                                                            idx += 1
                                                    if lines[idx].startswith('(/mask_pt_kf_s)'):
                                                        idx += 1
                                                else:
                                                    idx += 1
                                            
                                            if lines[idx].startswith('(/mask_pt_keyframe)'):
                                                idx += 1
                                            
                                            mask["pt"]["k"].append(keyframe)
                                        else:
                                            idx += 1
                                    
                                    if lines[idx].startswith('(/mask_pt_k_array)'):
                                        idx += 1
                                
                                else:
                                    # kshape
                                    mask["pt"]["k"] = {}
                                    idx += 1
                                    
                                    # shape
                                    while idx < len(lines) and not lines[idx].startswith('(/mask_pt_k)'):
                                        if lines[idx].startswith('(mask_pt_k_c'):
                                            # closed
                                            parts = lines[idx].split()
                                            if len(parts) > 1:
                                                mask["pt"]["k"]["c"] = parts[1].rstrip(')').lower() == "true"
                                            idx += 1
                                        
                                        elif lines[idx].startswith('(mask_pt_k_i'):
                                            # i
                                            values = extract_numbers(lines[idx])
                                            mask["pt"]["k"]["i"] = []
                                            for i in range(0, len(values), 2):
                                                if i + 1 < len(values):
                                                    mask["pt"]["k"]["i"].append([values[i], values[i+1]])
                                            idx += 1
                                        
                                        elif lines[idx].startswith('(mask_pt_k_o'):
                                            # o
                                            values = extract_numbers(lines[idx])
                                            mask["pt"]["k"]["o"] = []
                                            for i in range(0, len(values), 2):
                                                if i + 1 < len(values):
                                                    mask["pt"]["k"]["o"].append([values[i], values[i+1]])
                                            idx += 1
                                        
                                        elif lines[idx].startswith('(mask_pt_k_v'):
                                            # v
                                            values = extract_numbers(lines[idx])
                                            mask["pt"]["k"]["v"] = []
                                            for i in range(0, len(values), 2):
                                                if i + 1 < len(values):
                                                    mask["pt"]["k"]["v"].append([values[i], values[i+1]])
                                            idx += 1
                                        else:
                                            idx += 1
                                    
                                    if lines[idx].startswith('(/mask_pt_k)'):
                                        idx += 1
                            
                            if idx < len(lines) and lines[idx].startswith('(/mask_pt)'):
                                idx += 1
                        
                        elif lines[idx].startswith('(mask_o '):
                            # opacity
                            o_attrs = parse_tag_attrs(lines[idx])
                            mask["o"] = {}
                            if "a" in o_attrs:
                                mask["o"]["a"] = int(o_attrs["a"])
                            if "ix" in o_attrs:
                                mask["o"]["ix"] = int(o_attrs["ix"])
                            
                            #
                            if "a" in o_attrs and int(o_attrs["a"]) == 1:
                                #
                                mask["o"]["k"] = []
                                idx += 1
                                while idx < len(lines) and lines[idx].startswith('(keyframe'):
                                    kf_attrs = parse_tag_attrs(lines[idx])
                                    keyframe = {}
                                    if "t" in kf_attrs:
                                        keyframe["t"] = float(kf_attrs["t"])
                                    if "s" in kf_attrs:
                                        keyframe["s"] = [float(kf_attrs["s"])]
                                    if "i_x" in kf_attrs and "i_y" in kf_attrs:
                                        keyframe["i"] = {
                                            "x": [float(kf_attrs["i_x"])],
                                            "y": [float(kf_attrs["i_y"])]
                                        }
                                    if "o_x" in kf_attrs and "o_y" in kf_attrs:
                                        keyframe["o"] = {
                                            "x": [float(kf_attrs["o_x"])],
                                            "y": [float(kf_attrs["o_y"])]
                                        }
                                    mask["o"]["k"].append(keyframe)
                                    idx += 1
                            else:
                                #
                                if "k" in o_attrs:
                                    mask["o"]["k"] = float(o_attrs["k"])
                                idx += 1
                        
                        elif lines[idx].startswith('(mask_x '):
                            # dilate
                            x_attrs = parse_tag_attrs(lines[idx])
                            mask["x"] = {}
                            if "a" in x_attrs:
                                mask["x"]["a"] = int(x_attrs["a"])
                            if "ix" in x_attrs:
                                mask["x"]["ix"] = int(x_attrs["ix"])
                            
                            #
                            if "a" in x_attrs and int(x_attrs["a"]) == 1:
                                #
                                mask["x"]["k"] = []
                                idx += 1
                                while idx < len(lines) and lines[idx].startswith('(keyframe'):
                                    kf_attrs = parse_tag_attrs(lines[idx])
                                    keyframe = {}
                                    if "t" in kf_attrs:
                                        keyframe["t"] = float(kf_attrs["t"])
                                    if "s" in kf_attrs:
                                        keyframe["s"] = [float(kf_attrs["s"])]
                                    if "i_x" in kf_attrs and "i_y" in kf_attrs:
                                        keyframe["i"] = {
                                            "x": [float(kf_attrs["i_x"])],
                                            "y": [float(kf_attrs["i_y"])]
                                        }
                                    if "o_x" in kf_attrs and "o_y" in kf_attrs:
                                        keyframe["o"] = {
                                            "x": [float(kf_attrs["o_x"])],
                                            "y": [float(kf_attrs["o_y"])]
                                        }
                                    mask["x"]["k"].append(keyframe)
                                    idx += 1
                            else:
                                #
                                if "k" in x_attrs:
                                    mask["x"]["k"] = float(x_attrs["k"])
                                idx += 1
                        else:
                            idx += 1
                    
                    if lines[idx].startswith('(/mask)'):
                        idx += 1
                    
                    layer.masksProperties.append(mask)
                else:
                    idx += 1
            
            if lines[idx].startswith('(/masksProperties)'):
                idx += 1
            


        elif lines[idx].strip() == '(/layer)' or lines[idx].strip() == '(/null_layer)':
            idx += 1
            break
        else:
            idx += 1
    
    return layer, idx

def parse_transform_tag(lines, idx):
    """Parse transform tag with support for single-line static properties"""
    transform = Transform()
    
    # Initialize default values
    transform.position = MultiDimensional(NVector(0, 0, 0))
    transform.scale = MultiDimensional(NVector(100, 100, 100))
    transform.rotation = Value(0)
    transform.opacity = Value(100)
    transform.anchor = MultiDimensional(NVector(0, 0, 0))
    
    idx += 1
    while idx < len(lines):
        line = lines[idx].strip()
        
        # Check if this line contains multiple static properties
        if '(' in line and ')' in line and line.count('(') > 1:
            # Parse multiple properties on the same line
            import re
            props = re.findall(r'\([^)]+\)', line)
            for prop in props:
                prop = prop.strip()
                if prop.startswith('(position'):
                    components = extract_numbers(prop)
                    if components:
                        if len(components) == 1:
                            transform.position = MultiDimensional(NVector(components[0], 0, 0))
                        elif len(components) == 2:
                            transform.position = MultiDimensional(NVector(components[0], components[1], 0))
                        else:
                            transform.position = MultiDimensional(NVector(*components))
                elif prop.startswith('(scale'):
                    components = extract_numbers(prop)
                    if len(components) >= 3:
                        transform.scale = MultiDimensional(NVector(*components))
                    elif len(components) == 2:
                        transform.scale = MultiDimensional(NVector(components[0], components[1], 100))
                    elif len(components) == 1:
                        transform.scale = MultiDimensional(NVector(components[0], components[0], 100))
                elif prop.startswith('(rotation'):
                    value = extract_number(prop)
                    transform.rotation = Value(value)
                elif prop.startswith('(opacity'):
                    value = extract_number(prop)
                    transform.opacity = Value(value)
                elif prop.startswith('(anchor'):
                    components = extract_numbers(prop)
                    if components:
                        if len(components) == 1:
                            transform.anchor = MultiDimensional(NVector(components[0], 0, 0))
                        else:
                            transform.anchor = MultiDimensional(NVector(*components))
            idx += 1
            continue
        
        # Add expression parsing

        if line.startswith('(position'):
            if 'separated=true' in line:
                # Handle separated position with animated components
                transform.position = Value(NVector(0, 0, 0))
                transform.position.separated = True
                idx += 1
                while idx < len(lines) and not lines[idx].startswith('(/position)'):
                    if lines[idx].startswith('(position_x'):
                        if 'animated=true' in lines[idx]:
                            # Parse animated x component
                            idx += 1
                            keyframes = []
                            while idx < len(lines) and not lines[idx].startswith('(/position_x)'):
                                if lines[idx].startswith('(keyframe'):
                                    attrs = parse_tag_attrs(lines[idx])
                                    time = float(attrs.get('t', 0))
                                    value = float(attrs.get('s', 0))
                                    kf = Keyframe(time, value)
                                    
                                    if 'i_x' in attrs and 'i_y' in attrs:
                                        # Handle bracketed format for easing parameters
                                        i_x_str = attrs['i_x']
                                        i_y_str = attrs['i_y']
                                        
                                        if i_x_str.startswith('[') and i_x_str.endswith(']'):
                                            i_x = float(i_x_str[1:-1])
                                        else:
                                            i_x = float(i_x_str)
                                        
                                        if i_y_str.startswith('[') and i_y_str.endswith(']'):
                                            i_y = float(i_y_str[1:-1])
                                        else:
                                            i_y = float(i_y_str)
                                        
                                        kf.in_tan = {'x': i_x, 'y': i_y}
                                    
                                    if 'o_x' in attrs and 'o_y' in attrs:
                                        # Handle bracketed format for easing parameters
                                        o_x_str = attrs['o_x']
                                        o_y_str = attrs['o_y']
                                        
                                        if o_x_str.startswith('[') and o_x_str.endswith(']'):
                                            o_x = float(o_x_str[1:-1])
                                        else:
                                            o_x = float(o_x_str)
                                        
                                        if o_y_str.startswith('[') and o_y_str.endswith(']'):
                                            o_y = float(o_y_str[1:-1])
                                        else:
                                            o_y = float(o_y_str)
                                        
                                        kf.out_tan = {'x': o_x, 'y': o_y}
                                    if 'h' in attrs:
                                        kf.h = int(attrs['h'])
                                    # Handle n and e attributes
                                    if 'n' in attrs:
                                        kf.n = attrs['n']
                                    if 'e' in attrs:
                                        try:
                                            kf.e = json.loads(attrs['e']) if attrs['e'].startswith('[') else float(attrs['e'])
                                        except:
                                            kf.e = attrs['e']
                                    
                                    keyframes.append(kf)
                                idx += 1
                            
                            if keyframes:
                                x_value = Value(keyframes[0].value if keyframes else 0)
                                x_value.keyframes = keyframes
                                transform.position.x = x_value
                            
                            if idx < len(lines) and lines[idx].startswith('(/position_x)'):
                                idx += 1
                        else:
                            value = extract_number(lines[idx])
                            transform.position.x = Value(value)
                            idx += 1
                    elif lines[idx].startswith('(position_y'):
                        if 'animated=true' in lines[idx]:
                            # Parse animated y component
                            idx += 1
                            keyframes = []
                            while idx < len(lines) and not lines[idx].startswith('(/position_y)'):
                                if lines[idx].startswith('(keyframe'):
                                    attrs = parse_tag_attrs(lines[idx])
                                    time = float(attrs.get('t', 0))
                                    value = float(attrs.get('s', 0))
                                    kf = Keyframe(time, value)
                                    
                                    if 'i_x' in attrs and 'i_y' in attrs:
                                        # Handle bracketed format for easing parameters
                                        i_x_str = attrs['i_x']
                                        i_y_str = attrs['i_y']
                                        
                                        if i_x_str.startswith('[') and i_x_str.endswith(']'):
                                            i_x = float(i_x_str[1:-1])
                                        else:
                                            i_x = float(i_x_str)
                                        
                                        if i_y_str.startswith('[') and i_y_str.endswith(']'):
                                            i_y = float(i_y_str[1:-1])
                                        else:
                                            i_y = float(i_y_str)
                                        
                                        kf.in_tan = {'x': i_x, 'y': i_y}
                                    
                                    if 'o_x' in attrs and 'o_y' in attrs:
                                        # Handle bracketed format for easing parameters
                                        o_x_str = attrs['o_x']
                                        o_y_str = attrs['o_y']
                                        
                                        if o_x_str.startswith('[') and o_x_str.endswith(']'):
                                            o_x = float(o_x_str[1:-1])
                                        else:
                                            o_x = float(o_x_str)
                                        
                                        if o_y_str.startswith('[') and o_y_str.endswith(']'):
                                            o_y = float(o_y_str[1:-1])
                                        else:
                                            o_y = float(o_y_str)
                                        
                                        kf.out_tan = {'x': o_x, 'y': o_y}
                                    if 'h' in attrs:
                                        kf.h = int(attrs['h'])
                                    # Handle n and e attributes
                                    if 'n' in attrs:
                                        kf.n = attrs['n']
                                    if 'e' in attrs:
                                        try:
                                            kf.e = json.loads(attrs['e']) if attrs['e'].startswith('[') else float(attrs['e'])
                                        except:
                                            kf.e = attrs['e']
                                    
                                    keyframes.append(kf)
                                idx += 1
                            
                            if keyframes:
                                y_value = Value(keyframes[0].value if keyframes else 0)
                                y_value.keyframes = keyframes
                                transform.position.y = y_value
                            
                            if idx < len(lines) and lines[idx].startswith('(/position_y)'):
                                idx += 1
                        else:
                            value = extract_number(lines[idx])
                            transform.position.y = Value(value)
                            idx += 1
                    elif lines[idx].startswith('(position_z'):
                        if 'animated=true' in lines[idx]:
                            # Parse animated z component
                            idx += 1
                            keyframes = []
                            while idx < len(lines) and not lines[idx].startswith('(/position_z)'):
                                if lines[idx].startswith('(keyframe'):
                                    attrs = parse_tag_attrs(lines[idx])
                                    time = float(attrs.get('t', 0))
                                    value = float(attrs.get('s', 0))
                                    kf = Keyframe(time, value)
                                    
                                    if 'i_x' in attrs and 'i_y' in attrs:
                                        # Handle bracketed format for easing parameters
                                        i_x_str = attrs['i_x']
                                        i_y_str = attrs['i_y']
                                        
                                        if i_x_str.startswith('[') and i_x_str.endswith(']'):
                                            i_x = float(i_x_str[1:-1])
                                        else:
                                            i_x = float(i_x_str)
                                        
                                        if i_y_str.startswith('[') and i_y_str.endswith(']'):
                                            i_y = float(i_y_str[1:-1])
                                        else:
                                            i_y = float(i_y_str)
                                        
                                        kf.in_tan = {'x': i_x, 'y': i_y}
                                    
                                    if 'o_x' in attrs and 'o_y' in attrs:
                                        # Handle bracketed format for easing parameters
                                        o_x_str = attrs['o_x']
                                        o_y_str = attrs['o_y']
                                        
                                        if o_x_str.startswith('[') and o_x_str.endswith(']'):
                                            o_x = float(o_x_str[1:-1])
                                        else:
                                            o_x = float(o_x_str)
                                        
                                        if o_y_str.startswith('[') and o_y_str.endswith(']'):
                                            o_y = float(o_y_str[1:-1])
                                        else:
                                            o_y = float(o_y_str)
                                        
                                        kf.out_tan = {'x': o_x, 'y': o_y}
                                    
                                    if 'h' in attrs:
                                        kf.h = int(attrs['h'])
                                    # Handle n and e attributes
                                    if 'n' in attrs:
                                        kf.n = attrs['n']
                                    if 'e' in attrs:
                                        try:
                                            kf.e = json.loads(attrs['e']) if attrs['e'].startswith('[') else float(attrs['e'])
                                        except:
                                            kf.e = attrs['e']
                                    
                                    keyframes.append(kf)
                                idx += 1
                            
                            if keyframes:
                                z_value = Value(keyframes[0].value if keyframes else 0)
                                z_value.keyframes = keyframes
                                transform.position.z = z_value
                            
                            if idx < len(lines) and lines[idx].startswith('(/position_z)'):
                                idx += 1
                        else:
                            value = extract_number(lines[idx])
                            transform.position.z = Value(value)
                            idx += 1
                    else:
                        idx += 1
                if lines[idx].startswith('(/position)'):
                    idx += 1
            elif 'animated=true' in line:
                # Regular animated position
                idx += 1
                keyframes = []
                
                while idx < len(lines) and not lines[idx].startswith('(/position)'):
                    if lines[idx].startswith('(keyframe'):
                        attrs = parse_tag_attrs(lines[idx])
                        
                        time = float(attrs.get('t', 0))
                        
                        s_str = attrs.get('s', '')
                        if s_str:
                            values = [float(x) for x in s_str.split()]
                            if len(values) >= 3:
                                value = NVector(values[0], values[1], values[2])
                            elif len(values) == 2:
                                value = NVector(values[0], values[1], 0)
                            else:
                                value = NVector(0, 0, 0)
                        else:
                            value = NVector(0, 0, 0)
                        
                        kf = Keyframe(time, value)
                        
                        if 'i_x' in attrs and 'i_y' in attrs:
                            i_x_str = attrs['i_x']
                            i_y_str = attrs['i_y']
                            
                            # Handle space-separated list format
                            if ' ' in i_x_str:
                                i_x = [float(v) for v in i_x_str.split()]
                                i_y = [float(v) for v in i_y_str.split()]
                            # Handle bracketed format
                            elif i_x_str.startswith('[') and i_x_str.endswith(']'):
                                # Extract value from bracketed format [0.833] -> 0.833
                                i_x = float(i_x_str[1:-1])
                                i_y = float(i_y_str[1:-1])
                            else:
                                i_x = float(i_x_str)
                                i_y = float(i_y_str)
                            
                            kf.in_tan = {'x': i_x, 'y': i_y}
                        
                        if 'o_x' in attrs and 'o_y' in attrs:
                            o_x_str = attrs['o_x']
                            o_y_str = attrs['o_y']
                            
                            # Handle space-separated list format
                            if ' ' in o_x_str:
                                o_x = [float(v) for v in o_x_str.split()]
                                o_y = [float(v) for v in o_y_str.split()]
                            # Handle bracketed format
                            elif o_x_str.startswith('[') and o_x_str.endswith(']'):
                                # Extract value from bracketed format [0.833] -> 0.833
                                o_x = float(o_x_str[1:-1])
                                o_y = float(o_y_str[1:-1])
                            else:
                                o_x = float(o_x_str)
                                o_y = float(o_y_str)
                            
                            kf.out_tan = {'x': o_x, 'y': o_y}
                        
                        if 'to' in attrs:
                            try:
                                kf.to = json.loads(attrs['to'])
                            except:
                                pass
                        
                        if 'ti' in attrs:
                            try:
                                kf.ti = json.loads(attrs['ti'])
                            except:
                                pass
                        
                        if 'h' in attrs:
                            kf.h = int(attrs['h'])
                        # Handle n and e attributes
                        if 'n' in attrs:
                            kf.n = attrs['n']
                        if 'e' in attrs:
                            try:
                                kf.e = json.loads(attrs['e']) if attrs['e'].startswith('[') else [float(x) for x in attrs['e'].split()]
                            except:
                                try:
                                    kf.e = float(attrs['e'])
                                except:
                                    kf.e = attrs['e']
                        
                        keyframes.append(kf)
                    idx += 1
                
                if idx < len(lines) and lines[idx].startswith('(/position)'):
                    idx += 1
                
                if keyframes:
                    pos_value = MultiDimensional(keyframes[0].value)
                    pos_value.keyframes = keyframes
                    transform.position = pos_value
            else:
                components = extract_numbers(line)
                if components:
                    if len(components) == 1:
                        transform.position = MultiDimensional(NVector(components[0], 0, 0))
                    elif len(components) == 2:
                        transform.position = MultiDimensional(NVector(components[0], components[1], 0))
                    else:
                        transform.position = MultiDimensional(NVector(*components))
                else:
                    transform.position = MultiDimensional(NVector(250, 250, 0))
                idx += 1
          
        elif line.startswith('(scale'):
            # Scale parsing code with bracketed format handling
            if 'separated=true' in line:
                # Handle separated scale
                transform.scale = Value(NVector(100, 100, 100))
                transform.scale.separated = True
                idx += 1
                while idx < len(lines) and not lines[idx].startswith('(/scale)'):
                    if lines[idx].startswith('(scale_x'):
                        if 'animated=true' in lines[idx]:
                            # Parse animated x component
                            idx += 1
                            keyframes = []
                            while idx < len(lines) and not lines[idx].startswith('(/scale_x)'):
                                if lines[idx].startswith('(keyframe'):
                                    attrs = parse_tag_attrs(lines[idx])
                                    time = float(attrs.get('t', 0))
                                    value = float(attrs.get('s', 100))
                                    kf = Keyframe(time, value)
                                    
                                    if 'i_x' in attrs and 'i_y' in attrs:
                                        i_x_str = attrs['i_x']
                                        i_y_str = attrs['i_y']
                                        
                                        if i_x_str.startswith('[') and i_x_str.endswith(']'):
                                            i_x = float(i_x_str[1:-1])
                                        else:
                                            i_x = float(i_x_str)
                                        
                                        if i_y_str.startswith('[') and i_y_str.endswith(']'):
                                            i_y = float(i_y_str[1:-1])
                                        else:
                                            i_y = float(i_y_str)
                                        
                                        kf.in_tan = {'x': i_x, 'y': i_y}
                                    
                                    if 'o_x' in attrs and 'o_y' in attrs:
                                        o_x_str = attrs['o_x']
                                        o_y_str = attrs['o_y']
                                        
                                        if o_x_str.startswith('[') and o_x_str.endswith(']'):
                                            o_x = float(o_x_str[1:-1])
                                        else:
                                            o_x = float(o_x_str)
                                        
                                        if o_y_str.startswith('[') and o_y_str.endswith(']'):
                                            o_y = float(o_y_str[1:-1])
                                        else:
                                            o_y = float(o_y_str)
                                        
                                        kf.out_tan = {'x': o_x, 'y': o_y}
                                    
                                    keyframes.append(kf)
                                idx += 1
                            
                            if keyframes:
                                x_value = Value(keyframes[0].value if keyframes else 100)
                                x_value.keyframes = keyframes
                                transform.scale.x = x_value
                            
                            if idx < len(lines) and lines[idx].startswith('(/scale_x)'):
                                idx += 1
                        else:
                            value = extract_number(lines[idx])
                            transform.scale.x = Value(value)
                            idx += 1
                    elif lines[idx].startswith('(scale_y'):
                        if 'animated=true' in lines[idx]:
                            # Parse animated y component
                            idx += 1
                            keyframes = []
                            while idx < len(lines) and not lines[idx].startswith('(/scale_y)'):
                                if lines[idx].startswith('(keyframe'):
                                    attrs = parse_tag_attrs(lines[idx])
                                    time = float(attrs.get('t', 0))
                                    value = float(attrs.get('s', 100))
                                    kf = Keyframe(time, value)
                                    
                                    if 'i_x' in attrs and 'i_y' in attrs:
                                        i_x_str = attrs['i_x']
                                        i_y_str = attrs['i_y']
                                        
                                        if i_x_str.startswith('[') and i_x_str.endswith(']'):
                                            i_x = float(i_x_str[1:-1])
                                        else:
                                            i_x = float(i_x_str)
                                        
                                        if i_y_str.startswith('[') and i_y_str.endswith(']'):
                                            i_y = float(i_y_str[1:-1])
                                        else:
                                            i_y = float(i_y_str)
                                        
                                        kf.in_tan = {'x': i_x, 'y': i_y}
                                    
                                    if 'o_x' in attrs and 'o_y' in attrs:
                                        o_x_str = attrs['o_x']
                                        o_y_str = attrs['o_y']
                                        
                                        if o_x_str.startswith('[') and o_x_str.endswith(']'):
                                            o_x = float(o_x_str[1:-1])
                                        else:
                                            o_x = float(o_x_str)
                                        
                                        if o_y_str.startswith('[') and o_y_str.endswith(']'):
                                            o_y = float(o_y_str[1:-1])
                                        else:
                                            o_y = float(o_y_str)
                                        
                                        kf.out_tan = {'x': o_x, 'y': o_y}
                                    
                                    keyframes.append(kf)
                                idx += 1
                            
                            if keyframes:
                                y_value = Value(keyframes[0].value if keyframes else 100)
                                y_value.keyframes = keyframes
                                transform.scale.y = y_value
                            
                            if idx < len(lines) and lines[idx].startswith('(/scale_y)'):
                                idx += 1
                        else:
                            value = extract_number(lines[idx])
                            transform.scale.y = Value(value)
                            idx += 1
                    elif lines[idx].startswith('(scale_z'):
                        if 'animated=true' in lines[idx]:
                            # Parse animated z component
                            idx += 1
                            keyframes = []
                            while idx < len(lines) and not lines[idx].startswith('(/scale_z)'):
                                if lines[idx].startswith('(keyframe'):
                                    attrs = parse_tag_attrs(lines[idx])
                                    time = float(attrs.get('t', 0))
                                    value = float(attrs.get('s', 100))
                                    kf = Keyframe(time, value)
                                    
                                    if 'i_x' in attrs and 'i_y' in attrs:
                                        i_x_str = attrs['i_x']
                                        i_y_str = attrs['i_y']
                                        
                                        if i_x_str.startswith('[') and i_x_str.endswith(']'):
                                            i_x = float(i_x_str[1:-1])
                                        else:
                                            i_x = float(i_x_str)
                                        
                                        if i_y_str.startswith('[') and i_y_str.endswith(']'):
                                            i_y = float(i_y_str[1:-1])
                                        else:
                                            i_y = float(i_y_str)
                                        
                                        kf.in_tan = {'x': i_x, 'y': i_y}
                                    
                                    if 'o_x' in attrs and 'o_y' in attrs:
                                        o_x_str = attrs['o_x']
                                        o_y_str = attrs['o_y']
                                        
                                        if o_x_str.startswith('[') and o_x_str.endswith(']'):
                                            o_x = float(o_x_str[1:-1])
                                        else:
                                            o_x = float(o_x_str)
                                        
                                        if o_y_str.startswith('[') and o_y_str.endswith(']'):
                                            o_y = float(o_y_str[1:-1])
                                        else:
                                            o_y = float(o_y_str)
                                        
                                        kf.out_tan = {'x': o_x, 'y': o_y}
                                    
                                    keyframes.append(kf)
                                idx += 1
                            
                            if keyframes:
                                z_value = Value(keyframes[0].value if keyframes else 100)
                                z_value.keyframes = keyframes
                                transform.scale.z = z_value
                            
                            if idx < len(lines) and lines[idx].startswith('(/scale_z)'):
                                idx += 1
                        else:
                            value = extract_number(lines[idx])
                            transform.scale.z = Value(value)
                            idx += 1
                    else:
                        idx += 1
                if lines[idx].startswith('(/scale)'):
                    idx += 1
            elif 'animated=true' in line:
                # Regular animated scale
                idx += 1
                keyframes = []
                
                while idx < len(lines) and not lines[idx].startswith('(/scale)'):
                    if lines[idx].startswith('(keyframe'):
                        attrs = parse_tag_attrs(lines[idx])
                        
                        time = float(attrs.get('t', 0))
                        
                        s_str = attrs.get('s', '')
                        if s_str:
                            values = [float(x) for x in s_str.split()]
                            if len(values) >= 3:
                                value = NVector(values[0], values[1], values[2])
                            elif len(values) == 2:
                                value = NVector(values[0], values[1], 100)
                            else:
                                value = NVector(values[0] if values else 100, values[0] if values else 100, 100)
                        else:
                            value = NVector(100, 100, 100)
                        
                        kf = Keyframe(time, value)
                        
                        # Handle easing parameters
                        if 'i_x' in attrs and 'i_y' in attrs:
                            i_x_str = attrs['i_x']
                            i_y_str = attrs['i_y']
                            
                            # Handle space-separated list format
                            if ' ' in i_x_str:
                                i_x = [float(v) for v in i_x_str.split()]
                                i_y = [float(v) for v in i_y_str.split()]
                            # Handle bracketed format
                            elif i_x_str.startswith('[') and i_x_str.endswith(']'):
                                i_x = float(i_x_str[1:-1])
                                i_y = float(i_y_str[1:-1])
                            else:
                                i_x = float(i_x_str)
                                i_y = float(i_y_str)
                            
                            kf.in_tan = {'x': i_x, 'y': i_y}
                        
                        if 'o_x' in attrs and 'o_y' in attrs:
                            o_x_str = attrs['o_x']
                            o_y_str = attrs['o_y']
                            
                            # Handle space-separated list format
                            if ' ' in o_x_str:
                                o_x = [float(v) for v in o_x_str.split()]
                                o_y = [float(v) for v in o_y_str.split()]
                            # Handle bracketed format
                            elif o_x_str.startswith('[') and o_x_str.endswith(']'):
                                o_x = float(o_x_str[1:-1])
                                o_y = float(o_y_str[1:-1])
                            else:
                                o_x = float(o_x_str)
                                o_y = float(o_y_str)
                            
                            kf.out_tan = {'x': o_x, 'y': o_y}
                        
                        # FIX: Add h attribute restoration
                        if 'h' in attrs:
                            kf.h = int(attrs['h'])
                        
                        # Add n and e attributes
                        if 'n' in attrs:
                            kf.n = attrs['n']
                        if 'e' in attrs:
                            try:
                                kf.e = json.loads(attrs['e']) if attrs['e'].startswith('[') else float(attrs['e'])
                            except:
                                kf.e = attrs['e']
                        
                        keyframes.append(kf)
                    idx += 1
                
                if keyframes:
                    scale_value = MultiDimensional(keyframes[0].value)
                    scale_value.keyframes = keyframes
                    transform.scale = scale_value
                else:
                    transform.scale = MultiDimensional(NVector(100, 100, 100))
                    
                if idx < len(lines) and lines[idx].startswith('(/scale)'):
                    idx += 1
            
            else:
                components = extract_numbers(line)
                if len(components) >= 3:
                    transform.scale = MultiDimensional(NVector(*components))
                elif len(components) == 2:
                    transform.scale = MultiDimensional(NVector(components[0], components[1], 100))
                elif len(components) == 1:
                    transform.scale = MultiDimensional(NVector(components[0], components[0], 100))
                idx += 1
        
        elif line.startswith('(rotation'):
            # Handle separated rotation
            if 'separated=true' in line:
                # Handle separated rotation
                transform.rotation = Value(0)
                transform.rotation.separated = True
                idx += 1
                while idx < len(lines) and not lines[idx].startswith('(/rotation)'):
                    if lines[idx].startswith('(rotation_x'):
                        if 'animated=true' in lines[idx]:
                            # Parse animated x component
                            idx += 1
                            keyframes = []
                            while idx < len(lines) and not lines[idx].startswith('(/rotation_x)'):
                                if lines[idx].startswith('(keyframe'):
                                    attrs = parse_tag_attrs(lines[idx])
                                    time = float(attrs.get('t', 0))
                                    value = float(attrs.get('s', 0))
                                    kf = Keyframe(time, value)
                                    
                                    if 'i_x' in attrs and 'i_y' in attrs:
                                        i_x_str = attrs['i_x']
                                        i_y_str = attrs['i_y']
                                        
                                        if i_x_str.startswith('[') and i_x_str.endswith(']'):
                                            i_x = float(i_x_str[1:-1])
                                        else:
                                            i_x = float(i_x_str)
                                        
                                        if i_y_str.startswith('[') and i_y_str.endswith(']'):
                                            i_y = float(i_y_str[1:-1])
                                        else:
                                            i_y = float(i_y_str)
                                        
                                        kf.in_tan = {'x': i_x, 'y': i_y}
                                    
                                    if 'o_x' in attrs and 'o_y' in attrs:
                                        o_x_str = attrs['o_x']
                                        o_y_str = attrs['o_y']
                                        
                                        if o_x_str.startswith('[') and o_x_str.endswith(']'):
                                            o_x = float(o_x_str[1:-1])
                                        else:
                                            o_x = float(o_x_str)
                                        
                                        if o_y_str.startswith('[') and o_y_str.endswith(']'):
                                            o_y = float(o_y_str[1:-1])
                                        else:
                                            o_y = float(o_y_str)
                                        
                                        kf.out_tan = {'x': o_x, 'y': o_y}
                                    
                                    keyframes.append(kf)
                                idx += 1
                            
                            if keyframes:
                                x_value = Value(keyframes[0].value if keyframes else 0)
                                x_value.keyframes = keyframes
                                transform.rotation.x = x_value
                            
                            if idx < len(lines) and lines[idx].startswith('(/rotation_x)'):
                                idx += 1
                        else:
                            value = extract_number(lines[idx])
                            transform.rotation.x = Value(value)
                            idx += 1
                    elif lines[idx].startswith('(rotation_y'):
                        value = extract_number(lines[idx])
                        transform.rotation.y = Value(value)
                        idx += 1
                    elif lines[idx].startswith('(rotation_z'):
                        value = extract_number(lines[idx])
                        transform.rotation.z = Value(value)
                        idx += 1
                    else:
                        idx += 1
                if lines[idx].startswith('(/rotation)'):
                    idx += 1
            elif 'animated=true' in line:
                idx += 1
                keyframes = []
                
                while idx < len(lines) and not lines[idx].startswith('(/rotation)'):
                    if lines[idx].startswith('(keyframe'):
                        attrs = parse_tag_attrs(lines[idx])
                        
                        time = float(attrs.get('t', 0))
                        s_str = attrs.get('s', '')
                        value = float(s_str) if s_str else 0
                        
                        kf = Keyframe(time, value)
                        
                        if 'i_x' in attrs and 'i_y' in attrs:
                            i_x_str = attrs['i_x']
                            i_y_str = attrs['i_y']
                            
                            # Handle space-separated list format
                            if ' ' in i_x_str:
                                i_x = [float(v) for v in i_x_str.split()]
                                i_y = [float(v) for v in i_y_str.split()]
                            # Handle bracketed format
                            elif i_x_str.startswith('[') and i_x_str.endswith(']'):
                                i_x = float(i_x_str[1:-1])
                                i_y = float(i_y_str[1:-1])
                            else:
                                i_x = float(i_x_str)
                                i_y = float(i_y_str)
                            
                            kf.in_tan = {'x': i_x, 'y': i_y}
                        
                        if 'o_x' in attrs and 'o_y' in attrs:
                            o_x_str = attrs['o_x']
                            o_y_str = attrs['o_y']
                            
                            # Handle space-separated list format
                            if ' ' in o_x_str:
                                o_x = [float(v) for v in o_x_str.split()]
                                o_y = [float(v) for v in o_y_str.split()]
                            # Handle bracketed format
                            elif o_x_str.startswith('[') and o_x_str.endswith(']'):
                                o_x = float(o_x_str[1:-1])
                                o_y = float(o_y_str[1:-1])
                            else:
                                o_x = float(o_x_str)
                                o_y = float(o_y_str)
                            
                            kf.out_tan = {'x': o_x, 'y': o_y}
                        if 'h' in attrs:
                            kf.h = int(attrs['h'])
                        # Handle n and e attributes
                        if 'n' in attrs:
                            kf.n = attrs['n']
                        if 'e' in attrs:
                            try:
                                kf.e = json.loads(attrs['e']) if attrs['e'].startswith('[') else float(attrs['e'])
                            except:
                                kf.e = attrs['e']
                        
                        keyframes.append(kf)
                    idx += 1
                
                if idx < len(lines) and lines[idx].startswith('(/rotation)'):
                    idx += 1
                
                if keyframes:
                    rot_value = Value(keyframes[0].value)
                    rot_value.keyframes = keyframes
                    transform.rotation = rot_value
            else:
                value = extract_number(line)
                transform.rotation = Value(value)
                idx += 1
        
        elif line.startswith('(opacity'):
            if 'animated=true' in line:
                idx += 1
                keyframes = []
                
                while idx < len(lines) and not lines[idx].startswith('(/opacity)'):
                    if lines[idx].startswith('(keyframe'):
                        attrs = parse_tag_attrs(lines[idx])
                        
                        time = float(attrs.get('t', 0))
                        s_str = attrs.get('s', '')
                        value = float(s_str) if s_str else 100
                        
                        kf = Keyframe(time, value)
                        
                        if 'i_x' in attrs and 'i_y' in attrs:
                            i_x_str = attrs['i_x']
                            i_y_str = attrs['i_y']
                            
                            # Handle space-separated list format
                            if ' ' in i_x_str:
                                i_x = [float(v) for v in i_x_str.split()]
                                i_y = [float(v) for v in i_y_str.split()]
                            # Handle bracketed format
                            elif i_x_str.startswith('[') and i_x_str.endswith(']'):
                                i_x = float(i_x_str[1:-1])
                                i_y = float(i_y_str[1:-1])
                            else:
                                i_x = float(i_x_str)
                                i_y = float(i_y_str)
                            
                            kf.in_tan = {'x': i_x, 'y': i_y}
                        
                        if 'o_x' in attrs and 'o_y' in attrs:
                            o_x_str = attrs['o_x']
                            o_y_str = attrs['o_y']
                            
                            # Handle space-separated list format
                            if ' ' in o_x_str:
                                o_x = [float(v) for v in o_x_str.split()]
                                o_y = [float(v) for v in o_y_str.split()]
                            # Handle bracketed format
                            elif o_x_str.startswith('[') and o_x_str.endswith(']'):
                                o_x = float(o_x_str[1:-1])
                                o_y = float(o_y_str[1:-1])
                            else:
                                o_x = float(o_x_str)
                                o_y = float(o_y_str)
                            
                            kf.out_tan = {'x': o_x, 'y': o_y}
                        
                        # ADD THIS: Parse h attribute for hold keyframe
                        if 'h' in attrs:
                            kf.h = int(attrs['h'])
                        
                        # Handle n and e attributes
                        if 'n' in attrs:
                            kf.n = attrs['n']
                        if 'e' in attrs:
                            try:
                                kf.e = json.loads(attrs['e']) if attrs['e'].startswith('[') else float(attrs['e'])
                            except:
                                kf.e = attrs['e']
                        
                        keyframes.append(kf)
                    idx += 1
                
                if idx < len(lines) and lines[idx].startswith('(/opacity)'):
                    idx += 1
                
                if keyframes:
                    op_value = Value(keyframes[0].value)
                    op_value.keyframes = keyframes
                    transform.opacity = op_value
            else:
                value = extract_number(line)
                transform.opacity = Value(value)
                idx += 1


        elif line.startswith('(anchor'):
            if 'animated=true' in line:
                idx += 1
                keyframes = []
                
                while idx < len(lines) and not lines[idx].startswith('(/anchor)'):
                    if lines[idx].startswith('(keyframe'):
                        attrs = parse_tag_attrs(lines[idx])
                        
                        time = float(attrs.get('t', 0))
                        
                        s_str = attrs.get('s', '')
                        if s_str:
                            values = [float(x) for x in s_str.split()]
                            if len(values) >= 2:
                                value = NVector(values[0], values[1], 0)
                            else:
                                value = NVector(0, 0, 0)
                        else:
                            value = NVector(0, 0, 0)
                        
                        kf = Keyframe(time, value)
                        
                        if 'i_x' in attrs and 'i_y' in attrs:
                            i_x_str = attrs['i_x']
                            i_y_str = attrs['i_y']
                            
                            # Handle space-separated list format
                            if ' ' in i_x_str:
                                i_x = [float(v) for v in i_x_str.split()]
                                i_y = [float(v) for v in i_y_str.split()]
                            # Handle bracketed format
                            elif i_x_str.startswith('[') and i_x_str.endswith(']'):
                                i_x = float(i_x_str[1:-1])
                                i_y = float(i_y_str[1:-1])
                            else:
                                i_x = float(i_x_str)
                                i_y = float(i_y_str)
                            
                            kf.in_tan = {'x': i_x, 'y': i_y}
                        
                        if 'o_x' in attrs and 'o_y' in attrs:
                            o_x_str = attrs['o_x']
                            o_y_str = attrs['o_y']
                            
                            # Handle space-separated list format
                            if ' ' in o_x_str:
                                o_x = [float(v) for v in o_x_str.split()]
                                o_y = [float(v) for v in o_y_str.split()]
                            # Handle bracketed format
                            elif o_x_str.startswith('[') and o_x_str.endswith(']'):
                                o_x = float(o_x_str[1:-1])
                                o_y = float(o_y_str[1:-1])
                            else:
                                o_x = float(o_x_str)
                                o_y = float(o_y_str)
                            
                            kf.out_tan = {'x': o_x, 'y': o_y}
                        
                        # Add to/ti attributes parsing
                        if 'to' in attrs:
                            try:
                                kf.to = json.loads(attrs['to'])
                            except:
                                pass
                        
                        if 'ti' in attrs:
                            try:
                                kf.ti = json.loads(attrs['ti'])
                            except:
                                pass
                        if 'h' in attrs:
                            kf.h = int(attrs['h'])
                        
                        keyframes.append(kf)
                    idx += 1
                
                if idx < len(lines) and lines[idx].startswith('(/anchor)'):
                    idx += 1
                
                if keyframes:
                    anchor_value = MultiDimensional(keyframes[0].value)
                    anchor_value.keyframes = keyframes
                    transform.anchor = anchor_value
            else:
                components = extract_numbers(line)
                if components:
                    if len(components) == 1:
                        transform.anchor = MultiDimensional(NVector(components[0], 0, 0))
                    else:
                        transform.anchor = MultiDimensional(NVector(*components))
                idx += 1
        
        elif line.startswith('(skew'):
            value = extract_number(line)
            transform.skew = Value(value)
            idx += 1
        
        elif line.startswith('(skew_axis'):
            value = extract_number(line)
            transform.skew_axis = Value(value)
            idx += 1
            
        elif line.strip() == '(/transform)':
            idx += 1
            break
        else:
            idx += 1
    
    return transform, idx


def parse_solid_layer_tag(lines, idx):
    """"""
    from .layers import SolidColorLayer
    
    solid_attrs = parse_tag_attrs(lines[idx])
    
    solid_layer = SolidColorLayer()
    solid_layer.type = ElementType.SOLID_LAYER
    solid_layer.index = int(float(solid_attrs.get("index", 0)))
    solid_layer.name = solid_attrs.get("name", "Solid Layer")
    solid_layer.in_point = float(solid_attrs.get("in_point", 0))
    solid_layer.out_point = float(solid_attrs.get("out_point", 60))
    solid_layer.start_time = float(solid_attrs.get("start_time", 0))
    solid_layer.color = solid_attrs.get("color", "#000000")
    solid_layer.width = float(solid_attrs.get("width", 512))
    solid_layer.height = float(solid_attrs.get("height", 512))
        
    # hasMask
    if "hasMask" in solid_attrs:
        solid_layer.hasMask = solid_attrs["hasMask"].lower() == "true"
        
    idx += 1
    while idx < len(lines):
        line = lines[idx]
        
        if line.startswith('(parent'):
            parent_index = int(extract_number(line))
            solid_layer.parent_index = parent_index
            idx += 1
        elif line.startswith('(transform'):
            transform, new_idx = parse_transform_tag(lines, idx)
            solid_layer.transform = transform
            idx = new_idx

        elif line.startswith('(masksProperties'):
            # masksProperties
            solid_layer.masksProperties = []
            idx += 1
            
            while idx < len(lines) and not lines[idx].startswith('(/masksProperties)'):
                if lines[idx].startswith('(mask '):
                    # mask
                    mask_attrs = parse_tag_attrs(lines[idx])
                    mask = {}
                    
                    #
                    if "inv" in mask_attrs:
                        mask["inv"] = mask_attrs["inv"].lower() == "true"
                    if "mode" in mask_attrs:
                        mask["mode"] = mask_attrs["mode"]
                    if "nm" in mask_attrs:
                        mask["nm"] = mask_attrs["nm"]
                    
                    idx += 1
                    
                    # mask
                    while idx < len(lines) and not lines[idx].startswith('(/mask)'):
                        if lines[idx].startswith('(mask_pt '):
                            # pt
                            pt_attrs = parse_tag_attrs(lines[idx])
                            mask["pt"] = {}
                            if "a" in pt_attrs:
                                mask["pt"]["a"] = int(pt_attrs["a"])
                            if "ix" in pt_attrs:
                                mask["pt"]["ix"] = int(pt_attrs["ix"])
                            
                            idx += 1
                            
                            # pt.k
                            if idx < len(lines) and lines[idx].startswith('(mask_pt_k'):
                                if lines[idx].startswith('(mask_pt_k_array'):
                                    # k
                                    mask["pt"]["k"] = []
                                    idx += 1
                                    
                                    #
                                    while idx < len(lines) and not lines[idx].startswith('(/mask_pt_k_array)'):
                                        if lines[idx].startswith('(mask_pt_keyframe'):
                                            kf_attrs = parse_tag_attrs(lines[idx])
                                            keyframe = {}
                                            
                                            if "t" in kf_attrs:
                                                keyframe["t"] = float(kf_attrs["t"])
                                            
                                            idx += 1
                                            
                                            # ...
                                            while idx < len(lines) and not lines[idx].startswith('(/mask_pt_keyframe)'):
                                                if lines[idx].startswith('(mask_pt_kf_i'):
                                                    i_attrs = parse_tag_attrs(lines[idx])
                                                    keyframe["i"] = {
                                                        "x": float(i_attrs.get("x", 0)),
                                                        "y": float(i_attrs.get("y", 0))
                                                    }
                                                    idx += 1
                                                elif lines[idx].startswith('(mask_pt_kf_o'):
                                                    o_attrs = parse_tag_attrs(lines[idx])
                                                    keyframe["o"] = {
                                                        "x": float(o_attrs.get("x", 0)),
                                                        "y": float(o_attrs.get("y", 0))
                                                    }
                                                    idx += 1
                                                elif lines[idx].startswith('(mask_pt_kf_s'):
                                                    keyframe["s"] = []
                                                    idx += 1
                                                    while idx < len(lines) and not lines[idx].startswith('(/mask_pt_kf_s)'):
                                                        if lines[idx].startswith('(mask_pt_kf_shape'):
                                                            shape_attrs = parse_tag_attrs(lines[idx])
                                                            shape = {}
                                                            if "c" in shape_attrs:
                                                                shape["c"] = shape_attrs["c"].lower() == "true"
                                                            idx += 1
                                                            while idx < len(lines) and not lines[idx].startswith('(/mask_pt_kf_shape)'):
                                                                if lines[idx].startswith('(mask_pt_kf_shape_i'):
                                                                    values = extract_numbers(lines[idx])
                                                                    shape["i"] = []
                                                                    for i in range(0, len(values), 2):
                                                                        if i + 1 < len(values):
                                                                            shape["i"].append([values[i], values[i+1]])
                                                                    idx += 1
                                                                elif lines[idx].startswith('(mask_pt_kf_shape_o'):
                                                                    values = extract_numbers(lines[idx])
                                                                    shape["o"] = []
                                                                    for i in range(0, len(values), 2):
                                                                        if i + 1 < len(values):
                                                                            shape["o"].append([values[i], values[i+1]])
                                                                    idx += 1
                                                                elif lines[idx].startswith('(mask_pt_kf_shape_v'):
                                                                    values = extract_numbers(lines[idx])
                                                                    shape["v"] = []
                                                                    for i in range(0, len(values), 2):
                                                                        if i + 1 < len(values):
                                                                            shape["v"].append([values[i], values[i+1]])
                                                                    idx += 1
                                                                else:
                                                                    idx += 1
                                                            if lines[idx].startswith('(/mask_pt_kf_shape)'):
                                                                idx += 1
                                                            keyframe["s"].append(shape)
                                                        else:
                                                            idx += 1
                                                    if lines[idx].startswith('(/mask_pt_kf_s)'):
                                                        idx += 1
                                                else:
                                                    idx += 1
                                            
                                            if lines[idx].startswith('(/mask_pt_keyframe)'):
                                                idx += 1
                                            
                                            mask["pt"]["k"].append(keyframe)
                                        else:
                                            idx += 1
                                    
                                    if lines[idx].startswith('(/mask_pt_k_array)'):
                                        idx += 1
                                
                                else:
                                    # kshape
                                    mask["pt"]["k"] = {}
                                    idx += 1
                                    
                                    # shape
                                    while idx < len(lines) and not lines[idx].startswith('(/mask_pt_k)'):
                                        if lines[idx].startswith('(mask_pt_k_c'):
                                            # closed
                                            parts = lines[idx].split()
                                            if len(parts) > 1:
                                                mask["pt"]["k"]["c"] = parts[1].rstrip(')').lower() == "true"
                                            idx += 1
                                        
                                        elif lines[idx].startswith('(mask_pt_k_i'):
                                            # i
                                            values = extract_numbers(lines[idx])
                                            mask["pt"]["k"]["i"] = []
                                            for i in range(0, len(values), 2):
                                                if i + 1 < len(values):
                                                    mask["pt"]["k"]["i"].append([values[i], values[i+1]])
                                            idx += 1
                                        
                                        elif lines[idx].startswith('(mask_pt_k_o'):
                                            # o
                                            values = extract_numbers(lines[idx])
                                            mask["pt"]["k"]["o"] = []
                                            for i in range(0, len(values), 2):
                                                if i + 1 < len(values):
                                                    mask["pt"]["k"]["o"].append([values[i], values[i+1]])
                                            idx += 1
                                        
                                        elif lines[idx].startswith('(mask_pt_k_v'):
                                            # v
                                            values = extract_numbers(lines[idx])
                                            mask["pt"]["k"]["v"] = []
                                            for i in range(0, len(values), 2):
                                                if i + 1 < len(values):
                                                    mask["pt"]["k"]["v"].append([values[i], values[i+1]])
                                            idx += 1
                                        else:
                                            idx += 1
                                    
                                    if lines[idx].startswith('(/mask_pt_k)'):
                                        idx += 1
                            
                            if idx < len(lines) and lines[idx].startswith('(/mask_pt)'):
                                idx += 1
                        
                        elif lines[idx].startswith('(mask_o '):
                            # opacity
                            o_attrs = parse_tag_attrs(lines[idx])
                            mask["o"] = {}
                            if "a" in o_attrs:
                                mask["o"]["a"] = int(o_attrs["a"])
                            if "k" in o_attrs:
                                mask["o"]["k"] = float(o_attrs["k"])
                            if "ix" in o_attrs:
                                mask["o"]["ix"] = int(o_attrs["ix"])
                            idx += 1
                        
                        elif lines[idx].startswith('(mask_x '):
                            # dilate
                            x_attrs = parse_tag_attrs(lines[idx])
                            mask["x"] = {}
                            if "a" in x_attrs:
                                mask["x"]["a"] = int(x_attrs["a"])
                            if "k" in x_attrs:
                                mask["x"]["k"] = float(x_attrs["k"])
                            if "ix" in x_attrs:
                                mask["x"]["ix"] = int(x_attrs["ix"])
                            idx += 1
                        else:
                            idx += 1
                    
                    if lines[idx].startswith('(/mask)'):
                        idx += 1
                    
                    solid_layer.masksProperties.append(mask)
                else:
                    idx += 1
            
            if lines[idx].startswith('(/masksProperties)'):
                idx += 1

        elif lines[idx].startswith('(effects'):
            # effects
            effects, new_idx = parse_effects_tag(lines, idx)
            solid_layer.ef = effects
            idx = new_idx



        elif line.startswith('(tm '):
            # tm -
            tm_attrs = parse_tag_attrs(line)
            tm_data = {}
            if 'a' in tm_attrs:
                tm_data['a'] = int(tm_attrs['a'])
            if 'ix' in tm_attrs:
                tm_data['ix'] = int(tm_attrs['ix'])
            
            # keyframes
            idx += 1
            keyframes = []
            while idx < len(lines):
                line = lines[idx]
                if line.startswith('(keyframe'):
                    kf_attrs = parse_tag_attrs(line)
                    kf = {}
                    if 't' in kf_attrs:
                        kf['t'] = float(kf_attrs['t'])
                    if 's' in kf_attrs:
                        kf['s'] = [float(kf_attrs['s'])]
                    if 'h' in kf_attrs:
                        kf['h'] = int(kf_attrs['h'])
                    
                    #
                    if 'i_x' in kf_attrs or 'i_y' in kf_attrs:
                        kf['i'] = {}
                        if 'i_x' in kf_attrs:
                            kf['i']['x'] = [float(kf_attrs['i_x'])]
                        if 'i_y' in kf_attrs:
                            kf['i']['y'] = [float(kf_attrs['i_y'])]
                    
                    if 'o_x' in kf_attrs or 'o_y' in kf_attrs:
                        kf['o'] = {}
                        if 'o_x' in kf_attrs:
                            kf['o']['x'] = [float(kf_attrs['o_x'])]
                        if 'o_y' in kf_attrs:
                            kf['o']['y'] = [float(kf_attrs['o_y'])]
                    
                    keyframes.append(kf)
                    idx += 1
                elif line.startswith('(value'):
                    #
                    val = extract_number(line)
                    tm_data['k'] = val
                    idx += 1
                elif line.strip() == '(/tm)':
                    if keyframes:
                        tm_data['k'] = keyframes
                    idx += 1
                    break
                else:
                    idx += 1
            
            solid_layer.tm = tm_data
        
        
        elif line.startswith('(tt'):
            tt_value = extract_number(line)
            solid_layer.tt = int(tt_value)
            idx += 1
        elif line.startswith('(tp'):
            tp_value = extract_number(line)
            solid_layer.tp = int(tp_value)
            idx += 1
        elif line.startswith('(td'):
            td_value = extract_number(line)
            solid_layer.td = int(td_value)
            idx += 1
            
        elif line.strip() == '(/solid_layer)':
            idx += 1
            break
        else:
            idx += 1
    
    return solid_layer, idx


def parse_text_layer_tag(lines, idx):
    """ - """
    text_attrs = parse_tag_attrs(lines[idx])
    
    text_layer = TextLayer()
    text_layer.type = ElementType.TEXT_LAYER
    text_layer.index = int(float(text_attrs.get("index", 0)))
    text_layer.name = text_attrs.get("name", "Text Layer")
    text_layer.in_point = float(text_attrs.get("in_point", 0))
    text_layer.out_point = float(text_attrs.get("out_point", 60))
    text_layer.start_time = float(text_attrs.get("start_time", 0))
    #text_layer.ct = int(text_attrs.get("ct", 0))
    
    # ln
    #text_layer.ln =(text_attrs.get("ln", ""))
    if "ct" in text_attrs:
        text_layer.ct = int(text_attrs.get("ct"))
    # hasMask
    if "hasMask" in text_attrs:
        text_layer.hasMask = text_attrs["hasMask"].lower() == "true"

    idx += 1
    while idx < len(lines):
        line = lines[idx]
        

        if line.startswith('(tt'):
            tt_value = extract_number(line)
            text_layer.tt = int(tt_value)
            idx += 1
        elif line.startswith('(tp'):
            tp_value = extract_number(line)
            text_layer.tp = int(tp_value)
            idx += 1
        elif line.startswith('(td'):
            td_value = extract_number(line)
            text_layer.td = int(td_value)
            idx += 1
        elif line.startswith('(parent'):
            parent_index = int(extract_number(line))
            text_layer.parent_index = parent_index
            idx += 1
        
        elif lines[idx].startswith('(effects'):
            # effects
            effects, new_idx = parse_effects_tag(lines, idx)
            text_layer.ef = effects
            idx = new_idx
            
        
        elif line.startswith('(transform'):
            transform, new_idx = parse_transform_tag(lines, idx)
            text_layer.transform = transform
            idx = new_idx


        elif line.startswith('(text_data'):
            #
            idx += 1
            keyframes = []
            path_option = {}
            more_options = {}
            animators = []
            
            while idx < len(lines) and not lines[idx].startswith('(/text_data)'):
                if lines[idx].startswith('(text_keyframes'):
                    #
                    idx += 1
                    while idx < len(lines) and not lines[idx].startswith('(/text_keyframes)'):
                        if lines[idx].startswith('(text_keyframe'):
                            # text_keyframe
                            line_content = lines[idx]
                            
                            #
                            doc_data = {}
                            time = 0
                            
                            # t -
                            t_match = re.search(r't=([\d\.\-]+)', line_content)
                            if t_match:
                                time = float(t_match.group(1))
                            
                            # font_size -
                            fs_match = re.search(r'font_size=([\d\.\-]+)', line_content)
                            if fs_match:
                                doc_data['s'] = float(fs_match.group(1))
                            
                            # font_family
                            ff_match = re.search(r'font_family="([^"]*)"', line_content)
                            if ff_match:
                                doc_data['f'] = ff_match.group(1)
                            
                            # text -
                            text_match = re.search(r'text="([^"]*(?:\\.[^"]*)*)"', line_content)
                            if text_match:
                                text_val = text_match.group(1)
                                doc_data['t'] = text_val.replace('\\"', '"')
                            
                            # ca -
                            ca_match = re.search(r'ca=([\d]+)', line_content)
                            if ca_match:
                                doc_data['ca'] = int(ca_match.group(1))
                            
                            # justify -
                            j_match = re.search(r'justify=([\d]+)', line_content)
                            if j_match:
                                doc_data['j'] = int(j_match.group(1))
                            
                            # tracking -
                            tr_match = re.search(r'tracking=([\d\.\-]+)', line_content)
                            if tr_match:
                                doc_data['tr'] = float(tr_match.group(1))
                            
                            # line_height -
                            lh_match = re.search(r'line_height=([\d\.\-]+)', line_content)
                            if lh_match:
                                doc_data['lh'] = float(lh_match.group(1))
                            
                            # letter_spacing -
                            ls_match = re.search(r'letter_spacing=([\d\.\-]+)', line_content)
                            if ls_match:
                                doc_data['ls'] = float(ls_match.group(1))
                            
                            # fill_color
                            fc_match = re.search(r'fill_color=\[([^\]]+)\]', line_content)
                            if fc_match:
                                fc_str = fc_match.group(1)
                                fc_values = [float(v.strip()) for v in fc_str.split(',')]
                                doc_data['fc'] = fc_values
                            
                            # ADD PARSING FOR MISSING FIELDS
                            # stroke_color
                            sc_match = re.search(r'stroke_color=\[([^\]]+)\]', line_content)
                            if sc_match:
                                sc_str = sc_match.group(1)
                                sc_values = [float(v.strip()) for v in sc_str.split(',')]
                                doc_data['sc'] = sc_values
                            
                            # stroke_width -
                            sw_match = re.search(r'stroke_width=([\d\.\-]+)', line_content)
                            if sw_match:
                                doc_data['sw'] = float(sw_match.group(1))
                            
                            # offset
                            of_match = re.search(r'offset=(true|false)', line_content)
                            if of_match:
                                doc_data['of'] = of_match.group(1) == 'true'
                            
                            # Extract wrap_size (sz)
                            sz_match = re.search(r'wrap_size=\[([^\]]+)\]', line_content)
                            if sz_match:
                                sz_str = sz_match.group(1)
                                sz_values = [float(v.strip()) for v in sz_str.split(',')]
                                doc_data['sz'] = sz_values

                            # Extract wrap_position (ps)
                            ps_match = re.search(r'wrap_position=\[([^\]]+)\]', line_content)
                            if ps_match:
                                ps_str = ps_match.group(1)
                                ps_values = [float(v.strip()) for v in ps_str.split(',')]
                                doc_data['ps'] = ps_values
                            
                            keyframes.append({"s": doc_data, "t": time})
                            idx += 1
                        else:
                            idx += 1
                    
                    if lines[idx].startswith('(/text_keyframes'):
                        idx += 1
                
                elif lines[idx].startswith('(document_full'):
                    #
                    doc_json = extract_string_value(lines[idx])
                    if doc_json:
                        try:
                            keyframes = json.loads(doc_json)
                        except json.JSONDecodeError:
                            keyframes = []
                    idx += 1
                
                elif lines[idx].startswith('(path_option'):
                    path_json = extract_string_value(lines[idx])
                    if path_json:
                        try:
                            path_option = json.loads(path_json)
                        except json.JSONDecodeError:
                            path_option = {}
                    idx += 1
                
                elif lines[idx].startswith('(more_options') and not lines[idx].endswith('")'):
                    # more_options
                    line_content = lines[idx]
                    
                    # g
                    g_match = re.search(r'\(more_options g (\d+)', line_content)
                    g_value = int(g_match.group(1)) if g_match else 1
                    
                    # alignment
                    alignment_data = {"a": 0, "k": [0, 0], "ix": 2}
                    
                    # a
                    a_match = re.search(r'alignment a=(\d+)', line_content)
                    if a_match:
                        alignment_data['a'] = int(a_match.group(1))
                    
                    # alignment_k
                    k_match = re.search(r'alignment_k ([\d\.\-\s]+)(?:alignment_ix|$|\))', line_content)
                    if k_match:
                        k_values = [float(v) for v in k_match.group(1).strip().split()]
                        alignment_data['k'] = k_values
                    
                    # alignment_ix
                    ix_match = re.search(r'alignment_ix (\d+)', line_content)
                    if ix_match:
                        alignment_data['ix'] = int(ix_match.group(1))
                    
                    more_options = {"g": g_value, "a": alignment_data}
                    idx += 1
                
                elif lines[idx].startswith('(more_options "'):
                    # JSON
                    more_json = extract_string_value(lines[idx])
                    if more_json:
                        try:
                            more_options = json.loads(more_json)
                        except json.JSONDecodeError:
                            more_options = {}
                    idx += 1
                
                elif lines[idx].startswith('(animators'):
                    animators = []
                    idx += 1
                    
                    while idx < len(lines) and not lines[idx].startswith('(/animators'):
                        if lines[idx].startswith('(animator '):
                            animator = {}
                            nm_match = re.search(r'nm="([^"]*)"', lines[idx])
                            if nm_match:
                                animator["nm"] = nm_match.group(1)
                            idx += 1
                            
                            # Parse range selector
                            if idx < len(lines) and lines[idx].startswith('(range_selector'):
                                range_selector = {}
                                params = lines[idx]
                                
                                # Parse basic range selector properties
                                # Fix: Use [^)\s]+ to exclude closing parenthesis and whitespace
                                for prop in ["t", "r", "b", "sh", "rn"]:
                                    match = re.search(rf'{prop}=([^)\s]+)', params)
                                    if match:
                                        range_selector[prop] = float(match.group(1)) if '.' in match.group(1) else int(match.group(1))
                                
                                idx += 1
                                
                                # Parse range properties
                                while idx < len(lines) and not lines[idx].startswith('(/range_selector'):
                                    prop_line = lines[idx]
                                    
                                    # Map property names
                                    prop_map = {
                                        "range_start": "s",
                                        "range_end": "e",
                                        "range_offset": "o",
                                        "amount": "a",
                                        "max_ease": "xe",
                                        "min_ease": "ne",
                                        "s_m": "sm"
                                    }
                                    
                                    found_prop = False
                                    for prop_name, prop_key in prop_map.items():
                                        if prop_line.startswith(f'({prop_name} '):
                                            found_prop = True
                                            # Check if animated
                                            a_match = re.search(r'a=(\d+)', prop_line)
                                            
                                            if a_match and a_match.group(1) == "1":
                                                # Animated property - parse keyframes
                                                prop_data = {"a": 1, "k": []}
                                                idx += 1
                                                
                                                while idx < len(lines) and lines[idx].startswith(f'({prop_name}_keyframe'):
                                                    kf_line = lines[idx]
                                                    keyframe = {}
                                                    
                                                    # Parse time
                                                    t_match = re.search(r't=([^)\s]+)', kf_line)
                                                    if t_match:
                                                        keyframe["t"] = float(t_match.group(1))
                                                    
                                                    # Parse value
                                                    s_match = re.search(r's=([^)]+?)(?:\s+[io]_|$|\))', kf_line)
                                                    if s_match:
                                                        s_values = s_match.group(1).strip().split()
                                                        if len(s_values) > 1:
                                                            keyframe["s"] = [float(v) for v in s_values]
                                                        else:
                                                            keyframe["s"] = [float(s_values[0])]
                                                    
                                                    # Parse interpolation
                                                    for interp in ["i", "o"]:
                                                        x_match = re.search(rf'{interp}_x=([^)]+?)(?:\s+[io]_|$|\))', kf_line)
                                                        y_match = re.search(rf'{interp}_y=([^)]+?)(?:\s+[io]_|$|\))', kf_line)
                                                        
                                                        if x_match or y_match:
                                                            keyframe[interp] = {}
                                                            if x_match:
                                                                x_values = x_match.group(1).strip().split()
                                                                keyframe[interp]["x"] = [float(v) for v in x_values]
                                                            if y_match:
                                                                y_values = y_match.group(1).strip().split()
                                                                keyframe[interp]["y"] = [float(v) for v in y_values]
                                                    
                                                    prop_data["k"].append(keyframe)
                                                    idx += 1
                                                
                                                # Skip closing tag if present
                                                if idx < len(lines) and lines[idx] == f'(/{prop_name})':
                                                    idx += 1
                                                
                                                range_selector[prop_key] = prop_data
                                            else:
                                                # Static property - ALWAYS use the {a, k, ix} structure
                                                k_match = re.search(r'k=([^)\s]+)', prop_line)
                                                ix_match = re.search(r'ix=(\d+)', prop_line)
                                                
                                                k_value = 0
                                                if k_match:
                                                    k_str = k_match.group(1)
                                                    # Handle both single values and space-separated values
                                                    if ' ' in prop_line[prop_line.find('k='):]:
                                                        # Multiple values - extract until we hit ix= or )
                                                        k_full_match = re.search(r'k=([\d.\s-]+?)(?:\s+ix=|\))', prop_line)
                                                        if k_full_match:
                                                            k_values = k_full_match.group(1).strip().split()
                                                            k_value = [float(v) for v in k_values]
                                                        else:
                                                            k_value = float(k_str)
                                                    else:
                                                        k_value = float(k_str)
                                                
                                                range_selector[prop_key] = {
                                                    "a": int(a_match.group(1)) if a_match else 0,
                                                    "k": k_value,
                                                    "ix": int(ix_match.group(1)) if ix_match else 0
                                                }
                                                idx += 1
                                            break
                                    
                                    if not found_prop:
                                        idx += 1
                                
                                animator["s"] = range_selector
                                if idx < len(lines) and lines[idx] == '(/range_selector)':
                                    idx += 1

                            # Parse animator properties
                            if idx < len(lines) and lines[idx].startswith('(animator_properties'):
                                idx += 1
                                a_props = {}
                                
                                prop_map = {
                                    "opacity_animators": "o",
                                    "position_animators": "p",
                                    "scale_animators": "s",
                                    "rotation_animators": "r",
                                    "anchor_animators": "a",
                                    "skew_animators": "sk",
                                    "skew_axis_animators": "sa",
                                    "fill_colo_animatorsr": "fc",
                                    "stroke_color_animators": "sc",
                                    "stroke_width_animators": "sw",
                                    "tracking_animators": "t"
                                }
                                
                                while idx < len(lines) and not lines[idx].startswith('(/animator_properties'):
                                    line = lines[idx]
                                    
                                    # Check each property type
                                    for prop_name, prop_key in prop_map.items():
                                        if line.startswith(f'({prop_name} '):
                                            # Check if animated
                                            a_match = re.search(r'a=(\d+)', line)
                                            
                                            if a_match and a_match.group(1) == "1":
                                                # Animated property - parse keyframes
                                                prop_data = {"a": 1, "k": []}
                                                idx += 1
                                                
                                                # Parse keyframes
                                                while idx < len(lines) and lines[idx].startswith('(keyframe '):
                                                    kf_line = lines[idx]
                                                    keyframe = {}
                                                    
                                                    # Parse time
                                                    t_match = re.search(r't=([^)\s]+)', kf_line)
                                                    if t_match:
                                                        keyframe["t"] = float(t_match.group(1))
                                                    
                                                    # Parse value(s) - now properly handle quoted values
                                                    s_match = re.search(r's="([^"]*)"', kf_line)
                                                    if s_match:
                                                        s_values = s_match.group(1).strip().split()
                                                        if len(s_values) > 1:
                                                            keyframe["s"] = [float(v) for v in s_values]
                                                        else:
                                                            keyframe["s"] = [float(s_values[0])]
                                                    
                                                    # Parse 'to' and 'ti'
                                                    to_match = re.search(r'to="([^"]*)"', kf_line)
                                                    if to_match:
                                                        to_values = to_match.group(1).strip().split()
                                                        if len(to_values) > 1:
                                                            keyframe["to"] = [float(v) for v in to_values]
                                                        else:
                                                            keyframe["to"] = [float(to_values[0])]
                                                    
                                                    ti_match = re.search(r'ti="([^"]*)"', kf_line)
                                                    if ti_match:
                                                        ti_values = ti_match.group(1).strip().split()
                                                        if len(ti_values) > 1:
                                                            keyframe["ti"] = [float(v) for v in ti_values]
                                                        else:
                                                            keyframe["ti"] = [float(ti_values[0])]
                                                    
                                                    
                                                    # Parse interpolation - handle quoted values
                                                    for interp in ["i", "o"]:
                                                        x_match = re.search(rf'{interp}_x="([^"]*)"', kf_line)
                                                        y_match = re.search(rf'{interp}_y="([^"]*)"', kf_line)
                                                        
                                                        if x_match or y_match:
                                                            keyframe[interp] = {}
                                                            if x_match:
                                                                x_values = x_match.group(1).strip().split()
                                                                if len(x_values) > 1:
                                                                    keyframe[interp]["x"] = [float(v) for v in x_values]
                                                                else:
                                                                    keyframe[interp]["x"] = float(x_values[0])
                                                            if y_match:
                                                                y_values = y_match.group(1).strip().split()
                                                                if len(y_values) > 1:
                                                                    keyframe[interp]["y"] = [float(v) for v in y_values]
                                                                else:
                                                                    keyframe[interp]["y"] = float(y_values[0])
                                                    
                                                    prop_data["k"].append(keyframe)
                                                    idx += 1
                                                
                                                # Check for closing tag
                                                if idx < len(lines) and lines[idx] == f'(/{prop_name})':
                                                    idx += 1
                                                
                                                a_props[prop_key] = prop_data
                                            else:
                                                # Static property
                                                k_match = re.search(r'k=(\[[\d.,\s-]+\]|[^)\s]+)', line)
                                                ix_match = re.search(r'ix=(\d+)', line)
                                                
                                                k_value = 0
                                                if k_match:
                                                    k_str = k_match.group(1)
                                                    if k_str.startswith('['):
                                                        # Parse array
                                                        k_str = k_str.strip('[]')
                                                        k_value = [float(v.strip()) for v in k_str.split(',')]
                                                    else:
                                                        k_value = float(k_str)
                                                
                                                a_props[prop_key] = {
                                                    "a": int(a_match.group(1)) if a_match else 0,
                                                    "k": k_value,
                                                    "ix": int(ix_match.group(1)) if ix_match else 0
                                                }
                                                idx += 1
                                            break
                                    else:
                                        # Line doesn't match any property
                                        idx += 1
                                
                                animator["a"] = a_props
                                idx += 1  # Skip (/animator_properties)


                            idx += 1  # Skip (/animator)
                            animators.append(animator)
                        else:
                            idx += 1
                    
                    text_layer.data.animators = animators
                    idx += 1  # Skip (/animators)

                else:
                    idx += 1
            
            #
            if keyframes:
                text_layer.data.document = Value(keyframes)
            text_layer.data.path_option = path_option
            text_layer.data.more_options = more_options
            text_layer.data.animators = animators
            
            if lines[idx].startswith('(/text_data)'):
                idx += 1



        elif line.startswith('(masksProperties'):
            # masksProperties
            text_layer.masksProperties = []
            idx += 1
            
            while idx < len(lines) and not lines[idx].startswith('(/masksProperties)'):
                if lines[idx].startswith('(mask '):
                    # mask
                    mask_attrs = parse_tag_attrs(lines[idx])
                    mask = {}
                    
                    #
                    if "inv" in mask_attrs:
                        mask["inv"] = mask_attrs["inv"].lower() == "true"
                    if "mode" in mask_attrs:
                        mask["mode"] = mask_attrs["mode"]
                    if "nm" in mask_attrs:
                        mask["nm"] = mask_attrs["nm"]
                    
                    idx += 1
                    
                    # mask
                    while idx < len(lines) and not lines[idx].startswith('(/mask)'):
                        if lines[idx].startswith('(mask_pt '):
                            # pt
                            pt_attrs = parse_tag_attrs(lines[idx])
                            mask["pt"] = {}
                            if "a" in pt_attrs:
                                mask["pt"]["a"] = int(pt_attrs["a"])
                            if "ix" in pt_attrs:
                                mask["pt"]["ix"] = int(pt_attrs["ix"])
                            
                            idx += 1
                            
                            # pt.k
                            if idx < len(lines) and lines[idx].startswith('(mask_pt_k'):
                                if lines[idx].startswith('(mask_pt_k_array'):
                                    # k
                                    mask["pt"]["k"] = []
                                    idx += 1
                                    
                                    #
                                    while idx < len(lines) and not lines[idx].startswith('(/mask_pt_k_array)'):
                                        if lines[idx].startswith('(mask_pt_keyframe'):
                                            kf_attrs = parse_tag_attrs(lines[idx])
                                            keyframe = {}
                                            
                                            if "t" in kf_attrs:
                                                keyframe["t"] = float(kf_attrs["t"])
                                            
                                            idx += 1
                                            
                                            # ...
                                            while idx < len(lines) and not lines[idx].startswith('(/mask_pt_keyframe)'):
                                                if lines[idx].startswith('(mask_pt_kf_i'):
                                                    i_attrs = parse_tag_attrs(lines[idx])
                                                    keyframe["i"] = {
                                                        "x": float(i_attrs.get("x", 0)),
                                                        "y": float(i_attrs.get("y", 0))
                                                    }
                                                    idx += 1
                                                elif lines[idx].startswith('(mask_pt_kf_o'):
                                                    o_attrs = parse_tag_attrs(lines[idx])
                                                    keyframe["o"] = {
                                                        "x": float(o_attrs.get("x", 0)),
                                                        "y": float(o_attrs.get("y", 0))
                                                    }
                                                    idx += 1
                                                elif lines[idx].startswith('(mask_pt_kf_s'):
                                                    keyframe["s"] = []
                                                    idx += 1
                                                    while idx < len(lines) and not lines[idx].startswith('(/mask_pt_kf_s)'):
                                                        if lines[idx].startswith('(mask_pt_kf_shape'):
                                                            shape_attrs = parse_tag_attrs(lines[idx])
                                                            shape = {}
                                                            if "c" in shape_attrs:
                                                                shape["c"] = shape_attrs["c"].lower() == "true"
                                                            idx += 1
                                                            while idx < len(lines) and not lines[idx].startswith('(/mask_pt_kf_shape)'):
                                                                if lines[idx].startswith('(mask_pt_kf_shape_i'):
                                                                    values = extract_numbers(lines[idx])
                                                                    shape["i"] = []
                                                                    for i in range(0, len(values), 2):
                                                                        if i + 1 < len(values):
                                                                            shape["i"].append([values[i], values[i+1]])
                                                                    idx += 1
                                                                elif lines[idx].startswith('(mask_pt_kf_shape_o'):
                                                                    values = extract_numbers(lines[idx])
                                                                    shape["o"] = []
                                                                    for i in range(0, len(values), 2):
                                                                        if i + 1 < len(values):
                                                                            shape["o"].append([values[i], values[i+1]])
                                                                    idx += 1
                                                                elif lines[idx].startswith('(mask_pt_kf_shape_v'):
                                                                    values = extract_numbers(lines[idx])
                                                                    shape["v"] = []
                                                                    for i in range(0, len(values), 2):
                                                                        if i + 1 < len(values):
                                                                            shape["v"].append([values[i], values[i+1]])
                                                                    idx += 1
                                                                else:
                                                                    idx += 1
                                                            if lines[idx].startswith('(/mask_pt_kf_shape)'):
                                                                idx += 1
                                                            keyframe["s"].append(shape)
                                                        else:
                                                            idx += 1
                                                    if lines[idx].startswith('(/mask_pt_kf_s)'):
                                                        idx += 1
                                                else:
                                                    idx += 1
                                            
                                            if lines[idx].startswith('(/mask_pt_keyframe)'):
                                                idx += 1
                                            
                                            mask["pt"]["k"].append(keyframe)
                                        else:
                                            idx += 1
                                    
                                    if lines[idx].startswith('(/mask_pt_k_array)'):
                                        idx += 1
                                
                                else:
                                    # kshape
                                    mask["pt"]["k"] = {}
                                    idx += 1
                                    
                                    # shape
                                    while idx < len(lines) and not lines[idx].startswith('(/mask_pt_k)'):
                                        if lines[idx].startswith('(mask_pt_k_c'):
                                            # closed
                                            parts = lines[idx].split()
                                            if len(parts) > 1:
                                                mask["pt"]["k"]["c"] = parts[1].rstrip(')').lower() == "true"
                                            idx += 1
                                        
                                        elif lines[idx].startswith('(mask_pt_k_i'):
                                            # i
                                            values = extract_numbers(lines[idx])
                                            mask["pt"]["k"]["i"] = []
                                            for i in range(0, len(values), 2):
                                                if i + 1 < len(values):
                                                    mask["pt"]["k"]["i"].append([values[i], values[i+1]])
                                            idx += 1
                                        
                                        elif lines[idx].startswith('(mask_pt_k_o'):
                                            # o
                                            values = extract_numbers(lines[idx])
                                            mask["pt"]["k"]["o"] = []
                                            for i in range(0, len(values), 2):
                                                if i + 1 < len(values):
                                                    mask["pt"]["k"]["o"].append([values[i], values[i+1]])
                                            idx += 1
                                        
                                        elif lines[idx].startswith('(mask_pt_k_v'):
                                            # v
                                            values = extract_numbers(lines[idx])
                                            mask["pt"]["k"]["v"] = []
                                            for i in range(0, len(values), 2):
                                                if i + 1 < len(values):
                                                    mask["pt"]["k"]["v"].append([values[i], values[i+1]])
                                            idx += 1
                                        else:
                                            idx += 1
                                    
                                    if lines[idx].startswith('(/mask_pt_k)'):
                                        idx += 1
                            
                            if idx < len(lines) and lines[idx].startswith('(/mask_pt)'):
                                idx += 1
                        
                        elif lines[idx].startswith('(mask_o '):
                            # opacity
                            o_attrs = parse_tag_attrs(lines[idx])
                            mask["o"] = {}
                            if "a" in o_attrs:
                                mask["o"]["a"] = int(o_attrs["a"])
                            if "k" in o_attrs:
                                mask["o"]["k"] = float(o_attrs["k"])
                            if "ix" in o_attrs:
                                mask["o"]["ix"] = int(o_attrs["ix"])
                            idx += 1
                        
                        elif lines[idx].startswith('(mask_x '):
                            # dilate
                            x_attrs = parse_tag_attrs(lines[idx])
                            mask["x"] = {}
                            if "a" in x_attrs:
                                mask["x"]["a"] = int(x_attrs["a"])
                            if "k" in x_attrs:
                                mask["x"]["k"] = float(x_attrs["k"])
                            if "ix" in x_attrs:
                                mask["x"]["ix"] = int(x_attrs["ix"])
                            idx += 1
                        else:
                            idx += 1
                    
                    if lines[idx].startswith('(/mask)'):
                        idx += 1
                    
                    text_layer.masksProperties.append(mask)
                else:
                    idx += 1
            
            if lines[idx].startswith('(/masksProperties)'):
                idx += 1


        elif line.strip() == '(/text_layer)':
            idx += 1
            break
        else:
            idx += 1
    
    return text_layer, idx

def parse_group_tag(lines, idx):
    """Parse a group tag and its contents"""
    group_attrs = parse_tag_attrs(lines[idx])
    
    group = Group()
    group.shapes = []
    
    group.name = group_attrs.get("name", "")
    
    # property_index
    if "ix" in group_attrs:
        group.property_index = int(group_attrs.get("ix", 1))
    if "cix" in group_attrs:
        group.cix = int(group_attrs.get("cix", 2))
    if "bm" in group_attrs:
        group.bm = 0
    if "hd" in group_attrs:
        group.hd = group_attrs.get("hd", "false").lower() == "true"
    if "mn" in group_attrs:
        group.mn = group_attrs.get("mn", "")
    if "np" in group_attrs:
        group.number_of_properties = int(float(group_attrs.get("np")))
    
        
    idx += 1
    while idx < len(lines):
        if lines[idx].startswith('("TransformShape"'):
            transform_shape, new_idx = parse_transform_shape_tag(lines, idx)
            group.shapes.append(transform_shape)
            idx = new_idx
        elif lines[idx].startswith('(group'):
            nested_group, new_idx = parse_group_tag(lines, idx)
            group.shapes.append(nested_group)
            idx = new_idx
        elif lines[idx].startswith('(path'):
            path, new_idx = parse_path_tag(lines, idx)
            group.shapes.append(path)
            idx = new_idx
        elif lines[idx].startswith('(fill'):
            fill, new_idx = parse_fill_tag(lines, idx)
            group.shapes.append(fill)
            idx = new_idx
        elif lines[idx].startswith('(stroke'):
            stroke, new_idx = parse_stroke_tag(lines, idx)
            group.shapes.append(stroke)
            idx = new_idx
        elif lines[idx].startswith('(rect'):
            rect, new_idx = parse_rect_tag(lines, idx)
            group.shapes.append(rect)
            idx = new_idx
        elif lines[idx].startswith('(ellipse'):
            ellipse, new_idx = parse_ellipse_tag(lines, idx)
            group.shapes.append(ellipse)
            idx = new_idx
        elif lines[idx].startswith('(star'):
            star, new_idx = parse_star_tag(lines, idx)
            group.shapes.append(star)
            idx = new_idx
        elif lines[idx].startswith('(trim'):
            trim, new_idx = parse_trim_tag(lines, idx)
            group.shapes.append(trim)
            idx = new_idx
        elif lines[idx].startswith('(repeater'):
            repeater, new_idx = parse_repeater_tag(lines, idx)
            group.shapes.append(repeater)
            idx = new_idx
        elif lines[idx].startswith('(gradient_fill'):
            gradient_fill, new_idx = parse_gradient_fill_tag(lines, idx)
            group.shapes.append(gradient_fill)
            idx = new_idx
        elif lines[idx].startswith('(gradient_stroke'):
            gradient_stroke, new_idx = parse_gradient_stroke_tag(lines, idx)
            group.shapes.append(gradient_stroke)
            idx = new_idx
        elif lines[idx].startswith('(merge'):
            merge, new_idx = parse_merge_tag(lines, idx)
            group.shapes.append(merge)
            idx = new_idx
        elif lines[idx].startswith('(rounded_corners'):
            rounded_corners, new_idx = parse_rounded_corners_tag(lines, idx)
            group.shapes.append(rounded_corners)
            idx = new_idx
        elif lines[idx].startswith('(twist'):
            twist, new_idx = parse_twist_tag(lines, idx)
            group.shapes.append(twist)
            idx = new_idx
        elif lines[idx].startswith('(zig_zag'):
            zig_zag, new_idx = parse_zig_zag_tag(lines, idx)
            group.shapes.append(zig_zag)
            idx = new_idx
        elif lines[idx].strip() == '(/group)':
            idx += 1
            break
        else:
            idx += 1
    
    return group, idx

def parse_zig_zag_tag(lines, idx):
    """"""
    zig_zag = ZigZag()
    
    #
    if lines[idx].startswith('(zig_zag'):
        attrs = lines[idx][8:-1].strip()  # Remove '(zig_zag' and ')'
        
        #
        if 'name=' in attrs:
            import re
            name_match = re.search(r'name="([^"]*)"', attrs)
            if name_match:
                zig_zag.name = name_match.group(1)
        
        if 'ix=' in attrs:
            import re
            ix_match = re.search(r'ix=(\d+)', attrs)
            if ix_match:
                zig_zag.property_index = int(ix_match.group(1))
    
    idx += 1
    
    #
    while idx < len(lines) and not lines[idx].startswith('(/zig_zag)'):
        line = lines[idx].strip()
        
        if line.startswith('(frequency'):
            # frequency
            parts = line.split()
            if len(parts) > 1:
                value_str = parts[1].rstrip(')')
                zig_zag.frequency = Value(float(value_str))
        
        elif line.startswith('(amplitude'):
            # amplitude
            parts = line.split()
            if len(parts) > 1:
                value_str = parts[1].rstrip(')')
                zig_zag.amplitude = Value(float(value_str))
        
        elif line.startswith('(point_type'):
            # point_type
            parts = line.split()
            if len(parts) > 1:
                value_str = parts[1].rstrip(')')
                zig_zag.point_type = Value(float(value_str))
        
        idx += 1
    
    #
    if idx < len(lines) and lines[idx].startswith('(/zig_zag)'):
        idx += 1
    
    return zig_zag, idx
 


def parse_trim_tag(lines, idx):
    """Parse trim tag and its contents - handle keyframes properly with e field"""
    trim_attrs = parse_tag_attrs(lines[idx])
    
    trim = Trim()
    trim.name = trim_attrs.get("name", "")
    
    if "ix" in trim_attrs:
        trim.property_index = int(trim_attrs.get("ix", 1))
    
    idx += 1
    while idx < len(lines):
        line = lines[idx]
        
        if line.startswith('(start'):
            if 'animated=true' in line:
                # Process animated start with keyframes
                idx += 1
                keyframes = []
                while idx < len(lines) and not lines[idx].startswith('(/start)'):
                    if lines[idx].startswith('(keyframe'):
                        attrs = parse_tag_attrs(lines[idx])
                        time = float(attrs.get('t', 0))
                        s_str = attrs.get('s', '0')
                        value = float(s_str) if s_str else 0
                        
                        kf = Keyframe(time, value)
                        
                        # Handle e field (end value)
                        if 'e' in attrs:
                            e_str = attrs.get('e', '0')
                            kf.e = float(e_str) if e_str else 0
                        
                        # Handle easing parameters
                        if 'i_x' in attrs and 'i_y' in attrs:
                            i_x_str = attrs['i_x']
                            i_y_str = attrs['i_y']
                            
                            if ' ' in i_x_str:
                                i_x = [float(v) for v in i_x_str.split()]
                            else:
                                i_x = float(i_x_str)
                            
                            if ' ' in i_y_str:
                                i_y = [float(v) for v in i_y_str.split()]
                            else:
                                i_y = float(i_y_str)
                            
                            kf.in_tan = {'x': i_x, 'y': i_y}
                        
                        if 'o_x' in attrs and 'o_y' in attrs:
                            o_x_str = attrs['o_x']
                            o_y_str = attrs['o_y']
                            
                            if ' ' in o_x_str:
                                o_x = [float(v) for v in o_x_str.split()]
                            else:
                                o_x = float(o_x_str)
                            
                            if ' ' in o_y_str:
                                o_y = [float(v) for v in o_y_str.split()]
                            else:
                                o_y = float(o_y_str)
                            
                            kf.out_tan = {'x': o_x, 'y': o_y}
                        
                        keyframes.append(kf)
                    idx += 1
                
                if keyframes:
                    trim.start = Value(keyframes[0].value)
                    trim.start.keyframes = keyframes
                    trim.start.animated = True
                else:
                    trim.start = Value(0)
                    trim.start.animated = True
                
                if idx < len(lines) and lines[idx].startswith('(/start)'):
                    idx += 1
            else:
                value = extract_number(line)
                trim.start = Value(value)
                idx += 1
                
        elif line.startswith('(end'):
            if 'animated=true' in line:
                # Process animated end with keyframes
                idx += 1
                keyframes = []
                while idx < len(lines) and not lines[idx].startswith('(/end)'):
                    if lines[idx].startswith('(keyframe'):
                        attrs = parse_tag_attrs(lines[idx])
                        time = float(attrs.get('t', 0))
                        s_str = attrs.get('s', '100')
                        value = float(s_str) if s_str else 100
                        
                        kf = Keyframe(time, value)
                        
                        # Handle e field (end value)
                        if 'e' in attrs:
                            e_str = attrs.get('e', '100')
                            kf.e = float(e_str) if e_str else 100
                        
                        # Handle easing parameters
                        if 'i_x' in attrs and 'i_y' in attrs:
                            i_x_str = attrs['i_x']
                            i_y_str = attrs['i_y']
                            
                            if ' ' in i_x_str:
                                i_y = [float(v) for v in i_x_str.split()]
                            else:
                                i_x = float(i_x_str)
                            
                            if ' ' in i_y_str:
                                i_y = [float(v) for v in i_y_str.split()]
                            else:
                                i_y = float(i_y_str)
                            
                            kf.in_tan = {'x': i_x, 'y': i_y}
                        
                        if 'o_x' in attrs and 'o_y' in attrs:
                            o_x_str = attrs['o_x']
                            o_y_str = attrs['o_y']
                            
                            if ' ' in o_x_str:
                                o_x = [float(v) for v in o_x_str.split()]
                            else:
                                o_x = float(o_x_str)
                            
                            if ' ' in o_y_str:
                                o_y = [float(v) for v in o_y_str.split()]
                            else:
                                o_y = float(o_y_str)
                            
                            kf.out_tan = {'x': o_x, 'y': o_y}
                        
                        keyframes.append(kf)
                    idx += 1
                
                if keyframes:
                    trim.end = Value(keyframes[0].value)
                    trim.end.keyframes = keyframes
                    trim.end.animated = True
                else:
                    trim.end = Value(100)
                    trim.end.animated = True
                
                if idx < len(lines) and lines[idx].startswith('(/end)'):
                    idx += 1
            else:
                value = extract_number(line)
                trim.end = Value(value)
                idx += 1
                
        elif line.startswith('(offset'):
            if 'animated=true' in line:
                # Process animated offset with keyframes
                idx += 1
                keyframes = []
                while idx < len(lines) and not lines[idx].startswith('(/offset)'):
                    if lines[idx].startswith('(keyframe'):
                        attrs = parse_tag_attrs(lines[idx])
                        time = float(attrs.get('t', 0))
                        s_str = attrs.get('s', '0')
                        value = float(s_str) if s_str else 0
                        
                        kf = Keyframe(time, value)
                        
                        # Handle e field (end value)
                        if 'e' in attrs:
                            e_str = attrs.get('e', '0')
                            kf.e = float(e_str) if e_str else 0
                        
                        # Handle easing parameters
                        if 'i_x' in attrs and 'i_y' in attrs:
                            i_x_str = attrs['i_x']
                            i_y_str = attrs['i_y']
                            
                            if ' ' in i_x_str:
                                i_x = [float(v) for v in i_x_str.split()]
                            else:
                                i_x = float(i_x_str)
                            
                            if ' ' in i_y_str:
                                i_y = [float(v) for v in i_y_str.split()]
                            else:
                                i_y = float(i_y_str)
                            
                            kf.in_tan = {'x': i_x, 'y': i_y}
                        
                        if 'o_x' in attrs and 'o_y' in attrs:
                            o_x_str = attrs['o_x']
                            o_y_str = attrs['o_y']
                            
                            if ' ' in o_x_str:
                                o_x = [float(v) for v in o_x_str.split()]
                            else:
                                o_x = float(o_x_str)
                            
                            if ' ' in o_y_str:
                                o_y = [float(v) for v in o_y_str.split()]
                            else:
                                o_y = float(o_y_str)
                            
                            kf.out_tan = {'x': o_x, 'y': o_y}
                        
                        keyframes.append(kf)
                    idx += 1
                
                if keyframes:
                    trim.offset = Value(keyframes[0].value)
                    trim.offset.keyframes = keyframes
                    trim.offset.animated = True
                else:
                    trim.offset = Value(0)
                    trim.offset.animated = True
                
                if idx < len(lines) and lines[idx].startswith('(/offset)'):
                    idx += 1
            else:
                value = extract_number(line)
                trim.offset = Value(value)
                idx += 1
                
        elif line.startswith('(multiple'):
            value = int(extract_number(line))
            trim.multiple = TrimMultipleShapes(value)
            idx += 1
        elif line.strip() == '(/trim)':
            idx += 1
            break
        else:
            idx += 1
    
    return trim, idx


def parse_star_tag(lines, idx):
    """Parse star tag and its contents"""
    star_attrs = parse_tag_attrs(lines[idx])
    
    star = Star()
    star.name = star_attrs.get("name", "")
    
    if "ix" in star_attrs:
        star.property_index = int(star_attrs.get("ix", 1))
    
    # directionstar_type
    if "d" in star_attrs:
        star.direction = float(star_attrs.get("d", 1))
    else:
        star.direction = 1
    
    if "sy" in star_attrs:
        try:
            sy_value = int(star_attrs.get("sy", 1))
            # StarType: 1(Star), 2(Polygon)
            if sy_value in [1, 2]:
                star.star_type = StarType(sy_value)
            else:
                # Star(1)
                star.star_type = StarType.Star
        except (ValueError, KeyError):
            star.star_type = StarType.Star
    else:
        star.star_type = StarType.Star
    
    idx += 1
    while idx < len(lines):
        line = lines[idx]
        
        if line.startswith('(position'):
            attrs = parse_tag_attrs(line)
            components = extract_numbers(line)
            if components:
                star.position = MultiDimensional(NVector(*components))
            if "ix" in attrs:
                star.position_ix = int(attrs["ix"])
            idx += 1
        elif line.startswith('(inner_radius'):
            attrs = parse_tag_attrs(line)
            value = extract_number(line)
            star.inner_radius = Value(value)
            if "ix" in attrs:
                star.inner_radius_ix = int(attrs["ix"])
            idx += 1
        elif line.startswith('(outer_radius'):
            attrs = parse_tag_attrs(line)
            value = extract_number(line)
            star.outer_radius = Value(value)
            if "ix" in attrs:
                star.outer_radius_ix = int(attrs["ix"])
            idx += 1
        elif line.startswith('(inner_roundness'):
            attrs = parse_tag_attrs(line)
            value = extract_number(line)
            star.inner_roundness = Value(value)
            if "ix" in attrs:
                star.inner_roundness_ix = int(attrs["ix"])
            idx += 1
        elif line.startswith('(outer_roundness'):
            attrs = parse_tag_attrs(line)
            value = extract_number(line)
            star.outer_roundness = Value(value)
            if "ix" in attrs:
                star.outer_roundness_ix = int(attrs["ix"])
            idx += 1
        elif line.startswith('(points_star'):
            attrs = parse_tag_attrs(line)
            value = extract_number(line)
            star.points = Value(value)
            if "ix" in attrs:
                star.points_ix = int(attrs["ix"])
            idx += 1
        elif line.startswith('(star_rotation'):
            attrs = parse_tag_attrs(line)
            value = extract_number(line)
            star.rotation = Value(value)
            if "ix" in attrs:
                star.rotation_ix = int(attrs["ix"])
            idx += 1
        elif line.strip() == '(/star)':
            idx += 1
            break
        else:
            idx += 1
    
    return star, idx

def parse_repeater_tag(lines, idx):
    """Parse repeater tag and its contents - Fixed to parse all transform values"""
    repeater_attrs = parse_tag_attrs(lines[idx])
    
    repeater = Repeater()
    repeater.name = repeater_attrs.get("name", "")
    
    if "ix" in repeater_attrs:
        repeater.property_index = int(repeater_attrs.get("ix", 1))
    
    # Initialize default values
    repeater.copies = Value(1)
    repeater.offset = Value(0)
    repeater.composite = 1  # Default value
    
    idx += 1
    while idx < len(lines):
        line = lines[idx]
        
        if line.startswith('(copies'):
            attrs = parse_tag_attrs(line)
            if 'animated=true' in line:
                # Handle animated copies
                value = extract_number(line)
                repeater.copies = Value(value)
                repeater.copies.animated = True
            else:
                value = extract_number(line)
                repeater.copies = Value(value)
            # Extract ix value
            if "ix" in attrs:
                repeater.copies_ix = int(attrs["ix"])
            idx += 1
        elif line.startswith('(repeater_offset'):
            attrs = parse_tag_attrs(line)
            if 'animated=true' in line:
                # Handle animated offset
                idx += 1
                keyframes = []
                offset_ix = None
                while idx < len(lines) and not lines[idx].startswith('(/repeater_offset)'):
                    if lines[idx].startswith('(keyframe'):
                        attrs = parse_tag_attrs(lines[idx])
                        time = float(attrs.get('t', 0))
                        value = float(attrs.get('s', 0))
                        kf = Keyframe(time, value)
                        
                        # Handle easing parameters
                        if 'i_x' in attrs and 'i_y' in attrs:
                            i_x_str = attrs['i_x']
                            i_y_str = attrs['i_y']
                            
                            if i_x_str.startswith('[') and i_x_str.endswith(']'):
                                i_x = float(i_x_str[1:-1])
                            else:
                                i_x = float(i_x_str)
                            
                            if i_y_str.startswith('[') and i_y_str.endswith(']'):
                                i_y = float(i_y_str[1:-1])
                            else:
                                i_y = float(i_y_str)
                            
                            kf.in_tan = {'x': i_x, 'y': i_y}
                        
                        if 'o_x' in attrs and 'o_y' in attrs:
                            o_x_str = attrs['o_x']
                            o_y_str = attrs['o_y']
                            
                            if o_x_str.startswith('[') and o_x_str.endswith(']'):
                                o_x = float(o_x_str[1:-1])
                            else:
                                o_x = float(o_x_str)
                            
                            if o_y_str.startswith('[') and o_y_str.endswith(']'):
                                o_y = float(o_y_str[1:-1])
                            else:
                                o_y = float(o_y_str)
                            
                            kf.out_tan = {'x': o_x, 'y': o_y}
                        
                        keyframes.append(kf)
                    elif lines[idx].startswith('(offset_ix'):
                        offset_ix = int(extract_number(lines[idx]))
                    idx += 1
                
                if keyframes:
                    repeater.offset = Value(keyframes[0].value if keyframes else 0)
                    repeater.offset.keyframes = keyframes
                    repeater.offset.animated = True
                
                if offset_ix is not None:
                    repeater.offset_ix = offset_ix
                
                if lines[idx].startswith('(/repeater_offset)'):
                    idx += 1
            else:
                value = extract_number(line)
                repeater.offset = Value(value)
                # Extract ix value
                if "ix" in attrs:
                    repeater.offset_ix = int(attrs["ix"])
                idx += 1
        elif line.startswith('(composite'):
            value = int(extract_number(line))
            repeater.composite = value
            idx += 1
        elif line.startswith('(repeater_transform'):
            # Parse transform
            transform = TransformShape()
            transform.type = "tr"
            transform.name = "Transform"
            
            # Set default values
            transform.anchor = MultiDimensional(NVector(0, 0))
            transform.position = MultiDimensional(NVector(0, 0))
            transform.scale = MultiDimensional(NVector(100, 100))
            transform.rotation = Value(0)
            transform.start_opacity = Value(100)
            transform.end_opacity = Value(100)
            
            idx += 1
            while idx < len(lines) and not lines[idx].startswith('(/repeater_transform)'):
                if lines[idx].startswith('(tr_position'):
                    components = extract_numbers(lines[idx])
                    if len(components) >= 2:
                        transform.position = MultiDimensional(NVector(components[0], components[1]))
                elif lines[idx].startswith('(tr_anchor'):
                    components = extract_numbers(lines[idx])
                    if len(components) >= 2:
                        transform.anchor = MultiDimensional(NVector(components[0], components[1]))
                elif lines[idx].startswith('(tr_scale'):
                    components = extract_numbers(lines[idx])
                    if len(components) >= 2:
                        transform.scale = MultiDimensional(NVector(components[0], components[1]))
                elif lines[idx].startswith('(tr_rotation'):
                    # PARSE ROTATION VALUE - THIS WAS MISSING!
                    value = extract_number(lines[idx])
                    transform.rotation = Value(value)
                elif lines[idx].startswith('(tr_start_opacity'):
                    value = extract_number(lines[idx])
                    transform.start_opacity = Value(value)
                elif lines[idx].startswith('(tr_end_opacity'):
                    value = extract_number(lines[idx])
                    transform.end_opacity = Value(value)
                elif lines[idx].startswith('(tr_p_ix'):
                    transform.position_ix = int(extract_number(lines[idx]))
                elif lines[idx].startswith('(tr_a_ix'):
                    transform.anchor_ix = int(extract_number(lines[idx]))
                elif lines[idx].startswith('(tr_s_ix'):
                    transform.scale_ix = int(extract_number(lines[idx]))
                elif lines[idx].startswith('(tr_r_ix'):
                    transform.rotation_ix = int(extract_number(lines[idx]))
                elif lines[idx].startswith('(tr_so_ix'):
                    transform.start_opacity_ix = int(extract_number(lines[idx]))
                elif lines[idx].startswith('(tr_eo_ix'):
                    transform.end_opacity_ix = int(extract_number(lines[idx]))
                idx += 1
            
            if lines[idx].startswith('(/repeater_transform)'):
                idx += 1
            
            repeater.transform = transform
        elif line.strip() == '(/repeater)':
            idx += 1
            break
        else:
            idx += 1
    
    return repeater, idx


def parse_merge_tag(lines, idx):
    """Parse merge tag and its contents"""
    merge_attrs = parse_tag_attrs(lines[idx])
    
    merge = Merge()
    merge.name = merge_attrs.get("name", "")
    
    if "ix" in merge_attrs:
        merge.property_index = int(merge_attrs.get("ix", 1))
    
    idx += 1
    while idx < len(lines):
        line = lines[idx]
        
        if line.startswith('(merge_mode'):
            value = int(extract_number(line))
            merge.merge_mode = value
            idx += 1
        elif line.strip() == '(/merge)':
            idx += 1
            break
        else:
            idx += 1
    
    return merge, idx


def parse_rounded_corners_tag(lines, idx):
    """Parse rounded corners tag and its contents"""
    rc_attrs = parse_tag_attrs(lines[idx])
    
    rounded_corners = RoundedCorners()
    rounded_corners.name = rc_attrs.get("name", "")
    
    if "ix" in rc_attrs:
        rounded_corners.property_index = int(rc_attrs.get("ix", 1))
    
    idx += 1
    while idx < len(lines):
        line = lines[idx]
        
        if line.startswith('(radius'):
            value = extract_number(line)
            rounded_corners.radius = Value(value)
            idx += 1
        elif line.strip() == '(/rounded_corners)':
            idx += 1
            break
        else:
            idx += 1
    
    return rounded_corners, idx


def parse_twist_tag(lines, idx):
    """Parse twist tag and its contents"""
    twist_attrs = parse_tag_attrs(lines[idx])
    
    twist = Twist()
    twist.name = twist_attrs.get("name", "")
    
    if "ix" in twist_attrs:
        twist.property_index = int(twist_attrs.get("ix", 1))
    
    idx += 1
    while idx < len(lines):
        line = lines[idx]
        
        if line.startswith('(angle'):
            value = extract_number(line)
            twist.angle = Value(value)
            idx += 1
        elif line.startswith('(center'):
            components = extract_numbers(line)
            if components:
                twist.center = MultiDimensional(NVector(*components))
            idx += 1
        elif line.strip() == '(/twist)':
            idx += 1
            break
        else:
            idx += 1
    
    return twist, idx

def parse_stroke_tag(lines, idx):
    """"""
    stroke_attrs = parse_tag_attrs(lines[idx])
    
    stroke = Stroke()
    stroke.name = stroke_attrs.get("name", "")
    
    # property_index
    if "ix" in stroke_attrs:
        stroke.property_index = int(stroke_attrs["ix"])
    
    # bm
    if "bm" in stroke_attrs:
        stroke.bm = int(stroke_attrs.get("bm", 0))
    else:
        stroke.bm = 0
    
    #
    if stroke_attrs.get("color_animated") == "true":
        #  - look for color_keyframe tags
        stroke.color = ColorValue(Color(0, 0, 0))
        stroke.color.keyframes = []
        
        idx += 1
        while idx < len(lines) and not lines[idx].startswith('(/color_animated)'):
            if lines[idx].startswith('(color_keyframe'):
                kf_attrs = parse_tag_attrs(lines[idx])
                time = float(kf_attrs.get('t', 0))
                r = float(kf_attrs.get('r', 0))
                g = float(kf_attrs.get('g', 0))
                b = float(kf_attrs.get('b', 0))
                
                color = Color(r, g, b)
                kf = Keyframe(time, color)
                
                if 'i_x' in kf_attrs and 'i_y' in kf_attrs:
                    kf.in_tan = {
                        'x': [float(kf_attrs['i_x'])],
                        'y': [float(kf_attrs['i_y'])]
                    }
                
                if 'o_x' in kf_attrs and 'o_y' in kf_attrs:
                    kf.out_tan = {
                        'x': [float(kf_attrs['o_x'])],
                        'y': [float(kf_attrs['o_y'])]
                    }
                
                stroke.color.keyframes.append(kf)
            idx += 1
    else:
        #
        r = float(stroke_attrs.get("r", 0))
        g = float(stroke_attrs.get("g", 0))
        b = float(stroke_attrs.get("b", 0))
        stroke.color = ColorValue(Color(r, g, b))
    
    #  -
    stroke.color_dimensions = int(stroke_attrs.get("color_dim", 3))
    
    # aix
    if "has_c_a" in stroke_attrs:
        stroke.has_c_a = stroke_attrs["has_c_a"] == "True"
    if "has_c_ix" in stroke_attrs:
        stroke.has_c_ix = stroke_attrs["has_c_ix"] == "True"
    if "c_ix" in stroke_attrs:
        stroke.c_ix = int(stroke_attrs["c_ix"])
    
    # line_capline_join -
    if "lc" in stroke_attrs:
        try:
            lc_value = int(stroke_attrs["lc"])
            # LineCap: 1(Butt), 2(Round), 3(Square)
            if lc_value in [1, 2, 3]:
                stroke.line_cap = LineCap(lc_value)
            else:
                # Round(2)
                stroke.line_cap = LineCap(2)
        except (ValueError, KeyError):
            stroke.line_cap = LineCap(2)
    else:
        stroke.line_cap = LineCap(2)

    if "lj" in stroke_attrs:
        try:
            lj_value = int(stroke_attrs["lj"])
            # LineJoin: 1(Miter), 2(Round), 3(Bevel)
            if lj_value in [1, 2, 3]:
                stroke.line_join = LineJoin(lj_value)
            else:
                # Round(2)
                stroke.line_join = LineJoin(2)
        except (ValueError, KeyError):
            stroke.line_join = LineJoin(2)
    else:
        stroke.line_join = LineJoin(2)
    
    # miter_limit
    if "ml" in stroke_attrs:
        stroke.miter_limit = float(stroke_attrs["ml"])
    
    # ml2
    if "ml2_animated" in stroke_attrs:
        try:
            keyframes_data = json.loads(stroke_attrs["ml2_animated"])
            ml2_value = Value(10)
            ml2_value.keyframes = []
            for kf_data in keyframes_data:
                time = kf_data.get('t', 0)
                value = kf_data.get('s', 10)
                kf = Keyframe(time, value)
                if 'i' in kf_data:
                    kf.in_tan = kf_data['i']
                if 'o' in kf_data:
                    kf.out_tan = kf_data['o']
                ml2_value.keyframes.append(kf)
            stroke.ml2 = ml2_value
        except:
            stroke.ml2 = Value(10)
    elif "ml2" in stroke_attrs:
        stroke.ml2 = Value(float(stroke_attrs["ml2"]))
    
    if "ml2_ix" in stroke_attrs:
        stroke.ml2_ix = int(stroke_attrs["ml2_ix"])
    
    # Parse width - check next line
    if idx + 1 < len(lines):
        if lines[idx + 1].startswith('(width_animated'):
            stroke.width = Value(1)
            stroke.width.keyframes = []
            idx += 2  # Skip the width_animated tag
            
            while idx < len(lines) and not lines[idx].startswith('(/width_animated)'):
                if lines[idx].startswith('(width_keyframe'):
                    kf_attrs = parse_tag_attrs(lines[idx])
                    time = float(kf_attrs.get('t', 0))
                    value = float(kf_attrs.get('s', 1))
                    
                    kf = Keyframe(time, value)
                    
                    if 'i_x' in kf_attrs and 'i_y' in kf_attrs:
                        kf.in_tan = {
                            'x': float(kf_attrs['i_x']),
                            'y': float(kf_attrs['i_y'])
                        }
                    
                    if 'o_x' in kf_attrs and 'o_y' in kf_attrs:
                        kf.out_tan = {
                            'x': float(kf_attrs['o_x']),
                            'y': float(kf_attrs['o_y'])
                        }
                    
                    stroke.width.keyframes.append(kf)
                idx += 1
            
            if stroke.width.keyframes:
                stroke.width.value = stroke.width.keyframes[0].value
            idx += 1  # Skip the /width_animated tag
        elif lines[idx + 1].startswith('(width '):
            # Static width in separate tag
            idx += 1
            width_value = extract_number(lines[idx])
            stroke.width = Value(width_value)
            idx += 1
        else:
            stroke.width = Value(1)
            idx += 1
    else:
        stroke.width = Value(1)
        idx += 1
    
    # Parse opacity - check next line
    if idx < len(lines):
        if lines[idx].startswith('(opacity_animated'):
            stroke.opacity = Value(100)
            stroke.opacity.keyframes = []
            idx += 1
            
            while idx < len(lines) and not lines[idx].startswith('(/opacity_animated)'):
                if lines[idx].startswith('(opacity_keyframe'):
                    kf_attrs = parse_tag_attrs(lines[idx])
                    time = float(kf_attrs.get('t', 0))
                    value = float(kf_attrs.get('s', 100))
                    
                    kf = Keyframe(time, value)
                    
                    if 'i_x' in kf_attrs and 'i_y' in kf_attrs:
                        kf.in_tan = {
                            'x': float(kf_attrs['i_x']),
                            'y': float(kf_attrs['i_y'])
                        }
                    
                    if 'o_x' in kf_attrs and 'o_y' in kf_attrs:
                        kf.out_tan = {
                            'x': float(kf_attrs['o_x']),
                            'y': float(kf_attrs['o_y'])
                        }
                    
                    stroke.opacity.keyframes.append(kf)
                idx += 1
            
            if stroke.opacity.keyframes:
                stroke.opacity.value = stroke.opacity.keyframes[0].value
            idx += 1
        elif lines[idx].startswith('(opacity '):
            # Static opacity in separate tag
            opacity_value = extract_number(lines[idx])
            stroke.opacity = Value(opacity_value)
            idx += 1
        else:
            stroke.opacity = Value(100)
    
    # Dashes handling - updated to parse keyframe format
    if idx < len(lines):
        stroke.dashes = []
        
        # Keep parsing dashes until we hit something that's not dash-related
        while idx < len(lines):
            if lines[idx].startswith('(dash_animated'):
                # Animated dash
                dash_attrs = parse_tag_attrs(lines[idx])
                dash = StrokeDash()
                dash.type = StrokeDashType(dash_attrs.get('type', 'd'))
                dash.name = dash_attrs.get('name', '')
                if 'v_ix' in dash_attrs:
                    dash.v_ix = int(dash_attrs['v_ix'])
                
                dash.length = Value(0)
                dash.length.keyframes = []
                
                idx += 1
                while idx < len(lines) and not lines[idx].startswith('(/dash_animated)'):
                    if lines[idx].startswith('(dash_keyframe'):
                        kf_attrs = parse_tag_attrs(lines[idx])
                        time = float(kf_attrs.get('t', 0))
                        value = float(kf_attrs.get('s', 0))
                        
                        kf = Keyframe(time, value)
                        
                        # Restore hold property if present
                        if 'h' in kf_attrs:
                            kf.hold = kf_attrs['h'] == 'True' if kf_attrs['h'] in ['True', 'False'] else bool(kf_attrs['h'])
                        
                        if 'i_x' in kf_attrs and 'i_y' in kf_attrs:
                            kf.in_tan = {
                                'x': float(kf_attrs['i_x']),
                                'y': float(kf_attrs['i_y'])
                            }
                        
                        if 'o_x' in kf_attrs and 'o_y' in kf_attrs:
                            kf.out_tan = {
                                'x': float(kf_attrs['o_x']),
                                'y': float(kf_attrs['o_y'])
                            }
                        
                        dash.length.keyframes.append(kf)
                    idx += 1
                
                if dash.length.keyframes:
                    dash.length.value = dash.length.keyframes[0].value
                
                stroke.dashes.append(dash)
                idx += 1
                
            elif lines[idx].startswith('(dash '):
                # Static dash
                dash_attrs = parse_tag_attrs(lines[idx])
                dash = StrokeDash()
                dash.type = StrokeDashType(dash_attrs.get('type', 'd'))
                dash.length = Value(float(dash_attrs.get('length', 0)))
                dash.name = dash_attrs.get('name', '')
                if 'v_ix' in dash_attrs:
                    dash.v_ix = int(dash_attrs['v_ix'])
                
                stroke.dashes.append(dash)
                idx += 1
                
            elif lines[idx].startswith('(dashes'):
                # Old format for backwards compatibility
                dashes_str = extract_string_value(lines[idx])
                if dashes_str:
                    dash_pairs = dashes_str.split(';')
                    for dash_pair in dash_pairs:
                        parts = dash_pair.split('|')
                        if len(parts) >= 2:
                            dash = StrokeDash()
                            dash.type = StrokeDashType(parts[0])
                            
                            try:
                                dash.length = Value(float(parts[1]))
                            except ValueError:
                                dash.length = Value(0)
                            
                            if len(parts) > 2 and parts[2]:
                                dash.name = parts[2]
                            if len(parts) > 3 and parts[3]:
                                try:
                                    dash.v_ix = int(parts[3])
                                except:
                                    pass
                            stroke.dashes.append(dash)
                idx += 1
                break
            else:
                # Not a dash-related tag, stop parsing dashes
                break
    
    return stroke, idx


def parse_rect_tag(lines, idx):
    """"""
    rect_attrs = parse_tag_attrs(lines[idx])
    
    rect = Rect()
    rect.name = rect_attrs.get("name", "")
    
    # property_index
    if "ix" in rect_attrs:
        rect.property_index = int(rect_attrs.get("ix", 1))
    # hd
    if "hd" in rect_attrs:
        rect.hd = rect_attrs.get("hd", "false").lower() == "true"
    
    # direction
    if "d" in rect_attrs:
        rect.direction = float(rect_attrs.get("d", 1))
    else:
        rect.direction = 1
    
    idx += 1
    while idx < len(lines):
        line = lines[idx]
        
        # Handle animated position
        if line.startswith('(position') and 'animated=true' in line:
            idx += 1
            keyframes = []
            while idx < len(lines) and not lines[idx].startswith('(/position)'):
                if lines[idx].startswith('(keyframe'):
                    attrs = parse_tag_attrs(lines[idx])
                    time = float(attrs.get('t', 0))
                    s_str = attrs.get('s', '')
                    if s_str:
                        values = [float(x) for x in s_str.split()]
                        value = NVector(*values) if values else NVector(0, 0)
                    else:
                        value = NVector(0, 0)
                    kf = Keyframe(time, value)

                    # Handle easing parameters -
                    if 'i_x' in attrs and 'i_y' in attrs:
                        i_x = attrs['i_x']
                        i_y = attrs['i_y']
                        #
                        if ' ' in i_x:
                            i_x_vals = [float(v) for v in i_x.split()]
                            i_y_vals = [float(v) for v in i_y.split()]
                        else:
                            i_x_vals = [float(i_x)]
                            i_y_vals = [float(i_y)]
                        kf.in_tan = {
                            'x': i_x_vals,
                            'y': i_y_vals
                        }

                    if 'o_x' in attrs and 'o_y' in attrs:
                        o_x = attrs['o_x']
                        o_y = attrs['o_y']
                        #
                        if ' ' in o_x:
                            o_x_vals = [float(v) for v in o_x.split()]
                            o_y_vals = [float(v) for v in o_y.split()]
                        else:
                            o_x_vals = [float(o_x)]
                            o_y_vals = [float(o_y)]
                        kf.out_tan = {
                            'x': o_x_vals,
                            'y': o_y_vals
                        }
                    
                    if 'to' in attrs:
                        try:
                            kf.to = json.loads(attrs['to'])
                        except:
                            pass
                    if 'ti' in attrs:
                        try:
                            kf.ti = json.loads(attrs['ti'])
                        except:
                            pass
                        
                    keyframes.append(kf)
                idx += 1
            if keyframes:
                rect.position = Value(keyframes[0].value)
                rect.position.keyframes = keyframes
                rect.position.animated = True
            if idx < len(lines) and lines[idx].startswith('(/position)'):
                idx += 1
                
        # Handle static position
        elif line.startswith('(position') and 'animated=true' not in line:
            components = extract_numbers(line)
            if components:
                rect.position = Value(NVector(*components))
            idx += 1
            
        # Handle animated size
        elif line.startswith('(size') and 'animated=true' in line:
            idx += 1
            keyframes = []
            while idx < len(lines) and not lines[idx].startswith('(/size)'):
                if lines[idx].startswith('(keyframe'):
                    attrs = parse_tag_attrs(lines[idx])
                    time = float(attrs.get('t', 0))
                    s_str = attrs.get('s', '')
                    if s_str:
                        values = [float(x) for x in s_str.split()]
                        value = NVector(*values) if values else NVector(100, 100)
                    else:
                        value = NVector(100, 100)
                    kf = Keyframe(time, value)

                    # Handle easing parameters -
                    if 'i_x' in attrs and 'i_y' in attrs:
                        i_x = attrs['i_x']
                        i_y = attrs['i_y']
                        #
                        if ' ' in i_x:
                            i_x_vals = [float(v) for v in i_x.split()]
                            i_y_vals = [float(v) for v in i_y.split()]
                        else:
                            i_x_vals = [float(i_x)]
                            i_y_vals = [float(i_y)]
                        kf.in_tan = {
                            'x': i_x_vals,
                            'y': i_y_vals
                        }

                    if 'o_x' in attrs and 'o_y' in attrs:
                        o_x = attrs['o_x']
                        o_y = attrs['o_y']
                        #
                        if ' ' in o_x:
                            o_x_vals = [float(v) for v in o_x.split()]
                            o_y_vals = [float(v) for v in o_y.split()]
                        else:
                            o_x_vals = [float(o_x)]
                            o_y_vals = [float(o_y)]
                        kf.out_tan = {
                            'x': o_x_vals,
                            'y': o_y_vals
                        }
                        
                    keyframes.append(kf)
                idx += 1
            if keyframes:
                rect.size = Value(keyframes[0].value)
                rect.size.keyframes = keyframes
                rect.size.animated = True
            if idx < len(lines) and lines[idx].startswith('(/size)'):
                idx += 1
                
        # Handle static size
        elif line.startswith('(rect_size') and 'animated=true' not in line:
            components = extract_numbers(line)
            if components:
                rect.size = Value(NVector(*components))
            idx += 1
            
        # Handle animated rounded
        elif line.startswith('(rounded') and 'animated=true' in line:
            idx += 1
            keyframes = []
            while idx < len(lines) and not lines[idx].startswith('(/rounded)'):
                if lines[idx].startswith('(keyframe'):
                    attrs = parse_tag_attrs(lines[idx])
                    time = float(attrs.get('t', 0))
                    s_str = attrs.get('s', '')
                    if s_str:
                        values = [float(x) for x in s_str.split()]
                        value = values[0] if values else 0
                    else:
                        value = 0
                    kf = Keyframe(time, value)

                    # Handle easing parameters -
                    if 'i_x' in attrs and 'i_y' in attrs:
                        i_x = attrs['i_x']
                        i_y = attrs['i_y']
                        #
                        if ' ' in i_x:
                            i_x_vals = [float(v) for v in i_x.split()]
                            i_y_vals = [float(v) for v in i_y.split()]
                        else:
                            i_x_vals = [float(i_x)]
                            i_y_vals = [float(i_y)]
                        kf.in_tan = {
                            'x': i_x_vals,
                            'y': i_y_vals
                        }

                    if 'o_x' in attrs and 'o_y' in attrs:
                        o_x = attrs['o_x']
                        o_y = attrs['o_y']
                        #
                        if ' ' in o_x:
                            o_x_vals = [float(v) for v in o_x.split()]
                            o_y_vals = [float(v) for v in o_y.split()]
                        else:
                            o_x_vals = [float(o_x)]
                            o_y_vals = [float(o_y)]
                        kf.out_tan = {
                            'x': o_x_vals,
                            'y': o_y_vals
                        }
                        
                    keyframes.append(kf)
                idx += 1
            if keyframes:
                rect.rounded = Value(keyframes[0].value)
                rect.rounded.keyframes = keyframes
                rect.rounded.animated = True
            if idx < len(lines) and lines[idx].startswith('(/rounded)'):
                idx += 1
                
        # Handle static rounded - FIX: Parse numeric values correctly
        elif line.startswith('(rounded') and 'animated=true' not in line:
            components = extract_numbers(line)
            if components:
                # For rounded, we typically want just a single value
                rect.rounded = Value(components[0] if components else 0)
            idx += 1

        elif line.strip() == '(/rect)':
            idx += 1
            break
        else:
            idx += 1
    
    return rect, idx
    

def parse_fill_tag(lines, idx):
    """ - """
    fill_attrs = parse_tag_attrs(lines[idx])
    
    fill = Fill()
    fill.name = fill_attrs.get("name", "")
    
    # property_index
    if "ix" in fill_attrs:
        fill.property_index = int(fill_attrs.get("ix", 1))
    
    # bm
    if "bm" in fill_attrs:
        fill.bm = int(fill_attrs.get("bm", 0))
    else:
        fill.bm = 0
    
    # Check for animated color
    if fill_attrs.get("color_animated") == "true":
        # Parse animated color keyframes
        kf_count = int(fill_attrs.get("c_kf_count", 0))
        fill.color = ColorValue(Color(0, 0, 0))
        
        # FIX: Ensure keyframes is a list, not None
        if not hasattr(fill.color, 'keyframes'):
            fill.color.keyframes = []
        elif fill.color.keyframes is None:
            fill.color.keyframes = []
        
        for i in range(kf_count):
            time = float(fill_attrs.get(f"c_kf_{i}_t", 0))
            r = float(fill_attrs.get(f"c_kf_{i}_r", 0))
            g = float(fill_attrs.get(f"c_kf_{i}_g", 0))
            b = float(fill_attrs.get(f"c_kf_{i}_b", 0))
            
            color = Color(r, g, b)
            kf = Keyframe(time, color)
            
            # Parse tangents if present
            if f"c_kf_{i}_i_x" in fill_attrs:
                kf.in_tan = {
                    'x': [float(fill_attrs.get(f"c_kf_{i}_i_x", 0.667))],
                    'y': [float(fill_attrs.get(f"c_kf_{i}_i_y", 1))]
                }
            
            if f"c_kf_{i}_o_x" in fill_attrs:
                kf.out_tan = {
                    'x': [float(fill_attrs.get(f"c_kf_{i}_o_x", 0.333))],
                    'y': [float(fill_attrs.get(f"c_kf_{i}_o_y", 0))]
                }
            
            fill.color.keyframes.append(kf)
    else:
        # Static color
        try:
            r = float(fill_attrs.get("r", 0))
        except ValueError:
            r = 0
        try:
            g = float(fill_attrs.get("g", 0))
        except ValueError:
            g = 0
        try:
            b = float(fill_attrs.get("b", 0))
        except ValueError:
            b = 0
        
        fill.color = ColorValue(Color(r, g, b))
    
    #
    fill.color_dimensions = int(fill_attrs.get("color_dim", 3))
    
    # aix
    if "has_c_a" in fill_attrs:
        fill.has_c_a = fill_attrs["has_c_a"] == "True"
    if "has_c_ix" in fill_attrs:
        fill.has_c_ix = fill_attrs["has_c_ix"] == "True"
    if "c_ix" in fill_attrs:
        fill.c_ix = int(fill_attrs["c_ix"])
    
    # Parse fill_rule if present -
    if "fill_rule" in fill_attrs:
        try:
            fill_rule_value = int(fill_attrs.get("fill_rule", 1))
            # FillRule: 1(NonZero), 2(EvenOdd)
            if fill_rule_value in [1, 2]:
                fill.fill_rule = FillRule(fill_rule_value)
            else:
                # NonZero(1)
                fill.fill_rule = FillRule(1)
        except (ValueError, KeyError):
            fill.fill_rule = FillRule(1)
    
    # Handle opacity - Fixed: properly parse animated opacity keyframes
    if fill_attrs.get("opacity_animated") == "true":
        # Parse animated opacity keyframes
        kf_count = int(fill_attrs.get("o_kf_count", 0))
        opacity_value = Value(100)
        opacity_value.animated = True
        
        # FIX: Ensure keyframes is a list, not None
        if not hasattr(opacity_value, 'keyframes'):
            opacity_value.keyframes = []
        elif opacity_value.keyframes is None:
            opacity_value.keyframes = []
        
        for i in range(kf_count):
            time = float(fill_attrs.get(f"o_kf_{i}_t", 0))
            value = float(fill_attrs.get(f"o_kf_{i}_s", 100))
            
            kf = Keyframe(time, value)
            
            # Parse tangents if present
            if f"o_kf_{i}_i_x" in fill_attrs:
                kf.in_tan = {
                    'x': float(fill_attrs.get(f"o_kf_{i}_i_x", 0.667)),
                    'y': float(fill_attrs.get(f"o_kf_{i}_i_y", 1))
                }
            
            if f"o_kf_{i}_o_x" in fill_attrs:
                kf.out_tan = {
                    'x': float(fill_attrs.get(f"o_kf_{i}_o_x", 0.333)),
                    'y': float(fill_attrs.get(f"o_kf_{i}_o_y", 0))
                }
            
            opacity_value.keyframes.append(kf)
        
        fill.opacity = opacity_value
    else:
        # Static opacity
        try:
            fill.opacity = Value(float(fill_attrs.get("opacity", 100)))
        except:
            fill.opacity = Value(100)
    
    # aix
    if "has_o_a" in fill_attrs:
        fill.has_o_a = fill_attrs["has_o_a"] == "True"
    if "has_o_ix" in fill_attrs:
        fill.has_o_ix = fill_attrs["has_o_ix"] == "True"
    if "o_ix" in fill_attrs:
        fill.o_ix = int(fill_attrs["o_ix"])
    
    return fill, idx + 1

def parse_effects_tag(lines, start_idx):
    """"""
    effects_list = []
    idx = start_idx
    
    while idx < len(lines):
        line = lines[idx].strip()
        
        if line.startswith('(effect '):
            #
            effect_dict, new_idx = parse_effect_tag(lines, idx)
            effects_list.append(effect_dict)
            idx = new_idx
        elif line.startswith('(/'):
            #
            break
        else:
            idx += 1
    
    return effects_list, idx


def parse_effect_tag(lines, idx):
    """"""
    import json
    
    effect_attrs = parse_tag_attrs(lines[idx])
    
    #
    effect_dict = {
        'nm': effect_attrs.get("name", ""),
        'ty': int(effect_attrs.get("type", 5)),
        'ix': int(effect_attrs.get("index", 1)),
        'mn': effect_attrs.get("match_name", ""),
        'en': int(effect_attrs.get("enabled", 1)),
        'ef': []
    }
    
    #  np
    if "np" in effect_attrs:
        effect_dict['np'] = int(effect_attrs.get("np", 0))
    
    idx += 1
    
    def parse_keyframes(lines, start_idx, end_tag):
        """"""
        keyframes = []
        idx = start_idx
        
        while idx < len(lines):
            line = lines[idx].strip()
            
            if line.startswith('(keyframe'):
                kf_attrs = parse_tag_attrs(line)
                kf = {
                    't': float(kf_attrs.get('t', 0))
                }
                
                #
                if 's' in kf_attrs:
                    # slider, angle, checkbox, dropdown
                    kf['s'] = [float(kf_attrs['s'])]
                elif 'x' in kf_attrs and 'y' in kf_attrs:
                    # Point
                    kf['s'] = [float(kf_attrs['x']), float(kf_attrs['y'])]
                elif 'r' in kf_attrs and 'g' in kf_attrs and 'b' in kf_attrs:
                    # Color
                    color_val = [
                        float(kf_attrs['r']),
                        float(kf_attrs['g']),
                        float(kf_attrs['b'])
                    ]
                    if 'a' in kf_attrs:
                        color_val.append(float(kf_attrs['a']))
                    else:
                        color_val.append(1)
                    kf['s'] = color_val
                
                #
                if 'i_x' in kf_attrs and 'i_y' in kf_attrs:
                    kf['i'] = {
                        'x': [float(kf_attrs['i_x'])],
                        'y': [float(kf_attrs['i_y'])]
                    }
                
                #
                if 'o_x' in kf_attrs and 'o_y' in kf_attrs:
                    kf['o'] = {
                        'x': [float(kf_attrs['o_x'])],
                        'y': [float(kf_attrs['o_y'])]
                    }
                
                # hold
                if 'h' in kf_attrs:
                    kf['h'] = int(kf_attrs['h'])
                
                keyframes.append(kf)
                idx += 1
                
            elif line.startswith(end_tag):
                break
            else:
                idx += 1
        
        return keyframes, idx
    
    while idx < len(lines):
        line = lines[idx].strip()
        
        if line.startswith('(slider'):
            slider_attrs = parse_tag_attrs(line)
            
            #
            if slider_attrs.get('animated') == 'true':
                #
                idx += 1
                print("lines", lines)
                keyframes, idx = parse_keyframes(lines, idx, '(/slider)')
                
                sub_effect = {
                    'ty': 0,
                    'nm': slider_attrs.get("name", ""),
                    'mn': slider_attrs.get("match_name", ""),
                    'ix': int(slider_attrs.get("index", 0)),
                    'v': {
                        'a': 1,
                        'k': keyframes,
                        'ix': int(slider_attrs.get("index", 0))
                    }
                }
            else:
                #
                try:
                    slider_value = float(slider_attrs.get("value", 0))
                except (ValueError, TypeError):
                    slider_value = 0
                
                sub_effect = {
                    'ty': 0,
                    'nm': slider_attrs.get("name", ""),
                    'mn': slider_attrs.get("match_name", ""),
                    'ix': int(slider_attrs.get("index", 0)),
                    'v': {
                        'a': 0,
                        'k': slider_value,
                        'ix': int(slider_attrs.get("index", 0))
                    }
                }
            
            effect_dict['ef'].append(sub_effect)
            idx += 1
                 
        elif line.startswith('(color'):
            color_attrs = parse_tag_attrs(line)
            
            if color_attrs.get('animated') == 'true':
                idx += 1
                keyframes, idx = parse_keyframes(lines, idx, '(/color)')
                
                sub_effect = {
                    'ty': 2,
                    'nm': color_attrs.get("name", ""),
                    'mn': color_attrs.get("match_name", ""),
                    'ix': int(color_attrs.get("index", 0)),
                    'v': {
                        'a': 1,
                        'k': keyframes,
                        'ix': int(color_attrs.get("index", 0))
                    }
                }
            else:
                sub_effect = {
                    'ty': 2,
                    'nm': color_attrs.get("name", ""),
                    'mn': color_attrs.get("match_name", ""),
                    'ix': int(color_attrs.get("index", 0)),
                    'v': {
                        'a': 0,
                        'k': [
                            float(color_attrs.get("r", 0)),
                            float(color_attrs.get("g", 0)),
                            float(color_attrs.get("b", 0)),
                            1
                        ],
                        'ix': int(color_attrs.get("index", 0))
                    }
                }
            
            effect_dict['ef'].append(sub_effect)
            idx += 1
            
        elif line.startswith('(angle'):
            angle_attrs = parse_tag_attrs(line)
            
            if angle_attrs.get('animated') == 'true':
                idx += 1
                keyframes, idx = parse_keyframes(lines, idx, '(/angle)')
                
                sub_effect = {
                    'ty': 1,
                    'nm': angle_attrs.get("name", ""),
                    'mn': angle_attrs.get("match_name", ""),
                    'ix': int(angle_attrs.get("index", 0)),
                    'v': {
                        'a': 1,
                        'k': keyframes,
                        'ix': int(angle_attrs.get("index", 0))
                    }
                }
            else:
                sub_effect = {
                    'ty': 1,
                    'nm': angle_attrs.get("name", ""),
                    'mn': angle_attrs.get("match_name", ""),
                    'ix': int(angle_attrs.get("index", 0)),
                    'v': {
                        'a': 0,
                        'k': float(angle_attrs.get("value", 0)),
                        'ix': int(angle_attrs.get("index", 0))
                    }
                }
            
            effect_dict['ef'].append(sub_effect)
            idx += 1
            
        elif line.startswith('(point'):
            point_attrs = parse_tag_attrs(line)
            
            if point_attrs.get('animated') == 'true':
                idx += 1
                keyframes, idx = parse_keyframes(lines, idx, '(/point)')
                
                sub_effect = {
                    'ty': 3,
                    'nm': point_attrs.get("name", ""),
                    'mn': point_attrs.get("match_name", ""),
                    'ix': int(point_attrs.get("index", 0)),
                    'v': {
                        'a': 1,
                        'k': keyframes,
                        'ix': int(point_attrs.get("index", 0))
                    }
                }
            else:
                sub_effect = {
                    'ty': 3,
                    'nm': point_attrs.get("name", ""),
                    'mn': point_attrs.get("match_name", ""),
                    'ix': int(point_attrs.get("index", 0)),
                    'v': {
                        'a': 0,
                        'k': [
                            float(point_attrs.get("x", 0)),
                            float(point_attrs.get("y", 0))
                        ],
                        'ix': int(point_attrs.get("index", 0))
                    }
                }
            
            effect_dict['ef'].append(sub_effect)
            idx += 1
            
        elif line.startswith('(checkbox'):
            checkbox_attrs = parse_tag_attrs(line)
            
            if checkbox_attrs.get('animated') == 'true':
                idx += 1
                keyframes, idx = parse_keyframes(lines, idx, '(/checkbox)')
                
                #
                for kf in keyframes:
                    if 's' in kf and isinstance(kf['s'], list):
                        kf['s'] = [int(kf['s'][0])]
                
                sub_effect = {
                    'ty': 4,
                    'nm': checkbox_attrs.get("name", ""),
                    'mn': checkbox_attrs.get("match_name", ""),
                    'ix': int(checkbox_attrs.get("index", 0)),
                    'v': {
                        'a': 1,
                        'k': keyframes,
                        'ix': int(checkbox_attrs.get("index", 0))
                    }
                }
            else:
                sub_effect = {
                    'ty': 4,
                    'nm': checkbox_attrs.get("name", ""),
                    'mn': checkbox_attrs.get("match_name", ""),
                    'ix': int(checkbox_attrs.get("index", 0)),
                    'v': {
                        'a': 0,
                        'k': int(checkbox_attrs.get("value", 0)),
                        'ix': int(checkbox_attrs.get("index", 0))
                    }
                }
            
            effect_dict['ef'].append(sub_effect)
            idx += 1
            
        elif line.startswith('(dropdown'):
            dropdown_attrs = parse_tag_attrs(line)
            
            if dropdown_attrs.get('animated') == 'true':
                idx += 1
                keyframes, idx = parse_keyframes(lines, idx, '(/dropdown)')
                
                #
                for kf in keyframes:
                    if 's' in kf and isinstance(kf['s'], list):
                        kf['s'] = [int(kf['s'][0])]
                
                sub_effect = {
                    'ty': 7,
                    'nm': dropdown_attrs.get("name", ""),
                    'mn': dropdown_attrs.get("match_name", ""),
                    'ix': int(dropdown_attrs.get("index", 0)),
                    'v': {
                        'a': 1,
                        'k': keyframes,
                        'ix': int(dropdown_attrs.get("index", 0))
                    }
                }
            else:
                sub_effect = {
                    'ty': 7,
                    'nm': dropdown_attrs.get("name", ""),
                    'mn': dropdown_attrs.get("match_name", ""),
                    'ix': int(dropdown_attrs.get("index", 0)),
                    'v': {
                        'a': 0,
                        'k': int(dropdown_attrs.get("value", 1)),
                        'ix': int(dropdown_attrs.get("index", 0))
                    }
                }
            
            effect_dict['ef'].append(sub_effect)
            idx += 1
            
        elif line.startswith('(layer_effect'):
            layer_attrs = parse_tag_attrs(line)
            
            if layer_attrs.get('animated') == 'true':
                idx += 1
                keyframes, idx = parse_keyframes(lines, idx, '(/layer_effect)')
                
                #
                for kf in keyframes:
                    if 's' in kf and isinstance(kf['s'], list):
                        kf['s'] = [int(kf['s'][0])]
                
                sub_effect = {
                    'ty': 10,
                    'nm': layer_attrs.get("name", ""),
                    'mn': layer_attrs.get("match_name", ""),
                    'ix': int(layer_attrs.get("index", 0)),
                    'v': {
                        'a': 1,
                        'k': keyframes,
                        'ix': int(layer_attrs.get("index", 0))
                    }
                }
            else:
                try:
                    layer_value = int(layer_attrs.get("value", 0))
                except (ValueError, TypeError):
                    layer_value = 0
                    
                sub_effect = {
                    'ty': 10,
                    'nm': layer_attrs.get("name", ""),
                    'mn': layer_attrs.get("match_name", ""),
                    'ix': int(layer_attrs.get("index", 0)),
                    'v': {
                        'a': 0,
                        'k': layer_value,
                        'ix': int(layer_attrs.get("index", 0))
                    }
                }
            
            effect_dict['ef'].append(sub_effect)
            idx += 1
            
        elif line.startswith('(ignored'):
            ignored_attrs = parse_tag_attrs(line)
            
            if ignored_attrs.get('animated') == 'true':
                idx += 1
                keyframes, idx = parse_keyframes(lines, idx, '(/ignored)')
                
                sub_effect = {
                    'ty': 0,  # slider
                    'nm': ignored_attrs.get("name", ""),
                    'mn': ignored_attrs.get("match_name", ""),
                    'ix': int(ignored_attrs.get("index", 0)),
                    'v': {
                        'a': 1,
                        'k': keyframes,
                        'ix': int(ignored_attrs.get("index", 0))
                    }
                }
            else:
                try:
                    ignored_value = float(ignored_attrs.get("value", 0))
                except (ValueError, TypeError):
                    ignored_value = 0
                    
                sub_effect = {
                    'ty': 0,  # slider
                    'nm': ignored_attrs.get("name", ""),
                    'mn': ignored_attrs.get("match_name", ""),
                    'ix': int(ignored_attrs.get("index", 0)),
                    'v': {
                        'a': 0,
                        'k': ignored_value,
                        'ix': int(ignored_attrs.get("index", 0))
                    }
                }
            
            effect_dict['ef'].append(sub_effect)
            idx += 1
            
        elif line.startswith('(no_value'):
            no_value_attrs = parse_tag_attrs(line)
            sub_effect = {
                'ty': 6,
                'nm': no_value_attrs.get("name", ""),
                'mn': no_value_attrs.get("match_name", ""),
                'ix': int(no_value_attrs.get("index", 0)),
                'v': 0
            }
            effect_dict['ef'].append(sub_effect)
            idx += 1
            
        elif line == '(/effect)':
            idx += 1
            break
        else:
            idx += 1
    
    return effect_dict, idx


def parse_gradient_fill_tag(lines, idx):
    """ - """
    attrs = parse_tag_attrs(lines[idx])
    
    gradient_fill = GradientFill()
    gradient_fill.name = attrs.get("name", "")
    
    if "ix" in attrs:
        gradient_fill.property_index = int(attrs.get("ix", 1))
    
    idx += 1
    colors_data = []
    original_array = None
    color_points = 0
    
    while idx < len(lines):
        line = lines[idx]
        
        if line.startswith('(opacity'):
            value = extract_number(line)
            gradient_fill.opacity = Value(value)
            idx += 1
        elif line.startswith('(fill_rule'):
            value = int(extract_number(line))
            gradient_fill.fill_rule = FillRule(value)
            idx += 1
        elif line.startswith('(start_point'):
            components = extract_numbers(line)
            if components:
                gradient_fill.start_point = MultiDimensional(NVector(*components))
            idx += 1
        elif line.startswith('(end_point'):
            components = extract_numbers(line)
            if components:
                gradient_fill.end_point = MultiDimensional(NVector(*components))
            idx += 1
        elif line.startswith('(gradient_type'):
            value = int(extract_number(line))
            gradient_fill.gradient_type = GradientType(value)
            idx += 1
        elif line.startswith('(highlight_length'):
            value = extract_number(line)
            gradient_fill.highlight_length = Value(value)
            idx += 1
        elif line.startswith('(highlight_angle'):
            value = extract_number(line)
            gradient_fill.highlight_angle = Value(value)
            idx += 1
        elif line.startswith('(original_colors'):
            #
            text = line[line.find(' ') + 1:].strip().rstrip(')')
            if text:
                try:
                    original_array = json.loads(text)
                except:
                    pass
            idx += 1
        elif line.startswith('(color_points'):
            color_points = int(extract_number(line))
            idx += 1
        elif line.startswith('(colors'):
            #
            text = line[line.find(' ') + 1:].strip().rstrip(')')
            if text:
                for color_data in text.split():
                    parts = color_data.split(',')
                    if len(parts) >= 4:
                        pos = float(parts[0])
                        r = float(parts[1])
                        g = float(parts[2])
                        b = float(parts[3])
                        colors_data.append((pos, Color(r, g, b)))
            idx += 1
        elif line.strip() == '(/gradient_fill)':
            idx += 1
            break
        else:
            idx += 1
    
    #
    if original_array:
        #
        gradient_fill._original_color_array = original_array
        gradient_fill._color_points = color_points
        
        #
        if color_points > 0:
            values_per_point = len(original_array) / color_points
            colors = []
            
            if values_per_point >= 4:
                step = int(values_per_point)
                for i in range(color_points):
                    base = i * step
                    pos = original_array[base]
                    r = original_array[base + 1]
                    g = original_array[base + 2]
                    b = original_array[base + 3]
                    colors.append((pos, Color(r, g, b)))
                gradient_fill.colors = GradientColors(colors)
    elif colors_data:
        gradient_fill.colors = GradientColors(colors_data)
    else:
        #
        gradient_fill.colors = GradientColors([
            (0.0, Color(0.85, 0.36, 0.33)),
            (0.15, Color(0.84, 1.0, 0.0))
        ])
    
    return gradient_fill, idx


def parse_transform_shape_tag(lines, idx):
    """TransformShape - """
    transform_attrs = parse_tag_attrs(lines[idx])
    
    transform = TransformShape()
    transform.name = transform_attrs.get("name", "")
    
    # property_index
    if "ix" in transform_attrs:
        transform.property_index = int(transform_attrs.get("ix"))
        
    if "hd" in transform_attrs:
        transform.hd = transform_attrs.get("hd", "false").lower() == "true"
    
    #
    if "position" in transform_attrs:
        values = [float(x) for x in transform_attrs["position"].split()]
        transform.position = MultiDimensional(NVector(*values))
    
    if "scale" in transform_attrs:
        values = [float(x) for x in transform_attrs["scale"].split()]
        if len(values) == 2:
            transform.scale = MultiDimensional(NVector(values[0], values[1]))
        elif len(values) == 3:
            transform.scale = MultiDimensional(NVector(values[0], values[1], values[2]))
        else:
            transform.scale = MultiDimensional(NVector(values[0], values[0]))
    
    if "rotation" in transform_attrs:
        transform.rotation = Value(float(transform_attrs["rotation"]))
    
    if "opacity" in transform_attrs:
        transform.opacity = Value(float(transform_attrs["opacity"]))
    
    if "anchor" in transform_attrs:
        values = [float(x) for x in transform_attrs["anchor"].split()]
        transform.anchor = MultiDimensional(NVector(*values))
    
    if "skew" in transform_attrs:
        transform.skew = Value(float(transform_attrs["skew"]))
    
    if "skew_axis" in transform_attrs:
        transform.skew_axis = Value(float(transform_attrs["skew_axis"]))
    
    #
    idx += 1
    while idx < len(lines):
        line = lines[idx]
        
        if line.startswith('(position') and 'animated=true' in line:
            # position
            idx += 1
            keyframes = []
            while idx < len(lines) and not lines[idx].startswith('(/position)'):
                if lines[idx].startswith('(keyframe'):
                    attrs = parse_tag_attrs(lines[idx])
                    time = float(attrs.get('t', 0))
                    s_str = attrs.get('s', '')
                    if s_str:
                        values = [float(x) for x in s_str.split()]
                        value = NVector(*values) if values else NVector(0, 0, 0)
                    else:
                        value = NVector(0, 0, 0)
                    kf = Keyframe(time, value)
                    
                    #  -  float
                    if 'i_x' in attrs and 'i_y' in attrs:
                        kf.in_tan = {
                            'x': float(attrs['i_x']), 
                            'y': float(attrs['i_y'])
                        }
                    
                    if 'o_x' in attrs and 'o_y' in attrs:
                        kf.out_tan = {
                            'x': float(attrs['o_x']), 
                            'y': float(attrs['o_y'])
                        }
                    
                    if 'to' in attrs:
                        try:
                            kf.to = json.loads(attrs['to'])
                        except:
                            pass
                    if 'ti' in attrs:
                        try:
                            kf.ti = json.loads(attrs['ti'])
                        except:
                            pass
                        
                    keyframes.append(kf)
                idx += 1
            if keyframes:
                transform.position = MultiDimensional(keyframes[0].value)
                transform.position.keyframes = keyframes
            if idx < len(lines) and lines[idx].startswith('(/position)'):
                idx += 1

      
        elif line.startswith('(scale'):
            if 'separated=true' in line:
                # Handle separated scale
                transform.scale = Value(NVector(100, 100))
                transform.scale.separated = True
                idx += 1
                while idx < len(lines) and not lines[idx].startswith('(/scale)'):
                    if lines[idx].startswith('(scale_x'):
                        value = extract_number(lines[idx])
                        transform.scale.x = Value(value)
                    elif lines[idx].startswith('(scale_y'):
                        value = extract_number(lines[idx])
                        transform.scale.y = Value(value)
                    elif lines[idx].startswith('(scale_z'):
                        value = extract_number(lines[idx])
                        transform.scale.z = Value(value)
                    idx += 1
                if idx < len(lines) and lines[idx].startswith('(/scale)'):
                    idx += 1
            elif 'animated=true' in line:
                # scale
                idx += 1
                keyframes = []
                while idx < len(lines) and not lines[idx].startswith('(/scale)'):
                    if lines[idx].startswith('(keyframe'):
                        attrs = parse_tag_attrs(lines[idx])
                        time = float(attrs.get('t', 0))
                        s_str = attrs.get('s', '')
                        if s_str:
                            values = [float(x) for x in s_str.split()]
                            if len(values) == 2:
                                value = NVector(values[0], values[1])
                            elif len(values) == 3:
                                value = NVector(values[0], values[1], values[2])
                            else:
                                value = NVector(100, 100)
                        else:
                            value = NVector(100, 100)
                        
                        kf = Keyframe(time, value)
                        
                        #  -
                        if 'i_x' in attrs and 'i_y' in attrs:
                            i_x_str = attrs['i_x']
                            i_y_str = attrs['i_y']
                            
                            if ' ' in i_x_str:
                                i_x = [float(v) for v in i_x_str.split()]
                                i_y = [float(v) for v in i_y_str.split()]
                            else:
                                i_x = float(i_x_str)
                                i_y = float(i_y_str)
                            
                            kf.in_tan = {'x': i_x, 'y': i_y}

                        if 'o_x' in attrs and 'o_y' in attrs:
                            o_x_str = attrs['o_x']
                            o_y_str = attrs['o_y']
                            
                            if ' ' in o_x_str:
                                o_x = [float(v) for v in o_x_str.split()]
                                o_y = [float(v) for v in o_y_str.split()]
                            else:
                                o_x = float(o_x_str)
                                o_y = float(o_y_str)
                            
                            kf.out_tan = {'x': o_x, 'y': o_y}
                        
                        keyframes.append(kf)
                    idx += 1
                
                if keyframes:
                    transform.scale = MultiDimensional(keyframes[0].value)
                    transform.scale.keyframes = keyframes
                else:
                    if not hasattr(transform, 'scale'):
                        transform.scale = MultiDimensional(NVector(100, 100))
                    
                if idx < len(lines) and lines[idx].startswith('(/scale)'):
                    idx += 1
            else:
                idx += 1
                 
        elif line.startswith('(rotation'):
            if 'separated=true' in line:
                transform.rotation = Value(0)
                transform.rotation.separated = True
                idx += 1
                while idx < len(lines) and not lines[idx].startswith('(/rotation)'):
                    if lines[idx].startswith('(rotation_x'):
                        value = extract_number(lines[idx])
                        transform.rotation.x = Value(value)
                    elif lines[idx].startswith('(rotation_y'):
                        value = extract_number(lines[idx])
                        transform.rotation.y = Value(value)
                    elif lines[idx].startswith('(rotation_z'):
                        value = extract_number(lines[idx])
                        transform.rotation.z = Value(value)
                    idx += 1
                if idx < len(lines) and lines[idx].startswith('(/rotation)'):
                    idx += 1
            elif 'animated=true' in line:
                # rotation
                idx += 1
                keyframes = []
                while idx < len(lines) and not lines[idx].startswith('(/rotation)'):
                    if lines[idx].startswith('(keyframe'):
                        attrs = parse_tag_attrs(lines[idx])
                        time = float(attrs.get('t', 0))
                        value = float(attrs.get('s', 0))
                        kf = Keyframe(time, value)
                        
                        #
                        if 'i_x' in attrs and 'i_y' in attrs:
                            i_x = float(attrs['i_x'])
                            i_y = float(attrs['i_y'])
                            kf.in_tan = {'x': i_x, 'y': i_y}
                        
                        if 'o_x' in attrs and 'o_y' in attrs:
                            o_x = float(attrs['o_x'])
                            o_y = float(attrs['o_y'])
                            kf.out_tan = {'x': o_x, 'y': o_y}
                            
                        keyframes.append(kf)
                    idx += 1
                if keyframes:
                    transform.rotation = Value(keyframes[0].value)
                    transform.rotation.keyframes = keyframes
                if idx < len(lines) and lines[idx].startswith('(/rotation)'):
                    idx += 1
            else:
                idx += 1
                
        elif line.startswith('(opacity') and 'animated=true' in line:
            # opacity
            idx += 1
            keyframes = []
            while idx < len(lines) and not lines[idx].startswith('(/opacity)'):
                if lines[idx].startswith('(keyframe'):
                    attrs = parse_tag_attrs(lines[idx])
                    time = float(attrs.get('t', 0))
                    value = float(attrs.get('s', 100))
                    kf = Keyframe(time, value)
                    
                    #
                    if 'i_x' in attrs and 'i_y' in attrs:
                        i_x = float(attrs['i_x'])
                        i_y = float(attrs['i_y'])
                        kf.in_tan = {'x': i_x, 'y': i_y}
                    
                    if 'o_x' in attrs and 'o_y' in attrs:
                        o_x = float(attrs['o_x'])
                        o_y = float(attrs['o_y'])
                        kf.out_tan = {'x': o_x, 'y': o_y}
                    
                    # h
                    if 'h' in attrs:
                        kf.h = int(attrs['h'])
                        
                    keyframes.append(kf)
                idx += 1
            if keyframes:
                transform.opacity = Value(keyframes[0].value)
                transform.opacity.keyframes = keyframes
            if idx < len(lines) and lines[idx].startswith('(/opacity)'):
                idx += 1
   
        elif line.startswith('(/'):  # Any closing tag
            break
        else:
            idx += 1
    
    return transform, idx
    


def parse_path_tag(lines, idx):
    """ - h"""
    path_attrs = parse_tag_attrs(lines[idx])
    
    path = Path()
    path.name = path_attrs.get("name", "")
    
    # property_index
    if "ix" in path_attrs:
        path.property_index = int(path_attrs.get("ix", 1))
    if "d" in path_attrs:
        path.d = int(path_attrs.get("d", 1))
    
    if "ind" in path_attrs:
        path.ind = int(path_attrs.get("ind", 1))
    else:
        path.ind = 1  # Default value
    
    if "hd" in path_attrs:
        path.hd = path_attrs.get("hd", "false").lower() == "true"
    
    if "mn" in path_attrs:
        path.mn = path_attrs.get("mn", "")
    
    # Check if animated
    is_animated = path_attrs.get("animated", "").lower() == "true"
    
    if is_animated:
        # Handle animated path
        keyframes = []
        idx += 1
        
        while idx < len(lines) and not lines[idx].startswith('(/path)'):
            if lines[idx].startswith('(keyframe'):
                kf_attrs = parse_tag_attrs(lines[idx])
                time = float(kf_attrs.get("t", 0))
                
                kf = Keyframe(time, None)
                
                if "i_x" in kf_attrs and "i_y" in kf_attrs:
                    kf.in_tan = {
                        "x": float(kf_attrs["i_x"]),
                        "y": float(kf_attrs["i_y"])
                    }
                
                if "o_x" in kf_attrs and "o_y" in kf_attrs:
                    kf.out_tan = {
                        "x": float(kf_attrs["o_x"]),
                        "y": float(kf_attrs["o_y"])
                    }
                
                # h
                if "h" in kf_attrs:
                    kf.h = int(kf_attrs["h"])
                
                idx += 1
                
                if lines[idx].startswith('(bezier'):
                    bezier_attrs = parse_tag_attrs(lines[idx])
                    
                    bezier = Bezier()
                    bezier.closed = bezier_attrs.get("closed", "").lower() == "true"
                    
                    idx += 1
                    
                    while idx < len(lines) and not lines[idx].startswith('(/bezier)'):
                        if lines[idx].startswith('(point'):
                            point_attrs = parse_tag_attrs(lines[idx])

                            x = float(point_attrs.get("x", 0))
                            y = float(point_attrs.get("y", 0))
                            in_x = float(point_attrs.get("in_x", 0))
                            in_y = float(point_attrs.get("in_y", 0))
                            out_x = float(point_attrs.get("out_x", 0))
                            out_y = float(point_attrs.get("out_y", 0))
                            
                            bezier.add_point(
                                NVector(x, y),
                                NVector(in_x, in_y),
                                NVector(out_x, out_y)
                            )
                        
                        idx += 1
                    
                    kf.value = bezier
                    
                    if idx < len(lines) and lines[idx].startswith('(/bezier)'):
                        idx += 1
                
                keyframes.append(kf)
                
                if idx < len(lines) and lines[idx].startswith('(/keyframe)'):
                    idx += 1
            else:
                idx += 1
        
        if keyframes:
            path.shape = Value(keyframes[0].value)
            path.shape.keyframes = keyframes
        
        if idx < len(lines) and lines[idx].startswith('(/path)'):
            idx += 1
    else:
        # Static path
        bezier = Bezier()
        bezier.closed = path_attrs.get("closed", "true").lower() == "true"
        
        idx += 1
        while idx < len(lines):
            if lines[idx].startswith('(point'):
                point_attrs = parse_tag_attrs(lines[idx])

                x = float(point_attrs.get("x", 0))
                y = float(point_attrs.get("y", 0))
                in_x = float(point_attrs.get("in_x", 0))
                in_y = float(point_attrs.get("in_y", 0))
                out_x = float(point_attrs.get("out_x", 0))
                out_y = float(point_attrs.get("out_y", 0))
                
                bezier.add_point(NVector(x, y), NVector(in_x, in_y), NVector(out_x, out_y))
                idx += 1
            elif lines[idx].strip() == '(/path)':
                idx += 1
                break
            else:
                idx += 1
        
        path.shape = Value(bezier)
    
    return path, idx




def parse_ellipse_tag(lines, idx):
    """"""
    ellipse_attrs = parse_tag_attrs(lines[idx])

    ellipse = Ellipse()
    ellipse.name = ellipse_attrs.get("name", "")

    # property_index
    if "ix" in ellipse_attrs:
        ellipse.property_index = int(ellipse_attrs.get("ix", 1))

    idx += 1
    while idx < len(lines):
        line = lines[idx]

        if line.startswith('(ellipse_position animated'):
            # animated position keyframes
            keyframes = []
            idx += 1
            while idx < len(lines):
                if lines[idx].startswith('(/ellipse_position)'):
                    idx += 1
                    break
                elif lines[idx].startswith('(keyframe'):
                    kf_attrs = parse_tag_attrs(lines[idx])
                    kf_dict = {'t': float(kf_attrs.get('t', 0))}
                    if 's' in kf_attrs:
                        s_vals = [float(v) for v in kf_attrs['s'].split()]
                        kf_dict['s'] = s_vals
                    if 'i_x' in kf_attrs and 'i_y' in kf_attrs:
                        i_x = [float(v) for v in kf_attrs['i_x'].split()] if ' ' in kf_attrs['i_x'] else float(kf_attrs['i_x'])
                        i_y = [float(v) for v in kf_attrs['i_y'].split()] if ' ' in kf_attrs['i_y'] else float(kf_attrs['i_y'])
                        kf_dict['i'] = {'x': i_x, 'y': i_y}
                    if 'o_x' in kf_attrs and 'o_y' in kf_attrs:
                        o_x = [float(v) for v in kf_attrs['o_x'].split()] if ' ' in kf_attrs['o_x'] else float(kf_attrs['o_x'])
                        o_y = [float(v) for v in kf_attrs['o_y'].split()] if ' ' in kf_attrs['o_y'] else float(kf_attrs['o_y'])
                        kf_dict['o'] = {'x': o_x, 'y': o_y}
                    if 'h' in kf_attrs:
                        kf_dict['h'] = int(kf_attrs['h'])
                    if 'to' in kf_attrs:
                        kf_dict['to'] = [float(v) for v in kf_attrs['to'].split()]
                    if 'ti' in kf_attrs:
                        kf_dict['ti'] = [float(v) for v in kf_attrs['ti'].split()]
                    keyframes.append(kf_dict)
                    idx += 1
                else:
                    # keyframes
                    break
            ellipse.position = MultiDimensional()
            nvec = NVector()
            nvec.components = keyframes
            ellipse.position.value = nvec
            ellipse.position.animated = True
        elif line.startswith('(ellipse_position'):
            components = extract_numbers(line)
            if components:
                ellipse.position = MultiDimensional(NVector(*components))
            idx += 1
        elif line.startswith('(ellipse_size animated'):
            # animated size keyframes
            keyframes = []
            idx += 1
            while idx < len(lines):
                if lines[idx].startswith('(/ellipse_size)'):
                    idx += 1
                    break
                elif lines[idx].startswith('(keyframe'):
                    kf_attrs = parse_tag_attrs(lines[idx])
                    kf_dict = {'t': float(kf_attrs.get('t', 0))}
                    if 's' in kf_attrs:
                        s_vals = [float(v) for v in kf_attrs['s'].split()]
                        kf_dict['s'] = s_vals
                    if 'i_x' in kf_attrs and 'i_y' in kf_attrs:
                        i_x = [float(v) for v in kf_attrs['i_x'].split()] if ' ' in kf_attrs['i_x'] else float(kf_attrs['i_x'])
                        i_y = [float(v) for v in kf_attrs['i_y'].split()] if ' ' in kf_attrs['i_y'] else float(kf_attrs['i_y'])
                        kf_dict['i'] = {'x': i_x, 'y': i_y}
                    if 'o_x' in kf_attrs and 'o_y' in kf_attrs:
                        o_x = [float(v) for v in kf_attrs['o_x'].split()] if ' ' in kf_attrs['o_x'] else float(kf_attrs['o_x'])
                        o_y = [float(v) for v in kf_attrs['o_y'].split()] if ' ' in kf_attrs['o_y'] else float(kf_attrs['o_y'])
                        kf_dict['o'] = {'x': o_x, 'y': o_y}
                    if 'h' in kf_attrs:
                        kf_dict['h'] = int(kf_attrs['h'])
                    keyframes.append(kf_dict)
                    idx += 1
                else:
                    # keyframes
                    break
            ellipse.size = MultiDimensional()
            nvec = NVector()
            nvec.components = keyframes
            ellipse.size.value = nvec
            ellipse.size.animated = True
        elif line.startswith('(ellipse_size'):
            components = extract_numbers(line)
            if components:
                ellipse.size = MultiDimensional(NVector(*components))
            idx += 1
        elif line.strip() == '(/ellipse)':
            idx += 1
            break
        else:
            idx += 1

    return ellipse, idx


def parse_gradient_stroke_tag(lines, idx):
    """ - ml2"""
    gradient_stroke_attrs = parse_tag_attrs(lines[idx])
    
    gradient_stroke = GradientStroke()
    gradient_stroke.name = gradient_stroke_attrs.get("name", "")
    
    if "ix" in gradient_stroke_attrs:
        gradient_stroke.property_index = int(gradient_stroke_attrs.get("ix", 1))
    
    idx += 1
    original_array = None
    color_points = 0
    
    while idx < len(lines):
        line = lines[idx]
        
        if line.startswith('(opacity'):
            value = extract_number(line)
            gradient_stroke.opacity = Value(value)
            idx += 1
        elif line.startswith('(width'):
            value = extract_number(line)
            gradient_stroke.width = Value(value)
            idx += 1
        elif line.startswith('(line_cap'):
            value = int(extract_number(line))
            gradient_stroke.line_cap = LineCap(value)
            idx += 1
        elif line.startswith('(line_join'):
            value = int(extract_number(line))
            gradient_stroke.line_join = LineJoin(value)
            idx += 1
        elif line.startswith('(miter_limit'):
            value = extract_number(line)
            gradient_stroke.miter_limit = value
            idx += 1
        elif line.startswith('(ml2_ix'):
            gradient_stroke.ml2_ix = int(extract_number(line))
            idx += 1
        elif line.startswith('(ml2'):
            value = extract_number(line)
            gradient_stroke.ml2 = Value(value)
            idx += 1
        elif line.startswith('(start_point'):
            components = extract_numbers(line)
            gradient_stroke.start_point = MultiDimensional(NVector(*components))
            # animated
            idx += 1
        elif line.startswith('(end_point'):
            components = extract_numbers(line)
            gradient_stroke.end_point = MultiDimensional(NVector(*components))
            # animated
            idx += 1
        elif line.startswith('(gradient_type'):
            value = int(extract_number(line))
            gradient_stroke.gradient_type = GradientType(value)
            idx += 1
        elif line.startswith('(highlight_length'):
            value = extract_number(line)
            gradient_stroke.highlight_length = Value(value)
            idx += 1
        elif line.startswith('(highlight_angle'):
            value = extract_number(line)
            gradient_stroke.highlight_angle = Value(value)
            idx += 1
        elif line.startswith('(original_colors'):
            #
            text = line[line.find(' ') + 1:].strip().rstrip(')')
            if text:
                try:
                    original_array = json.loads(text)
                    gradient_stroke._original_color_array = original_array
                except:
                    pass
            idx += 1
        elif line.startswith('(color_points'):
            color_points = int(extract_number(line))
            gradient_stroke._color_points = color_points
            idx += 1
        elif line.startswith('(colors'):
            #
            text = line[line.find(' ') + 1:].strip().rstrip(')')
            colors = []
            
            for color_data in text.split():
                parts = color_data.split(',')
                if len(parts) >= 4:
                    pos = float(parts[0])
                    r = float(parts[1])
                    g = float(parts[2])
                    b = float(parts[3])
                    colors.append((pos, Color(r, g, b)))
            
            gradient_stroke.colors = GradientColors(colors)
            idx += 1
        elif line.strip() == '(/gradient_stroke)':
            idx += 1
            break
        else:
            idx += 1
    
    #
    if original_array and color_points > 0:
        gradient_stroke._original_color_array = original_array
        gradient_stroke._color_points = color_points
        
        #
        colors = []
        values_per_point = len(original_array) / color_points
        if values_per_point >= 4:
            step = int(values_per_point)
            for i in range(color_points):
                base = i * step
                pos = original_array[base]
                r = original_array[base + 1]
                g = original_array[base + 2]
                b = original_array[base + 3]
                colors.append((pos, Color(r, g, b)))
            gradient_stroke.colors = GradientColors(colors)
    
    return gradient_stroke, idx


def parse_precomp_layer_tag(lines, idx):
    """Parse a precomp layer tag and its contents"""
    precomp_attrs = parse_tag_attrs(lines[idx])
    
    precomp_layer = PreCompLayer()
    precomp_layer.index = int(float(precomp_attrs.get("index", 0)))
    precomp_layer.name = precomp_attrs.get("name", "PreComp Layer")
    precomp_layer.in_point = float(precomp_attrs.get("in_point", 0))
    precomp_layer.out_point = float(precomp_attrs.get("out_point", 60))
    precomp_layer.start_time = float(precomp_attrs.get("start_time", 0))
    
    if "w" in precomp_attrs:
        precomp_layer.w = float(precomp_attrs["w"])
    if "h" in precomp_attrs:
        precomp_layer.h = float(precomp_attrs["h"])
    
    if "tt" in precomp_attrs:
        precomp_layer.tt = float(precomp_attrs["tt"])
    if "tp" in precomp_attrs:
        precomp_layer.tp = float(precomp_attrs["tp"])
    if "td" in precomp_attrs:
        precomp_layer.td = float(precomp_attrs["td"])  
    
    if "hasMask" in precomp_attrs:
        precomp_layer.hasMask = precomp_attrs["hasMask"] == "true"
    if "hd" in precomp_attrs:
        precomp_layer.hd = precomp_attrs["hd"] == "true"
    if "cp" in precomp_attrs:
        precomp_layer.cp = precomp_attrs["cp"] == "true"
    
    
    #if "ln" in precomp_attrs:
    #    precomp_layer.ln = float(precomp_attrs["ln"])  
        
    idx += 1
    while idx < len(lines):
        line = lines[idx]
        
        if line.startswith('(reference_id'):
            reference_id = line[line.find('"')+1:line.rfind('"')]
            precomp_layer.reference_id = reference_id
            idx += 1
        elif line.startswith('(dimensions'):
            dim_attrs = parse_tag_attrs(line)
            precomp_layer.width = int(float(dim_attrs.get("width", 512)))
            precomp_layer.height = int(float(dim_attrs.get("height", 512)))
            idx += 1
        elif line.startswith('(masksProperties'):
            # masksProperties
            precomp_layer.masksProperties = []
            idx += 1
            
            while idx < len(lines) and not lines[idx].startswith('(/masksProperties)'):
                if lines[idx].startswith('(mask '):
                    # mask
                    mask_attrs = parse_tag_attrs(lines[idx])
                    mask = {}
                    
                    #
                    if "inv" in mask_attrs:
                        mask["inv"] = mask_attrs["inv"].lower() == "true"
                    if "mode" in mask_attrs:
                        mask["mode"] = mask_attrs["mode"]
                    if "nm" in mask_attrs:
                        mask["nm"] = mask_attrs["nm"]
                    
                    idx += 1
                    
                    # mask
                    while idx < len(lines) and not lines[idx].startswith('(/mask)'):
                        if lines[idx].startswith('(mask_pt '):
                            # pt
                            pt_attrs = parse_tag_attrs(lines[idx])
                            mask["pt"] = {}
                            if "a" in pt_attrs:
                                mask["pt"]["a"] = int(pt_attrs["a"])
                            if "ix" in pt_attrs:
                                mask["pt"]["ix"] = int(pt_attrs["ix"])
                            
                            idx += 1
                            
                            # pt.k
                            if idx < len(lines) and lines[idx].startswith('(mask_pt_k'):
                                if lines[idx].startswith('(mask_pt_k_array'):
                                    # k
                                    mask["pt"]["k"] = []
                                    idx += 1
                                    
                                    #
                                    while idx < len(lines) and not lines[idx].startswith('(/mask_pt_k_array)'):
                                        if lines[idx].startswith('(mask_pt_keyframe'):
                                            kf_attrs = parse_tag_attrs(lines[idx])
                                            keyframe = {}
                                            
                                            if "t" in kf_attrs:
                                                keyframe["t"] = float(kf_attrs["t"])
                                            
                                            idx += 1
                                            
                                            # ...
                                            while idx < len(lines) and not lines[idx].startswith('(/mask_pt_keyframe)'):
                                                if lines[idx].startswith('(mask_pt_kf_i'):
                                                    i_attrs = parse_tag_attrs(lines[idx])
                                                    keyframe["i"] = {
                                                        "x": float(i_attrs.get("x", 0)),
                                                        "y": float(i_attrs.get("y", 0))
                                                    }
                                                    idx += 1
                                                elif lines[idx].startswith('(mask_pt_kf_o'):
                                                    o_attrs = parse_tag_attrs(lines[idx])
                                                    keyframe["o"] = {
                                                        "x": float(o_attrs.get("x", 0)),
                                                        "y": float(o_attrs.get("y", 0))
                                                    }
                                                    idx += 1
                                                elif lines[idx].startswith('(mask_pt_kf_s'):
                                                    keyframe["s"] = []
                                                    idx += 1
                                                    while idx < len(lines) and not lines[idx].startswith('(/mask_pt_kf_s)'):
                                                        if lines[idx].startswith('(mask_pt_kf_shape'):
                                                            shape_attrs = parse_tag_attrs(lines[idx])
                                                            shape = {}
                                                            if "c" in shape_attrs:
                                                                shape["c"] = shape_attrs["c"].lower() == "true"
                                                            idx += 1
                                                            while idx < len(lines) and not lines[idx].startswith('(/mask_pt_kf_shape)'):
                                                                if lines[idx].startswith('(mask_pt_kf_shape_i'):
                                                                    values = extract_numbers(lines[idx])
                                                                    shape["i"] = []
                                                                    for i in range(0, len(values), 2):
                                                                        if i + 1 < len(values):
                                                                            shape["i"].append([values[i], values[i+1]])
                                                                    idx += 1
                                                                elif lines[idx].startswith('(mask_pt_kf_shape_o'):
                                                                    values = extract_numbers(lines[idx])
                                                                    shape["o"] = []
                                                                    for i in range(0, len(values), 2):
                                                                        if i + 1 < len(values):
                                                                            shape["o"].append([values[i], values[i+1]])
                                                                    idx += 1
                                                                elif lines[idx].startswith('(mask_pt_kf_shape_v'):
                                                                    values = extract_numbers(lines[idx])
                                                                    shape["v"] = []
                                                                    for i in range(0, len(values), 2):
                                                                        if i + 1 < len(values):
                                                                            shape["v"].append([values[i], values[i+1]])
                                                                    idx += 1
                                                                else:
                                                                    idx += 1
                                                            if lines[idx].startswith('(/mask_pt_kf_shape)'):
                                                                idx += 1
                                                            keyframe["s"].append(shape)
                                                        else:
                                                            idx += 1
                                                    if lines[idx].startswith('(/mask_pt_kf_s)'):
                                                        idx += 1
                                                else:
                                                    idx += 1
                                            
                                            if lines[idx].startswith('(/mask_pt_keyframe)'):
                                                idx += 1
                                            
                                            mask["pt"]["k"].append(keyframe)
                                        else:
                                            idx += 1
                                    
                                    if lines[idx].startswith('(/mask_pt_k_array)'):
                                        idx += 1
                                
                                else:
                                    # kshape
                                    mask["pt"]["k"] = {}
                                    idx += 1
                                    
                                    # shape
                                    while idx < len(lines) and not lines[idx].startswith('(/mask_pt_k)'):
                                        if lines[idx].startswith('(mask_pt_k_c'):
                                            # closed
                                            parts = lines[idx].split()
                                            if len(parts) > 1:
                                                mask["pt"]["k"]["c"] = parts[1].rstrip(')').lower() == "true"
                                            idx += 1
                                        
                                        elif lines[idx].startswith('(mask_pt_k_i'):
                                            # i
                                            values = extract_numbers(lines[idx])
                                            mask["pt"]["k"]["i"] = []
                                            for i in range(0, len(values), 2):
                                                if i + 1 < len(values):
                                                    mask["pt"]["k"]["i"].append([values[i], values[i+1]])
                                            idx += 1
                                        
                                        elif lines[idx].startswith('(mask_pt_k_o'):
                                            # o
                                            values = extract_numbers(lines[idx])
                                            mask["pt"]["k"]["o"] = []
                                            for i in range(0, len(values), 2):
                                                if i + 1 < len(values):
                                                    mask["pt"]["k"]["o"].append([values[i], values[i+1]])
                                            idx += 1
                                        
                                        elif lines[idx].startswith('(mask_pt_k_v'):
                                            # v
                                            values = extract_numbers(lines[idx])
                                            mask["pt"]["k"]["v"] = []
                                            for i in range(0, len(values), 2):
                                                if i + 1 < len(values):
                                                    mask["pt"]["k"]["v"].append([values[i], values[i+1]])
                                            idx += 1
                                        else:
                                            idx += 1
                                    
                                    if lines[idx].startswith('(/mask_pt_k)'):
                                        idx += 1
                            
                            if idx < len(lines) and lines[idx].startswith('(/mask_pt)'):
                                idx += 1
                        
                        elif lines[idx].startswith('(mask_o '):
                            # opacity
                            o_attrs = parse_tag_attrs(lines[idx])
                            mask["o"] = {}
                            if "a" in o_attrs:
                                mask["o"]["a"] = int(o_attrs["a"])
                            if "k" in o_attrs:
                                mask["o"]["k"] = float(o_attrs["k"])
                            if "ix" in o_attrs:
                                mask["o"]["ix"] = int(o_attrs["ix"])
                            idx += 1
                        
                        elif lines[idx].startswith('(mask_x '):
                            # dilate
                            x_attrs = parse_tag_attrs(lines[idx])
                            mask["x"] = {}
                            if "a" in x_attrs:
                                mask["x"]["a"] = int(x_attrs["a"])
                            if "k" in x_attrs:
                                mask["x"]["k"] = float(x_attrs["k"])
                            if "ix" in x_attrs:
                                mask["x"]["ix"] = int(x_attrs["ix"])
                            idx += 1
                        else:
                            idx += 1
                    
                    if lines[idx].startswith('(/mask)'):
                        idx += 1
                    
                    precomp_layer.masksProperties.append(mask)
                else:
                    idx += 1
            
            if lines[idx].startswith('(/masksProperties)'):
                idx += 1

            
        
        elif lines[idx].startswith('(effects'):
            # effects
            effects, new_idx = parse_effects_tag(lines, idx)
            precomp_layer.ef = effects
            idx = new_idx
        
        elif line.startswith('(ct'):
            # ct
            ct_value = extract_number(line)
            precomp_layer.ct = ct_value
            idx += 1

        elif line.startswith('(tm '):
            # tm
            tm_attrs = parse_tag_attrs(line)
            tm_data = {}
            if 'a' in tm_attrs:
                tm_data['a'] = int(tm_attrs['a'])
            if 'ix' in tm_attrs:
                tm_data['ix'] = int(tm_attrs['ix'])
            
            # keyframes
            idx += 1
            keyframes = []
            while idx < len(lines):
                line = lines[idx]
                if line.startswith('(keyframe'):
                    kf_attrs = parse_tag_attrs(line)
                    kf = {}
                    if 't' in kf_attrs:
                        kf['t'] = float(kf_attrs['t'])
                    if 's' in kf_attrs:
                        kf['s'] = [float(kf_attrs['s'])]
                    if 'h' in kf_attrs:
                        kf['h'] = int(kf_attrs['h'])
                    
                    #  -
                    if 'i_x' in kf_attrs or 'i_y' in kf_attrs:
                        kf['i'] = {}
                        if 'i_x' in kf_attrs:
                            kf['i']['x'] = float(kf_attrs['i_x'])  #
                        if 'i_y' in kf_attrs:
                            kf['i']['y'] = float(kf_attrs['i_y'])  #
                    
                    if 'o_x' in kf_attrs or 'o_y' in kf_attrs:
                        kf['o'] = {}
                        if 'o_x' in kf_attrs:
                            kf['o']['x'] = float(kf_attrs['o_x'])  #
                        if 'o_y' in kf_attrs:
                            kf['o']['y'] = float(kf_attrs['o_y'])  #
                    
                    keyframes.append(kf)
                    idx += 1
                elif line.startswith('(value'):
                    #
                    val = extract_number(line)
                    tm_data['k'] = val
                    idx += 1
                elif line.strip() == '(/tm)':
                    if keyframes:
                        tm_data['k'] = keyframes
                    idx += 1
                    break
                else:
                    idx += 1
            
            precomp_layer.tm = tm_data

        elif line.startswith('(parent'):
            parent_index = int(extract_number(line))
            precomp_layer.parent_index = parent_index
            idx += 1
        elif line.startswith('(transform'):
            transform, new_idx = parse_transform_tag(lines, idx)
            precomp_layer.transform = transform
            idx = new_idx
        elif line.strip() == '(/precomp_layer)':
            idx += 1
            break
        else:
            idx += 1
    
    return precomp_layer, idx


def parse_tag_attrs(line):
    """Parse tag attributes, including complex values like JSON arrays"""
    # Extract tag content
    content = line[1:-1]  # Remove parentheses
    
    # Find first space to separate tag name and attributes
    first_space = content.find(' ')
    if first_space == -1:
        return {}
    
    tag_name = content[:first_space]
    attrs_part = content[first_space+1:]
    
    # Handle quoted tag name
    if tag_name.startswith('"') and tag_name.endswith('"'):
        tag_name = tag_name[1:-1]
    
    # Parse attributes
    attrs = {}
    
    # Process the attributes string with proper handling for complex values
    i = 0
    while i < len(attrs_part):
        # Skip whitespace
        while i < len(attrs_part) and attrs_part[i].isspace():
            i += 1
        
        if i >= len(attrs_part):
            break
        
        # Find attribute name
        start = i
        while i < len(attrs_part) and attrs_part[i] not in "= \t\n\r":
            i += 1
        
        if i >= len(attrs_part):
            break
        
        attr_name = attrs_part[start:i]
        
        # Skip to the value
        while i < len(attrs_part) and (attrs_part[i].isspace() or attrs_part[i] == '='):
            i += 1
        
        if i >= len(attrs_part):
            break
        
        # Parse attribute value based on its format
        if attrs_part[i] == '"':
            # Quoted string
            i += 1  # Skip opening quote
            start = i
            while i < len(attrs_part) and attrs_part[i] != '"':
                i += 1
            
            attr_value = attrs_part[start:i]
            i += 1  # Skip closing quote
        elif attrs_part[i] == '[':
            # Handle JSON array or list
            bracket_count = 1
            start = i
            i += 1
            
            while i < len(attrs_part) and bracket_count > 0:
                if attrs_part[i] == '[':
                    bracket_count += 1
                elif attrs_part[i] == ']':
                    bracket_count -= 1
                
                i += 1
            
            attr_value = attrs_part[start:i]
        else:
            # Regular value
            start = i
            while i < len(attrs_part) and not attrs_part[i].isspace():
                i += 1
            
            attr_value = attrs_part[start:i]
        
        attrs[attr_name] = attr_value
    
    return attrs


def extract_numbers(line):
    """"""
    #
    start_idx = line.find(' ')
    if start_idx == -1:
        return []
    content = line[start_idx:].strip()
    
    #
    return [float(x) for x in re.findall(r'-?\d+\.?\d*', content)]

def extract_number(line):
    """"""
    numbers = extract_numbers(line)
    return numbers[0] if numbers else 0


# Multi-threaded folder processing
solid_color_layer_to_json = solid_layer_to_json


<!-- <div align= "center">
    <h1> Official repo for OmniSVG</h1>

</div> -->

<h3 align="center"><strong>OmniLottie: Generating Vector Animations via Parameterized Lottie Tokens
</strong></h3>


<div align="center">
<a href='https://arxiv.org/abs/2603.02138'><img src='https://img.shields.io/badge/arXiv-2603.02138-b31b1b.svg'></a> &nbsp;&nbsp;&nbsp;&nbsp;
 <a href='https://openvglab.github.io/OmniLottie/'><img src='https://img.shields.io/badge/Project-Page-Green'></a> &nbsp;&nbsp;&nbsp;&nbsp;
<a href="https://huggingface.co/OmniLottie/OmniLottie"><img src="https://img.shields.io/badge/%F0%9F%A4%97%20Weights-HF-orange"></a> &nbsp;&nbsp;&nbsp;&nbsp;
<a href="https://huggingface.co/datasets/OmniLottie/MMLottie-2M"><img src="https://img.shields.io/badge/%F0%9F%A4%97%20Dataset%20-HF-orange"></a> &nbsp;&nbsp;&nbsp;&nbsp;
<a href="https://huggingface.co/datasets/OmniLottie/MMLottieBench"><img src="https://img.shields.io/badge/%F0%9F%A4%97%20Bench-HF-orange"></a> &nbsp;&nbsp;&nbsp;&nbsp;
<a href="https://huggingface.co/spaces/OmniLottie/OmniLottie"><img src="https://img.shields.io/badge/%F0%9F%A4%97%20Demo%20-HF-orange"></a> &nbsp;&nbsp;&nbsp;&nbsp;
<!-- <a href='https://github.com/OpenVGLab/OmniLottie'><img src='https://img.shields.io/badge/Training-Code-blue?logo=github'></a> -->
</div>


# ComfyUI_OmniLottie
[OmniLottie](https://github.com/OpenVGLab/OmniLottie):  Generating Vector Animations via Parameterized Lottie Tokens

# Update
* 已更新插件，连入视频或者图片开启图片或者视频生成模式，注意图片模式要最好加入描述提示词，有用记得给官方项目打星。  
* The node has been updated to enable image or video generation mode when connecting to videos or images. It is recommended to add descriptive prompts to the image mode,Remember to star the official project if it is useful.

# 1. Installation

In the ./ComfyUI/custom_nodes directory, run the following:   
```
git clone https://github.com/smthemex/ComfyUI_OmniLottie.git
```

# 2. Requirements  
```
pip install -r requirements.txt
```

# 3.Model
* merge model  from [OmniLottie](https://huggingface.co/smthem/OmniLottie-merge)  #  模型地址,针对官方的模型加载流程做了少许改动，目前使用的模型是qwen底模和 OmniLottie合并后的单体模型，没梯子就去我云盘拉取； 
```
--  ComfyUI/models/diffusion_models/
    |--Lottie_weight.safetensors
```
# Example
![](https://github.com/smthemex/ComfyUI_OmniLottie/blob/main/example_workflows/example.png)

# Citation
```
@article{yang2026omnilottie,
  title={OmniLottie: Generating Vector Animations via Parameterized Lottie Tokens},
  author={Yiying Yang and Wei Cheng and Sijin Chen and Honghao Fu and Xianfang Zeng and Yujun Cai and Gang Yu and Xinjun Ma},
  journal={arXiv preprint arxiv:2603.02138},
  year={2026}
}
```

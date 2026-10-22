from typing_extensions import override
from comfy_api.latest import ComfyExtension, io
from .OmniLottie_node import OmniLottie_SM_Model,OmniLottie_SM_KSampler

class OmniLottie_SM_Extension(ComfyExtension):
    @override
    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        return [
            OmniLottie_SM_Model,
            OmniLottie_SM_KSampler,
        ]


async def comfy_entrypoint() -> OmniLottie_SM_Extension:
    return OmniLottie_SM_Extension()

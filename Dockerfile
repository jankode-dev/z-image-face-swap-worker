FROM runpod/worker-comfyui:5.8.5-base

# Custom nodes only — all models on network volume.
RUN comfy-node-install \
    comfyui_controlnet_aux \
    comfyui-inpaint-cropandstitch

COPY extra_model_paths.yaml /comfyui/extra_model_paths.yaml

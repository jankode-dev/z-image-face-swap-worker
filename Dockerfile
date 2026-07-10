FROM runpod/worker-comfyui:5.8.5-base

# CORE cvorovi (SAM3, ZImageFunControlnet...) traze ComfyUI >= v0.23 — pin na v0.27.0 kao na podu
RUN cd /comfyui && \
    git fetch --all --tags && \
    git checkout v0.27.0 && \
    pip install -r requirements.txt

# Custom nodes only — all models on network volume.
RUN comfy-node-install \
    comfyui_controlnet_aux \
    comfyui-inpaint-cropandstitch

COPY extra_model_paths.yaml /comfyui/extra_model_paths.yaml

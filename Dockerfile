FROM runpod/worker-comfyui:5.8.5-base

# Depth map preprocessor + inpaint crop/stitch (face-lock pass)
RUN comfy-node-install \
    comfyui_controlnet_aux \
    comfyui-inpaint-cropandstitch

# Depth Anything V2 — avoid flaky auto-download on cold serverless starts
RUN comfy model download \
    --url "https://huggingface.co/depth-anything/Depth-Anything-V2-Large/resolve/main/depth_anything_v2_vitl.pth" \
    --relative-path models/annotator/depth-anything/Depth-Anything-V2-Large \
    --filename depth_anything_v2_vitl.pth

# Large models (z_image, qwen, ae, sam3, controlnet union, loras) live on the network volume.
COPY extra_model_paths.yaml /comfyui/extra_model_paths.yaml

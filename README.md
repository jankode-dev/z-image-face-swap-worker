# z-image-face-swap-worker

RunPod **serverless** worker for the Z-Image Reimagine v11 workflow (reference → LoRA character reimagine + face lock).

Built on [`runpod/worker-comfyui`](https://github.com/runpod-workers/worker-comfyui). Models load from a **network volume**; custom nodes and the depth annotator model are baked into the Docker image. **LoRA is not baked in** — pass `lora_name` per request (file must exist on the volume under `models/loras/`).

---

## What's inside

| File | Purpose |
|------|---------|
| `Dockerfile` | Base worker + controlnet_aux + inpaint-cropandstitch + depth model |
| `extra_model_paths.yaml` | Points ComfyUI at the network volume |
| `workflow/zimage_reimagine_v11_api.json` | API-format workflow (compute path only) |
| `test_input.json` | curl payload template |
| `client.py` | Python test client |
| `.github/workflows/build.yml` | Builds & pushes `janko24/z-image-face-swap-worker:latest` on push to `main` |

---

## Prerequisites

### 1. Network volume models

Base path: `/runpod-volume/runpod-slim/ComfyUI/`

```
models/diffusion_models/z_image_turbo_bf16.safetensors
models/text_encoders/qwen_3_4b.safetensors
models/vae/ae.safetensors
models/checkpoints/sam3.1_multiplex_fp16.safetensors          ← NEW for this worker
models/model_patches/Z-Image-Turbo-Fun-Controlnet-Union-2.1-2602-8steps.safetensors  ← NEW
models/loras/<your_lora>.safetensors                          ← per character, not in Docker
```

Depth model (`depth_anything_v2_vitl.pth`) is **baked into the image**, not required on the volume.

### 2. Docker Hub secret

Add repo secret **`DOCKERHUB_TOKEN`** (Settings → Secrets → Actions). The workflow logs in as `janko24`.

---

## Build

Push to `main` → GitHub Action builds and pushes automatically.

Manual build:

```bash
docker build --platform linux/amd64 -t janko24/z-image-face-swap-worker:latest .
docker push janko24/z-image-face-swap-worker:latest
```

---

## Deploy on RunPod Serverless

1. **Serverless → New Endpoint → Import from Docker Registry**
2. Image: `janko24/z-image-face-swap-worker:latest`
3. Attach the **network volume** with the models above
4. GPU: **24 GB** minimum (4090 / L4), **48 GB** recommended (L40S)
5. Create endpoint, wait for **Ready**

If models are missing, set env `NETWORK_VOLUME_DEBUG=true` and check worker logs.

---

## API usage

One reference image + workflow JSON. The `name` must match LoadImage node 14:

- `reference.png` → node **14**

### curl

```bash
curl -X POST \
  -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d @request.json \
  https://api.runpod.ai/v2/<ENDPOINT_ID>/runsync
```

`request.json`:

```json
{
  "input": {
    "workflow": { "...contents of workflow/zimage_reimagine_v11_api.json..." },
    "images": [
      { "name": "reference.png", "image": "<base64>" }
    ]
  }
}
```

### Python

```bash
export RUNPOD_API_KEY=xxxxx
export RUNPOD_ENDPOINT_ID=xxxxx
python client.py reference.png --lora Woman123_000002900.safetensors --prompt "Woman123, photo of Woman123, ..."
```

Output: `output.images` (base64 by default). Produced by SaveImage node **36**.

---

## Per-request patches (KoReel / API)

| Node | Field | Default | Notes |
|------|-------|---------|-------|
| `6` LoraLoaderModelOnly | `lora_name`, `strength_model` | `your_lora.safetensors`, 1.4 | LoRA on volume |
| `11` CLIPTextEncode | `text` | regen prompt | trigger + scene/clothing |
| `13` CLIPTextEncode | `text` | face-lock prompt | trigger + face quality |
| `14` LoadImage | `image` | `reference.png` | must match images[].name |
| `20` ZImageFunControlnet | `strength` | 0.55 | depth CN |
| `23` KSampler | `seed`, `denoise` | 8021, 0.65 | REGEN pass |
| `32` KSampler | `seed`, `denoise` | 8022, 0.55 | face-lock pass |

---

## Editing the workflow

Load in ComfyUI, edit, then **Workflow → Export (API)** and overwrite `workflow/zimage_reimagine_v11_api.json`. Remove preview/note nodes before export.

---

## Notes

- Custom nodes belong **in the Docker image** (Python deps), not on the volume.
- LoRA files belong **on the volume** (`models/loras/`), selected per request.
- If `SAM3_Detect` or `ZImageFunControlnet` fail on cold start, bump the base image tag in `Dockerfile` to a newer `runpod/worker-comfyui` release that includes recent ComfyUI.

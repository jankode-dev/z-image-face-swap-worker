#!/usr/bin/env python3
"""
Minimal client for the z-image-face-swap serverless endpoint.

Usage:
  export RUNPOD_API_KEY=xxxxx
  export RUNPOD_ENDPOINT_ID=xxxxx
  python client.py reference.png [--lora your_lora.safetensors] [--prompt "..."] [--seed 123]

reference.png -> LoadImage node 14
"""
import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path
from urllib import request as urlrequest

API_KEY = os.environ.get("RUNPOD_API_KEY")
ENDPOINT_ID = os.environ.get("RUNPOD_ENDPOINT_ID")
WORKFLOW_PATH = Path(__file__).parent / "workflow" / "zimage_reimagine_v11_api.json"


def b64(path: str) -> str:
    return base64.b64encode(Path(path).read_bytes()).decode()


def post(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode()
    req = urlrequest.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
    )
    with urlrequest.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def main() -> None:
    if not API_KEY or not ENDPOINT_ID:
        sys.exit("Set RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID env vars first.")

    ap = argparse.ArgumentParser()
    ap.add_argument("reference", help="Reference/composition image")
    ap.add_argument("--lora", default=None, help="LoRA filename on volume (models/loras/)")
    ap.add_argument("--lora-strength", type=float, default=None, help="LoRA strength_model (default 1.4)")
    ap.add_argument("--prompt", default=None, help="Regen prompt (node 11)")
    ap.add_argument("--face-prompt", default=None, help="Face-lock prompt (node 13)")
    ap.add_argument("--seed-regen", type=int, default=None, help="REGEN KSampler seed (node 23)")
    ap.add_argument("--seed-face", type=int, default=None, help="Face-lock KSampler seed (node 32)")
    ap.add_argument("--denoise-regen", type=float, default=None, help="REGEN denoise (node 23)")
    ap.add_argument("--denoise-face", type=float, default=None, help="Face-lock denoise (node 32)")
    ap.add_argument("--depth-strength", type=float, default=None, help="Depth CN strength (node 20)")
    args = ap.parse_args()

    wf = json.loads(WORKFLOW_PATH.read_text())

    if args.lora is not None:
        wf["6"]["inputs"]["lora_name"] = args.lora
    if args.lora_strength is not None:
        wf["6"]["inputs"]["strength_model"] = args.lora_strength
    if args.prompt is not None:
        wf["11"]["inputs"]["text"] = args.prompt
    if args.face_prompt is not None:
        wf["13"]["inputs"]["text"] = args.face_prompt
    if args.seed_regen is not None:
        wf["23"]["inputs"]["seed"] = args.seed_regen
    if args.seed_face is not None:
        wf["32"]["inputs"]["seed"] = args.seed_face
    if args.denoise_regen is not None:
        wf["23"]["inputs"]["denoise"] = args.denoise_regen
    if args.denoise_face is not None:
        wf["32"]["inputs"]["denoise"] = args.denoise_face
    if args.depth_strength is not None:
        wf["20"]["inputs"]["strength"] = args.depth_strength

    payload = {
        "input": {
            "workflow": wf,
            "images": [
                {"name": "reference.png", "image": b64(args.reference)},
            ],
        }
    }

    base = f"https://api.runpod.ai/v2/{ENDPOINT_ID}"
    print("Submitting job (runsync)...")
    t0 = time.time()
    result = post(f"{base}/runsync", payload)

    status = result.get("status")
    if status != "COMPLETED":
        print(json.dumps(result, indent=2)[:4000])
        sys.exit(f"Job status: {status}")

    images = result.get("output", {}).get("images", [])
    if not images:
        sys.exit("No images in output.")

    for i, img in enumerate(images):
        if img.get("type") == "base64":
            out = f"result_{i}.png"
            Path(out).write_bytes(base64.b64decode(img["data"]))
            print(f"Saved {out}")
        else:
            print(f"Image URL: {img['data']}")

    print(f"Done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()

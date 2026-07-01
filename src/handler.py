import runpod
import json
import base64
import os
import time
from io import BytesIO
from PIL import Image

# The base image includes this utility
try:
    from runpod_comfyui import ComfyUI
except ImportError:
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "runpod-comfyui"])
    from runpod_comfyui import ComfyUI

comfyui = None


def setup():
    global comfyui
    comfyui = ComfyUI("127.0.0.1", 8188)
    comfyui.wait_for_server()
    print("✅ ComfyUI server ready.")


def handler(job):
    global comfyui
    if comfyui is None:
        setup()

    # 1. Load your workflow (API format)
    # The generated repo places it in the root as workflow_api.json
    workflow_path = "/comfyui/workflow_api.json"
    if not os.path.exists(workflow_path):
        workflow_path = "workflow_api.json"  # fallback

    with open(workflow_path, "r") as f:
        workflow = json.load(f)

    # 2. Handle input images
    input_images = job["input"].get("images", [])
    for img_data in input_images:
        name = img_data.get("name", "input.png")
        # Decode base64 (strip data:image/...;base64, if present)
        raw = img_data["image"]
        if "," in raw:
            raw = raw.split(",")[-1]
        img_bytes = base64.b64decode(raw)
        img = Image.open(BytesIO(img_bytes))

        # Save to ComfyUI's input folder
        save_path = f"/comfyui/input/{name}"
        img.save(save_path)

        # Update ALL LoadImage nodes to use this file
        for node_id, node in workflow.items():
            if node.get("class_type") == "LoadImage":
                node["inputs"]["image"] = name

    # 3. Queue the prompt
    prompt_id = comfyui.queue_prompt(workflow)
    outputs = comfyui.get_result(prompt_id)

    # 4. Extract images from all SaveImage nodes
    result_images = []
    for img_data in outputs.get("images", []):
        # Each item has "data" (base64) and "file_name"
        result_images.append(img_data["data"])

    # If you want to return them as a single concatenated string, change here.
    # But an array is more useful.
    return {"images": result_images}


if __name__ == "__main__":
    setup()
    runpod.serverless.start({"handler": handler})

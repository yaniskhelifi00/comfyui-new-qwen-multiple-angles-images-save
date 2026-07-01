import runpod
import json
import base64
import os
from io import BytesIO
from PIL import Image
from runpod_comfyui import ComfyUI

comfy = None

def initialize():
    global comfy
    print("⏳ Waiting for ComfyUI...")
    comfy = ComfyUI("127.0.0.1", 8188)
    comfy.wait_for_server()
    print("✅ ComfyUI ready.")

def handler(job):
    global comfy
    if comfy is None:
        initialize()

    # Load workflow
    with open("/comfyui/workflow_api.json", "r") as f:
        workflow = json.load(f)

    # Handle input image
    images_input = job["input"].get("images", [])
    if images_input:
        img_data = images_input[0]
        name = img_data.get("name", "input.png")
        raw = img_data["image"]
        if "," in raw:
            raw = raw.split(",")[-1]
        img_bytes = base64.b64decode(raw)
        img = Image.open(BytesIO(img_bytes))
        save_path = f"/comfyui/input/{name}"
        img.save(save_path)

        # Update all LoadImage nodes
        for node in workflow.values():
            if node.get("class_type") == "LoadImage":
                node["inputs"]["image"] = name

    # Queue prompt
    prompt_id = comfy.queue_prompt(workflow)
    outputs = comfy.get_result(prompt_id)

    # Extract images
    result_images = [img["data"] for img in outputs.get("images", [])]
    return {"images": result_images}

if __name__ == "__main__":
    initialize()
    runpod.serverless.start({"handler": handler})

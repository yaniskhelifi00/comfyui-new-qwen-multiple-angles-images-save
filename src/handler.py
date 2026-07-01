import runpod
import json
import base64
import os
from io import BytesIO
from PIL import Image

# This is the official RunPod ComfyUI helper (included in the full image)
from runpod_comfyui import ComfyUI

comfy = None

def initialize():
    global comfy
    print("⏳ Waiting for ComfyUI server...")
    comfy = ComfyUI("127.0.0.1", 8188)
    comfy.wait_for_server()
    print("✅ ComfyUI is ready.")

def handler(job):
    global comfy
    if comfy is None:
        initialize()

    # 1. Load your workflow
    workflow_path = "/comfyui/workflow_api.json"
    if not os.path.exists(workflow_path):
        # fallback if running locally
        workflow_path = "workflow_api.json"
    
    with open(workflow_path, "r") as f:
        workflow = json.load(f)

    # 2. Handle the input image
    images_input = job["input"].get("images", [])
    if images_input:
        img_data = images_input[0]
        name = img_data.get("name", "input.png")
        
        # Decode base64 (strip data:image/...;base64, if present)
        raw = img_data["image"]
        if "," in raw:
            raw = raw.split(",")[-1]
        img_bytes = base64.b64decode(raw)
        img = Image.open(BytesIO(img_bytes))
        
        # Save to ComfyUI input folder
        save_path = f"/comfyui/input/{name}"
        img.save(save_path)
        print(f"📥 Saved image to {save_path}")

        # Update ALL LoadImage nodes to use this filename
        for node_id, node in workflow.items():
            if node.get("class_type") == "LoadImage":
                node["inputs"]["image"] = name
                print(f"🔄 Updated node {node_id} to load '{name}'")
    else:
        print("⚠️ No images provided in request.")

    # 3. Run the generation
    print("🚀 Queuing prompt...")
    prompt_id = comfy.queue_prompt(workflow)
    print(f"📋 Prompt ID: {prompt_id}")
    
    outputs = comfy.get_result(prompt_id)
    print("✅ Generation finished.")

    # 4. Extract all generated images (your 6 angles)
    result_images = []
    for img_item in outputs.get("images", []):
        # img_item contains 'data' (base64) and 'file_name'
        result_images.append(img_item["data"])

    print(f"🖼️ Returning {len(result_images)} images.")
    return {"images": result_images}

if __name__ == "__main__":
    initialize()
    print("🚀 Starting RunPod serverless handler...")
    runpod.serverless.start({"handler": handler})

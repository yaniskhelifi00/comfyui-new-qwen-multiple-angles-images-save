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
    print("⏳ Waiting for ComfyUI server...")
    comfy = ComfyUI("127.0.0.1", 8188)
    comfy.wait_for_server()
    print("✅ ComfyUI ready.")

def handler(job):
    global comfy
    if comfy is None:
        initialize()

    # Load your workflow (copied during Docker build)
    workflow_path = "/comfyui/workflow_api.json"
    
    # Fallback for local testing
    if not os.path.exists(workflow_path):
        workflow_path = "workflow_api.json"
    
    with open(workflow_path, "r") as f:
        workflow = json.load(f)

    # 1. Process input images
    images_input = job["input"].get("images", [])
    if images_input:
        for img_data in images_input:
            name = img_data.get("name", "input.png")
            raw = img_data["image"]
            if "," in raw:
                raw = raw.split(",")[-1]
            img_bytes = base64.b64decode(raw)
            img = Image.open(BytesIO(img_bytes))
            save_path = f"/comfyui/input/{name}"
            img.save(save_path)
            print(f"📥 Saved image to {save_path}")

            # Update ALL LoadImage nodes to use this filename
            for node_id, node in workflow.items():
                if node.get("class_type") == "LoadImage":
                    node["inputs"]["image"] = name
                    print(f"🔄 Updated node {node_id} to load '{name}'")
    else:
        print("⚠️ No images provided, using existing placeholder image.")

    # 2. Queue the prompt
    print("🚀 Queuing prompt...")
    prompt_id = comfy.queue_prompt(workflow)
    print(f"📋 Prompt ID: {prompt_id}")
    
    outputs = comfy.get_result(prompt_id)
    print("✅ Generation finished.")

    # 3. Extract all images from SaveImage nodes (your 6 angles)
    result_images = []
    for img_item in outputs.get("images", []):
        result_images.append(img_item["data"])

    print(f"🖼️ Returning {len(result_images)} images.")
    return {"images": result_images}

if __name__ == "__main__":
    initialize()
    print("🚀 Starting RunPod serverless handler...")
    runpod.serverless.start({"handler": handler})

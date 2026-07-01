import runpod
import json
import base64
import os
import time
import requests
from io import BytesIO
from PIL import Image

COMFY_HOST = "127.0.0.1"
COMFY_PORT = 8188
BASE_URL = f"http://{COMFY_HOST}:{COMFY_PORT}"

def wait_for_comfyui():
    """Wait until ComfyUI is responsive."""
    print("⏳ Waiting for ComfyUI server...")
    while True:
        try:
            resp = requests.get(f"{BASE_URL}/", timeout=5)
            if resp.status_code == 200:
                print("✅ ComfyUI is ready.")
                break
        except:
            pass
        time.sleep(2)

def queue_prompt(workflow):
    """Send the workflow to ComfyUI and return the prompt_id."""
    payload = {"prompt": workflow}
    resp = requests.post(f"{BASE_URL}/prompt", json=payload)
    if resp.status_code != 200:
        raise Exception(f"❌ Failed to queue prompt: {resp.text}")
    return resp.json()["prompt_id"]

def get_history(prompt_id):
    """Fetch the execution history for a given prompt_id."""
    resp = requests.get(f"{BASE_URL}/history/{prompt_id}")
    return resp.json()

def fetch_output_images(prompt_id, timeout=300):
    """Poll the history until the prompt completes, then return base64 images."""
    start = time.time()
    while time.time() - start < timeout:
        history = get_history(prompt_id)
        if prompt_id in history:
            outputs = history[prompt_id].get("outputs", {})
            images = []
            for node_id, node_output in outputs.items():
                if "images" in node_output:
                    for img_info in node_output["images"]:
                        filename = img_info["filename"]
                        img_path = os.path.join("/comfyui/output", filename)
                        if os.path.exists(img_path):
                            with open(img_path, "rb") as f:
                                b64 = base64.b64encode(f.read()).decode()
                                images.append(b64)
                            print(f"📸 Captured output image: {filename}")
            if images:
                return images
            else:
                # Prompt finished but no images found – might be an error.
                print("⚠️ Prompt finished but no images found.")
                return []
        time.sleep(1)
    raise TimeoutError(f"⏰ Prompt {prompt_id} timed out after {timeout}s.")

def handler(job):
    """Main entry point for RunPod serverless."""
    # 1. Load the workflow from the JSON file
    workflow_path = "/comfyui/workflow_api.json"
    if not os.path.exists(workflow_path):
        # fallback for local testing
        workflow_path = "workflow_api.json"
    
    with open(workflow_path, "r") as f:
        workflow = json.load(f)

    # 2. Process the input image (if provided)
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
        print(f"📥 Saved input image to {save_path}")

        # Update all LoadImage nodes to use this filename
        for node_id, node in workflow.items():
            if node.get("class_type") == "LoadImage":
                node["inputs"]["image"] = name
                print(f"🔄 Updated node {node_id} to load '{name}'")
    else:
        print("ℹ️ No input image provided – using existing placeholder.")

    # 3. Queue the prompt and wait for the result
    prompt_id = queue_prompt(workflow)
    print(f"📋 Queued prompt: {prompt_id}")

    images = fetch_output_images(prompt_id)
    print(f"🖼️ Returning {len(images)} image(s).")
    return {"images": images}

if __name__ == "__main__":
    wait_for_comfyui()
    print("🚀 Starting RunPod handler...")
    runpod.serverless.start({"handler": handler})
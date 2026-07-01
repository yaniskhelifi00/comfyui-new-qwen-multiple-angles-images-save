# Use the base image that actually exists
FROM runpod/worker-comfyui:5.8.4-base

ARG HF_TOKEN=""

# ============================================
# 1. Install required Python packages (runpod-comfyui, etc.)
# ============================================

RUN pip install --no-cache-dir runpod-comfyui transformers accelerate sentencepiece protobuf

# ============================================
# 2. Install custom nodes
# ============================================

RUN git clone https://github.com/jtydhr88/ComfyUI-qwenmultiangle /comfyui/custom_nodes/ComfyUI-qwenmultiangle && \
    cd /comfyui/custom_nodes/ComfyUI-qwenmultiangle && \
    (git checkout a6539524a96d21bea6fe0fc01d9b792d2cb1844b 2>/dev/null || true) && \
    pip install --no-cache-dir -r requirements.txt 2>/dev/null || echo "No requirements"

RUN git clone https://github.com/comfyuistudio/ComfyUI-Studio-nodes /comfyui/custom_nodes/ComfyUI-Studio-nodes && \
    pip install --no-cache-dir -r /comfyui/custom_nodes/ComfyUI-Studio-nodes/requirements.txt 2>/dev/null || echo "No requirements"

RUN git clone https://github.com/rocketing/ComfyUI-easy-use /comfyui/custom_nodes/ComfyUI-easy-use && \
    pip install --no-cache-dir -r /comfyui/custom_nodes/ComfyUI-easy-use/requirements.txt 2>/dev/null || echo "No requirements"

# ============================================
# 3. Download models (using wget – more reliable)
# ============================================

WORKDIR /comfyui/models

RUN mkdir -p diffusion_models text_encoders vae loras

RUN wget --progress=dot:giga -O diffusion_models/Qwen-Image-Edit-2511-FP8_e4m3fn.safetensors \
    "https://huggingface.co/xms991/Qwen-Image-Edit-2511-fp8-e4m3fn/resolve/main/qwen_image_edit_2511_fp8_e4m3fn.safetensors" || \
    wget --progress=dot:giga -O diffusion_models/Qwen-Image-Edit-2511-FP8_e4m3fn.safetensors \
    "https://huggingface.co/1038lab/Qwen-Image-Edit-2511-FP8/resolve/main/Qwen-Image-Edit-2511-FP8_e4m3fn.safetensors"

RUN wget --progress=dot:giga -O text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors \
    "https://huggingface.co/Comfy-Org/HunyuanVideo_1.5_repackaged/resolve/main/split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors"

RUN wget --progress=dot:giga -O vae/qwen_image_vae.safetensors \
    "https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/vae/qwen_image_vae.safetensors"

RUN wget --progress=dot:giga -O loras/Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors \
    "https://huggingface.co/lightx2v/Qwen-Image-Edit-2511-Lightning/resolve/main/Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors"

RUN wget --progress=dot:giga -O loras/qwen-image-edit-2511-multiple-angles-lora.safetensors \
    "https://huggingface.co/fal/Qwen-Image-Edit-2511-Multiple-Angles-LoRA/resolve/main/qwen-image-edit-2511-multiple-angles-lora.safetensors"

WORKDIR /

# ============================================
# 4. Copy workflow and handler
# ============================================

COPY workflow_api.json /comfyui/workflow_api.json
COPY src/handler.py /src/handler.py

# ============================================
# 5. Override entrypoint to run our handler
# ============================================

ENTRYPOINT ["python", "-u", "/src/handler.py"]

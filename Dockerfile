# Use the full image (includes runpod-comfyui helper and default handler structure)
FROM runpod/worker-comfyui:5.8.4

# Build-time token for gated downloads (not needed for public models, but keep for flexibility)
ARG HF_TOKEN=""

# ============================================
# 1. Install custom nodes
# ============================================

# QwenMultiangle custom node (fixed to your workflow's commit)
RUN git clone https://github.com/jtydhr88/ComfyUI-qwenmultiangle /comfyui/custom_nodes/ComfyUI-qwenmultiangle && \
    cd /comfyui/custom_nodes/ComfyUI-qwenmultiangle && \
    (git checkout a6539524a96d21bea6fe0fc01d9b792d2cb1844b 2>/dev/null || \
     git fetch origin a6539524a96d21bea6fe0fc01d9b792d2cb1844b --depth=1 && \
     git checkout a6539524a96d21bea6fe0fc01d9b792d2cb1844b || \
     echo "WARN: commit unreachable, using default branch")

# ComfyUI-Studio-nodes (provides HuggingFaceDownloader – you removed it, but harmless to keep)
RUN git clone https://github.com/comfyuistudio/ComfyUI-Studio-nodes /comfyui/custom_nodes/ComfyUI-Studio-nodes

# ComfyUI-easy-use (provides the "easy showAnything" node)
RUN git clone https://github.com/rocketing/ComfyUI-easy-use /comfyui/custom_nodes/ComfyUI-easy-use

# ============================================
# 2. Download all required models
# ============================================

# Diffusion model (BF16 – used as base)
RUN BACKOFFS="10 20 30 60 90" && for i in 1 2 3 4 5; do \
    HF_TOKEN=$HF_TOKEN comfy model download \
    --url 'https://huggingface.co/Comfy-Org/Qwen-Image-Edit_ComfyUI/resolve/main/split_files/diffusion_models/qwen_image_edit_2511_bf16.safetensors' \
    --relative-path models/diffusion_models \
    --filename 'qwen_image_edit_2511_bf16.safetensors' && break; \
    if [ $i -eq 5 ]; then echo "model-download failed after 5 attempts" >&2; exit 1; fi; \
    SLEEP=$(echo $BACKOFFS | cut -d ' ' -f $i) && echo "attempt $i failed, retrying in $SLEEP" >&2; sleep $SLEEP; \
done

# Diffusion model (FP8 – used in your workflow)
RUN BACKOFFS="10 20 30 60 90" && for i in 1 2 3 4 5; do \
    HF_TOKEN=$HF_TOKEN comfy model download \
    --url 'https://huggingface.co/xms991/Qwen-Image-Edit-2511-fp8-e4m3fn/resolve/main/qwen_image_edit_2511_fp8_e4m3fn.safetensors' \
    --relative-path models/diffusion_models \
    --filename 'Qwen-Image-Edit-2511-FP8_e4m3fn.safetensors' && break; \
    if [ $i -eq 5 ]; then echo "model-download failed after 5 attempts" >&2; exit 1; fi; \
    SLEEP=$(echo $BACKOFFS | cut -d ' ' -f $i) && echo "attempt $i failed, retrying in $SLEEP" >&2; sleep $SLEEP; \
done

# Text encoder (CLIP)
RUN BACKOFFS="10 20 30 60 90" && for i in 1 2 3 4 5; do \
    HF_TOKEN=$HF_TOKEN comfy model download \
    --url 'https://huggingface.co/Comfy-Org/HunyuanVideo_1.5_repackaged/resolve/main/split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors' \
    --relative-path models/text_encoders \
    --filename 'qwen_2.5_vl_7b_fp8_scaled.safetensors' && break; \
    if [ $i -eq 5 ]; then echo "model-download failed after 5 attempts" >&2; exit 1; fi; \
    SLEEP=$(echo $BACKOFFS | cut -d ' ' -f $i) && echo "attempt $i failed, retrying in $SLEEP" >&2; sleep $SLEEP; \
done

# VAE
RUN BACKOFFS="10 20 30 60 90" && for i in 1 2 3 4 5; do \
    HF_TOKEN=$HF_TOKEN comfy model download \
    --url 'https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/vae/qwen_image_vae.safetensors' \
    --relative-path models/vae \
    --filename 'qwen_image_vae.safetensors' && break; \
    if [ $i -eq 5 ]; then echo "model-download failed after 5 attempts" >&2; exit 1; fi; \
    SLEEP=$(echo $BACKOFFS | cut -d ' ' -f $i) && echo "attempt $i failed, retrying in $SLEEP" >&2; sleep $SLEEP; \
done

# LoRA 1 – Lightning (speed optimization)
RUN BACKOFFS="10 20 30 60 90" && for i in 1 2 3 4 5; do \
    HF_TOKEN=$HF_TOKEN comfy model download \
    --url 'https://huggingface.co/lightx2v/Qwen-Image-Edit-2511-Lightning/resolve/main/Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors' \
    --relative-path models/loras \
    --filename 'Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors' && break; \
    if [ $i -eq 5 ]; then echo "model-download failed after 5 attempts" >&2; exit 1; fi; \
    SLEEP=$(echo $BACKOFFS | cut -d ' ' -f $i) && echo "attempt $i failed, retrying in $SLEEP" >&2; sleep $SLEEP; \
done

# LoRA 2 – Multiple Angles (core for your workflow)
RUN BACKOFFS="10 20 30 60 90" && for i in 1 2 3 4 5; do \
    HF_TOKEN=$HF_TOKEN comfy model download \
    --url 'https://huggingface.co/fal/Qwen-Image-Edit-2511-Multiple-Angles-LoRA/resolve/main/qwen-image-edit-2511-multiple-angles-lora.safetensors' \
    --relative-path models/loras \
    --filename 'qwen-image-edit-2511-multiple-angles-lora.safetensors' && break; \
    if [ $i -eq 5 ]; then echo "model-download failed after 5 attempts" >&2; exit 1; fi; \
    SLEEP=$(echo $BACKOFFS | cut -d ' ' -f $i) && echo "attempt $i failed, retrying in $SLEEP" >&2; sleep $SLEEP; \
done

# ============================================
# 3. Copy your workflow and handler
# ============================================

# Copy the API workflow JSON into the ComfyUI directory
COPY workflow_api.json /comfyui/workflow_api.json

# Copy your custom handler script
COPY src/handler.py /src/handler.py

# ============================================
# 4. Override the default CMD
# ============================================

# Explicitly run your handler – this bypasses any auto-discovery issues
CMD ["python", "-u", "/src/handler.py"]

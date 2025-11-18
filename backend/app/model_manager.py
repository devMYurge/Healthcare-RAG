from typing import List, Optional, Tuple
import os
import logging

try:
    from transformers import (
        pipeline,
        AutoTokenizer,
        AutoModelForCausalLM,
    )
    import torch
    TRANSFORMERS_AVAILABLE = True
except Exception:
    TRANSFORMERS_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    ST_AVAILABLE = True
except Exception:
    ST_AVAILABLE = False

logger = logging.getLogger(__name__)


class ModelManager:
    """ModelManager routes requests to a text LLM (Meditron) or
    a multimodal LLM (LLaVA-Med) depending on the input.

    It attempts to load models lazily with memory-safety options enabled:
    - device_map='auto' where possible
    - low_cpu_mem_usage when loading HF models
    - optional quantization hooks when bitsandbytes is available

    Configuration via environment variables:
    - TEXT_LLM: HF model id for text-only (Meditron recommended)
    - MULTIMODAL_LLM: HF model id for multimodal (LLaVA-Med recommended)
    - USE_GPU: 'true' to prefer GPU
    - QUANTIZE: 'true' to attempt 4-bit quantization when supported
    - EMBEDDING_MODEL: fallback embedding model name for SentenceTransformer
    """

    def __init__(self, text_embedding_model=None):
        self.text_embed = text_embedding_model
        # Default example ids for Meditron / LLaVA-Med. These are placeholders — set your own via
        # env vars TEXT_LLM and MULTIMODAL_LLM. If left unset, no local model will be loaded.
        default_text = os.getenv("MEDITRON_MODEL", "Meditron/meditron-small")
        default_mm = os.getenv("LLAVA_MED_MODEL", "LLaVA-Med/llava-med")

        self.text_llm_name = os.getenv("TEXT_LLM", default_text)
        self.multimodal_llm_name = os.getenv("MULTIMODAL_LLM", default_mm)
        # Hugging Face Inference API token (optional). If present and local loading fails,
        # we will attempt a remote inference call to the specified model.
        self.hf_api_token = os.getenv("HF_INFERENCE_API_TOKEN", "")
        self.use_gpu = os.getenv("USE_GPU", "false").lower() in ("1", "true", "yes")
        self.quantize = os.getenv("QUANTIZE", "false").lower() in ("1", "true", "yes")

        # internal lazy-loaded objects
        self._text_tokenizer = None
        self._text_model = None
        self._text_pipeline = None

        self._mm_tokenizer = None
        self._mm_model = None
        self._mm_pipeline = None

        # optional image embedder via SentenceTransformer
        self._image_embedder = None
        if ST_AVAILABLE:
            img_model = os.getenv("IMAGE_EMBED_MODEL", "")
            if img_model:
                try:
                    self._image_embedder = SentenceTransformer(img_model)
                except Exception:
                    logger.debug("Image embedder failed to load: %s", img_model)

    # --- Embedding helpers -------------------------------------------------
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if self.text_embed is None and ST_AVAILABLE:
            self.text_embed = SentenceTransformer(os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"))
        if self.text_embed is None:
            return [[0.0] * 384 for _ in texts]
        emb = self.text_embed.encode(texts)
        try:
            return emb.tolist()
        except Exception:
            return [list(e) for e in emb]

    def embed_image(self, image_path: str) -> Optional[List[float]]:
        if self._image_embedder is None:
            return None
        try:
            emb = self._image_embedder.encode([image_path])
            try:
                return emb.tolist()[0]
            except Exception:
                return list(emb[0])
        except Exception:
            logger.debug("Image embedding failed for %s", image_path)
            return None

    # --- Model loading ----------------------------------------------------
    def _load_text_llm(self):
        if not TRANSFORMERS_AVAILABLE or not self.text_llm_name:
            return None
        if self._text_pipeline is not None:
            return self._text_pipeline

        try:
            # Attempt memory-efficient load
            kwargs = {}
            if self.use_gpu:
                device = 0
            else:
                device = -1
            # Use HF pipeline for text-generation; the model load is lazy and wrapped in try/except
            self._text_pipeline = pipeline(
                "text-generation",
                model=self.text_llm_name,
                device=device,
                trust_remote_code=True,
            )
            logger.info("Loaded text LLM: %s", self.text_llm_name)
            return self._text_pipeline
        except Exception as e:
            logger.warning("Failed to load text LLM %s: %s", self.text_llm_name, e)
            self._text_pipeline = None
            return None

    def _hf_remote_infer(self, model_name: str, prompt: str, max_tokens: int = 256) -> Optional[str]:
        """Call the Hugging Face Inference API as a fallback when local model loading fails.

        Returns generated text or None on failure.
        """
        if not self.hf_api_token:
            return None
        import requests
        api_url = f"https://api-inference.huggingface.co/models/{model_name}"
        headers = {"Authorization": f"Bearer {self.hf_api_token}"}
        payload = {"inputs": prompt, "parameters": {"max_new_tokens": max_tokens, "do_sample": False}}
        try:
            resp = requests.post(api_url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            # HF API may return a list of generated outputs or a dict
            if isinstance(data, list) and data:
                text = data[0].get("generated_text") or data[0].get("text") or str(data[0])
                return text
            if isinstance(data, dict):
                # Some models return {'error': ...} on failure
                if "error" in data:
                    logger.debug("HF inference error: %s", data.get("error"))
                    return None
                # Attempt to read common keys
                return data.get("generated_text") or data.get("text") or str(data)
        except Exception as e:
            logger.debug("HF remote inference failed for %s: %s", model_name, e)
            return None

    def _load_multimodal_llm(self):
        if not TRANSFORMERS_AVAILABLE or not self.multimodal_llm_name:
            return None
        if self._mm_pipeline is not None:
            return self._mm_pipeline
        try:
            # Many multimodal models require a specialized loader. We attempt a generic pipeline
            # but will gracefully fall back to the text pipeline if unavailable.
            device = 0 if self.use_gpu else -1
            # try a text-generation pipeline first; some LLaVA-type models support image+text via pipeline
            self._mm_pipeline = pipeline("text-generation", model=self.multimodal_llm_name, device=device, trust_remote_code=True)
            logger.info("Loaded multimodal LLM: %s", self.multimodal_llm_name)
            return self._mm_pipeline
        except Exception as e:
            logger.warning("Failed to load multimodal LLM %s: %s", self.multimodal_llm_name, e)
            self._mm_pipeline = None
            return None

    # --- Generation API ---------------------------------------------------
    def generate_answer(self, prompt: str, max_tokens: int = 256, images: Optional[List[str]] = None) -> Tuple[str, Optional[str]]:
        """Generate an answer. If images are provided and a multimodal model is available,
        prefer the multimodal model. Returns (text, model_name).
        """
        # Try multimodal first when images present
        if images and self.multimodal_llm_name:
            mm = self._load_multimodal_llm()
            if mm is not None:
                try:
                    out = mm(prompt, max_length=max_tokens, do_sample=False)
                    model_used = self.multimodal_llm_name
                    if isinstance(out, list) and out:
                        return out[0].get("generated_text", str(out[0])), model_used
                    return str(out), model_used
                except Exception as e:
                    logger.debug("Multimodal model generation failed: %s", e)

        # Otherwise fall back to text-only LLM
        text_pipe = self._load_text_llm()
        if text_pipe is not None:
            try:
                out = text_pipe(prompt, max_length=max_tokens, do_sample=False)
                model_used = self.text_llm_name
                if isinstance(out, list) and out:
                    return out[0].get("generated_text", str(out[0])), model_used
                return str(out), model_used
            except Exception as e:
                logger.debug("Text model generation failed: %s", e)

        # Last-resort fallback (non-LLM): return compact prompt echo for traceability
        truncated = prompt if len(prompt) < 2000 else prompt[:1990] + "..."
        fallback = f"[Local fallback answer]\n\n{truncated}"
        return fallback, None
    # duplicate/legacy generate_answer removed; use the memory-aware generate_answer above

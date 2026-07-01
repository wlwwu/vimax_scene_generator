# https://platform.minimaxi.com/docs/guides/image-generation

import asyncio
import logging
import aiohttp
from typing import List, Optional
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from utils.retry import after_func
from utils.image import image_path_to_b64
from interfaces.image_output import ImageOutput


class ImageGeneratorMiniMaxAPI:
    def __init__(
        self,
        api_key: str,
        model: str = "image-01",
        base_url: str = "https://api.minimaxi.com/v1/image_generation",
        rate_limiter=None,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.rate_limiter = rate_limiter

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=30),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        reraise=True,
        after=after_func,
    )
    async def generate_single_image(
        self,
        prompt: str,
        reference_image_paths: List[str] = [],
        aspect_ratio: Optional[str] = "16:9",
        **kwargs,
    ) -> ImageOutput:
        logging.info(f"Calling MiniMax {self.model} to generate image...")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio if aspect_ratio else "16:9",
            "response_format": "url",
        }

        # Add subject reference if reference images are provided
        if reference_image_paths:
            # MiniMax supports one reference image for character consistency
            image_b64 = image_path_to_b64(reference_image_paths[0], mime=True)
            payload["subject_reference"] = [
                {
                    "type": "character",
                    "image_file": image_b64,
                }
            ]

        response_json = await self._post_request(headers, payload)

        # If content moderation triggered and we have reference images, retry without them
        base_resp = response_json.get("base_resp", {})
        if base_resp.get("status_code") == 1026 and reference_image_paths:
            logging.warning("MiniMax content moderation triggered with reference image, retrying without reference...")
            payload.pop("subject_reference", None)
            response_json = await self._post_request(headers, payload)

        # If still triggered, retry with sanitized prompt (remove potentially sensitive words)
        base_resp = response_json.get("base_resp", {})
        if base_resp.get("status_code") == 1026:
            logging.warning("MiniMax content moderation triggered on prompt, retrying with sanitized prompt...")
            import re
            sanitized = re.sub(
                r'\b(bra|bikini|lingerie|underwear|naked|nude|sexy|seductive|sensual)\b',
                'top',
                payload["prompt"],
                flags=re.IGNORECASE,
            )
            payload["prompt"] = sanitized
            response_json = await self._post_request(headers, payload)

        return self._parse_response(response_json)

    async def _post_request(self, headers, payload):
        async with aiohttp.ClientSession() as session:
            async with session.post(self.base_url, json=payload, headers=headers) as response:
                response_json = await response.json()
                if response.status >= 400:
                    raise RuntimeError(
                        f"MiniMax image generation failed with HTTP {response.status}: {response_json}"
                    )
        return response_json

    def _parse_response(self, response_json):
        # Check base_resp for errors
        base_resp = response_json.get("base_resp", {})
        if base_resp.get("status_code", 0) != 0:
            raise RuntimeError(f"MiniMax image generation error: {base_resp}")

        # Response format: {"data": {"image_urls": [...]}} for url
        # or {"data": {"image_base64": [...]}} for base64
        data = response_json.get("data") or {}
        if "image_urls" in data and data["image_urls"]:
            url = data["image_urls"][0]
            return ImageOutput(fmt="url", ext="jpeg", data=url)
        elif "image_url" in data and data["image_url"]:
            url = data["image_url"][0]
            return ImageOutput(fmt="url", ext="jpeg", data=url)
        elif "image_base64" in data and data["image_base64"]:
            b64 = data["image_base64"][0]
            return ImageOutput(fmt="b64", ext="jpeg", data=b64)
        else:
            # Check if it's a silent content moderation block (success but no images)
            metadata = response_json.get("metadata", {})
            if metadata.get("failed_count", "0") != "0":
                raise RuntimeError(f"MiniMax image generation content blocked (no images returned): {response_json}")
            raise RuntimeError(f"Unexpected MiniMax response format: {response_json}")

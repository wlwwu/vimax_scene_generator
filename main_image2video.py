"""
Generate a video from person image + street/scene image.
Uses MiniMax-M3 vision to describe the scene, MiniMax image-01 to composite,
and Doubao Seedance to animate.

Usage:
    python main_image2video.py --person <person.jpg> --scene <street.jpg> [--prompt "额外描述"]
    python main_image2video.py --person <person.jpg> --prompt "场景描述"  # text-only scene
"""
import asyncio
import argparse
import base64
import os
import yaml

from openai import AsyncOpenAI
from tools.image_generator_minimax_api import ImageGeneratorMiniMaxAPI
from tools.video_generator_doubao_seedance_yunwu_api import VideoGeneratorDoubaoSeedanceYunwuAPI

# Ensure SSL certs work behind corporate proxy
os.environ.setdefault("SSL_CERT_FILE", "/etc/ssl/certs/ca-certificates.crt")
os.environ.setdefault("REQUESTS_CA_BUNDLE", "/etc/ssl/certs/ca-certificates.crt")


async def describe_scene_image(client: AsyncOpenAI, image_path: str) -> str:
    """Use MiniMax-M3 vision to describe a scene image in detail."""
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    ext = os.path.splitext(image_path)[1].lower().lstrip(".")
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
            "webp": "image/webp", "gif": "image/gif"}.get(ext, "image/jpeg")

    response = await client.chat.completions.create(
        model="MiniMax-M3",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}"},
                    },
                    {
                        "type": "text",
                        "text": (
                            "Describe this scene/location image in vivid detail for an image generation prompt. "
                            "Focus on: environment, architecture, lighting, weather, colors, atmosphere, "
                            "and spatial layout. Do NOT mention any people. "
                            "Output a single English paragraph, ~100 words."
                        ),
                    },
                ],
            }
        ],
        max_tokens=300,
    )
    return response.choices[0].message.content.strip()


async def main(
    person_path: str,
    scene_path: str | None = None,
    prompt: str = "",
    output_dir: str = ".working_dir/image2video",
):
    with open("configs/idea2video.yaml", "r") as f:
        config = yaml.safe_load(f)

    os.makedirs(output_dir, exist_ok=True)

    llm_cfg = config["chat_model"]["init_args"]
    img_cfg = config["image_generator"]["init_args"]
    video_cfg = config["video_generator"]["init_args"]

    # 1. Build the scene prompt
    if scene_path:
        print("👁️ Describing scene image with MiniMax-M3 vision...")
        client = AsyncOpenAI(api_key=llm_cfg["api_key"], base_url=llm_cfg["base_url"])
        scene_description = await describe_scene_image(client, scene_path)
        print(f"   Scene description: {scene_description}")
        # Combine: scene description + any extra user prompt
        composite_prompt = f"This person is in the scene: {scene_description}"
        if prompt:
            composite_prompt += f" {prompt}"
    else:
        composite_prompt = prompt

    print(f"📝 Composite prompt: {composite_prompt}")

    # 2. Generate blended image (person composited into scene)
    print("🖼️ Generating composite image (person + scene)...")
    image_gen = ImageGeneratorMiniMaxAPI(api_key=img_cfg["api_key"])
    blended_image = await image_gen.generate_single_image(
        prompt=composite_prompt,
        reference_image_paths=[person_path],
        aspect_ratio="16:9",
    )
    first_frame_path = os.path.join(output_dir, "first_frame.png")
    blended_image.save(first_frame_path)
    print(f"✅ Composite image saved to {first_frame_path}")

    # 3. Generate video from the composite image
    print("🎬 Generating video from composite image...")
    video_gen = VideoGeneratorDoubaoSeedanceYunwuAPI(
        api_key=video_cfg["api_key"],
        ff2v_model=video_cfg.get("ff2v_model", "doubao-seedance-1-0-pro-fast-251015"),
    )
    video_prompt = composite_prompt + ", natural movement, cinematic"
    video_output = await video_gen.generate_single_video(
        prompt=video_prompt,
        reference_image_paths=[first_frame_path],
        resolution="1080p",
        duration=5,
    )
    video_path = os.path.join(output_dir, "output_video.mp4")
    video_output.save(video_path)
    print(f"✅ Video saved to {video_path}")
    return first_frame_path, video_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate video from person + scene images")
    parser.add_argument("--person", required=True, help="Path to the person image")
    parser.add_argument("--scene", default=None, help="Path to the street/scene image (optional)")
    parser.add_argument("--prompt", default="", help="Extra scene description (optional if --scene provided)")
    parser.add_argument("--output", default=".working_dir/image2video", help="Output directory")
    args = parser.parse_args()

    if not args.scene and not args.prompt:
        parser.error("Provide at least --scene or --prompt")

    asyncio.run(main(
        person_path=args.person,
        scene_path=args.scene,
        prompt=args.prompt,
        output_dir=args.output,
    ))

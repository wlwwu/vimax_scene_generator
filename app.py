"""
ViMax Scene Video Generator — Gradio Web UI

Tabs:
  1. Generate Video: User uploads person photo, picks a scene → walking video
  2. Manage Scenes: Admin adds/removes scene locations (with photos)
  3. History: View past generations

Launch:
    python app.py
"""
import asyncio
import base64
import os
import shutil
import time
import yaml
import gradio as gr

from openai import AsyncOpenAI
from scene_db import (
    add_scene, list_scenes, get_scene, get_scene_by_name,
    delete_scene, update_scene_description,
    log_generation, update_generation, list_generations,
    SCENES_DIR,
)
from tools.image_generator_minimax_api import ImageGeneratorMiniMaxAPI
from tools.video_generator_doubao_seedance_yunwu_api import VideoGeneratorDoubaoSeedanceYunwuAPI

# Ensure SSL certs work behind corporate proxy
os.environ.setdefault("SSL_CERT_FILE", "/etc/ssl/certs/ca-certificates.crt")
os.environ.setdefault("REQUESTS_CA_BUNDLE", "/etc/ssl/certs/ca-certificates.crt")

CONFIG_PATH = "configs/idea2video.yaml"


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


# ═══════════════════════════════════════════════════════════════════════════════
# WORKFLOW ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

async def describe_scene_with_vision(client: AsyncOpenAI, image_path: str) -> str:
    """Use MiniMax-M3 vision to describe a scene image."""
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    ext = os.path.splitext(image_path)[1].lower().lstrip(".")
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
            "webp": "image/webp"}.get(ext, "image/jpeg")

    response = await client.chat.completions.create(
        model="MiniMax-M3",
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                {"type": "text", "text": (
                    "Describe this scene/location in vivid detail for image generation. "
                    "Focus on: environment, architecture, lighting, colors, atmosphere. "
                    "Do NOT mention any people. Output a single English paragraph, ~60 words max."
                )},
            ],
        }],
        max_tokens=300,
    )
    return response.choices[0].message.content.strip()


async def generate_walking_video(
    person_image_path: str,
    scene_id: int,
    action: str = "walking naturally",
    duration: int = 5,
) -> tuple[str, str, str]:
    """
    Full pipeline: person + scene → composite → video.
    Returns (composite_path, video_path, prompt_used).
    """
    config = load_config()
    scene = get_scene(scene_id)
    if not scene:
        raise ValueError(f"Scene {scene_id} not found")

    llm_cfg = config["chat_model"]["init_args"]
    img_cfg = config["image_generator"]["init_args"]
    video_cfg = config["video_generator"]["init_args"]

    # Step 1: Get scene description (use cached or generate fresh)
    if scene["description"]:
        scene_description = scene["description"]
    else:
        client = AsyncOpenAI(api_key=llm_cfg["api_key"], base_url=llm_cfg["base_url"])
        scene_description = await describe_scene_with_vision(client, scene["image_path"])
        # Cache it for next time
        update_scene_description(scene_id, scene_description)

    # Step 2: Build composite prompt (MiniMax limit: 1500 chars)
    scene_desc_truncated = scene_description[:800]
    composite_prompt = (
        f"A person {action} in this scene: {scene_desc_truncated}. "
        f"Full body shot, natural pose, street photography, cinematic lighting."
    )
    if len(composite_prompt) > 1450:
        composite_prompt = composite_prompt[:1450]

    # Step 3: Generate composite image
    timestamp = int(time.time())
    output_dir = f"outputs/{timestamp}"
    os.makedirs(output_dir, exist_ok=True)

    image_gen = ImageGeneratorMiniMaxAPI(api_key=img_cfg["api_key"])
    blended = await image_gen.generate_single_image(
        prompt=composite_prompt,
        reference_image_paths=[person_image_path],
        aspect_ratio="16:9",
    )
    composite_path = os.path.join(output_dir, "composite.png")
    blended.save(composite_path)

    # Step 4: Generate walking video
    video_gen = VideoGeneratorDoubaoSeedanceYunwuAPI(
        api_key=video_cfg["api_key"],
        ff2v_model=video_cfg.get("ff2v_model", "doubao-seedance-1-0-pro-fast-251015"),
    )
    video_prompt = (
        f"A person {action}, {scene_desc_truncated[:400]}, "
        f"natural movement, smooth gait, cinematic"
    )
    video_output = await video_gen.generate_single_video(
        prompt=video_prompt,
        reference_image_paths=[composite_path],
        resolution="1080p",
        duration=duration,
    )
    video_path = os.path.join(output_dir, "walking_video.mp4")
    video_output.save(video_path)

    return composite_path, video_path, composite_prompt


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: GENERATE VIDEO
# ═══════════════════════════════════════════════════════════════════════════════

def get_scene_choices():
    """Return scene names for the dropdown."""
    scenes = list_scenes()
    return [s["name"] for s in scenes]


def get_scene_preview(scene_name):
    """Return the scene image for preview."""
    if not scene_name:
        return None
    scene = get_scene_by_name(scene_name)
    if scene and os.path.exists(scene["image_path"]):
        return scene["image_path"]
    return None


def run_generate(person_img, scene_name, action, duration, progress=gr.Progress()):
    if person_img is None:
        return None, None, "❌ Please upload a person photo."
    if not scene_name:
        return None, None, "❌ Please select a scene."

    scene = get_scene_by_name(scene_name)
    if not scene:
        return None, None, f"❌ Scene '{scene_name}' not found in database."

    # Save person image
    person_dir = "uploads/persons"
    os.makedirs(person_dir, exist_ok=True)
    person_save = os.path.join(person_dir, f"{int(time.time())}_{os.path.basename(person_img)}")
    shutil.copy2(person_img, person_save)

    # Log generation
    gen_id = log_generation(scene["id"], person_save)

    progress(0.1, desc="Starting generation pipeline...")
    try:
        composite_path, video_path, prompt_used = asyncio.run(
            generate_walking_video(
                person_image_path=person_save,
                scene_id=scene["id"],
                action=action if action else "walking naturally",
                duration=int(duration),
            )
        )
        update_generation(gen_id, "done", composite_path, video_path, prompt_used)
        progress(1.0, desc="Done!")
        return composite_path, video_path, f"✅ Video generated! Scene: {scene_name}"
    except Exception as e:
        update_generation(gen_id, "failed", prompt_used=str(e))
        return None, None, f"❌ Error: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: MANAGE SCENES
# ═══════════════════════════════════════════════════════════════════════════════

def add_new_scene(name, image, category, description):
    if not name or not name.strip():
        return "❌ Please enter a scene name.", refresh_scene_table()
    if image is None:
        return "❌ Please upload a scene image.", refresh_scene_table()

    # Save image to assets/scenes/
    ext = os.path.splitext(image)[1] or ".jpg"
    safe_name = name.strip().replace(" ", "_").replace("/", "_")
    dest = os.path.join(SCENES_DIR, f"{safe_name}{ext}")
    shutil.copy2(image, dest)

    add_scene(
        name=name.strip(),
        image_path=dest,
        description=description.strip() if description else "",
        category=category or "street",
    )
    return f"✅ Scene '{name}' added!", refresh_scene_table()


def remove_scene(scene_name):
    if not scene_name:
        return "❌ Select a scene to delete.", refresh_scene_table()
    scene = get_scene_by_name(scene_name)
    if scene:
        delete_scene(scene["id"])
        return f"✅ Scene '{scene_name}' deleted.", refresh_scene_table()
    return f"❌ Scene '{scene_name}' not found.", refresh_scene_table()


def refresh_scene_table():
    scenes = list_scenes()
    if not scenes:
        return [["(no scenes)", "", "", ""]]
    return [[s["name"], s["category"], s["description"][:50] if s["description"] else "", s["image_path"]] for s in scenes]


def generate_description_for_scene(scene_name):
    """Use M3 vision to generate and cache a description for a scene."""
    if not scene_name:
        return "❌ Select a scene first."
    scene = get_scene_by_name(scene_name)
    if not scene:
        return "❌ Scene not found."

    config = load_config()
    llm_cfg = config["chat_model"]["init_args"]
    client = AsyncOpenAI(api_key=llm_cfg["api_key"], base_url=llm_cfg["base_url"])
    desc = asyncio.run(describe_scene_with_vision(client, scene["image_path"]))
    update_scene_description(scene["id"], desc)
    return f"✅ Description generated and cached:\n{desc}"


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3: HISTORY
# ═══════════════════════════════════════════════════════════════════════════════

def refresh_history():
    gens = list_generations(limit=20)
    if not gens:
        return [["(no history)", "", "", "", ""]]
    return [
        [g["scene_name"] or "?", g["status"], g["created_at"],
         g["video_path"] or "", g["prompt_used"][:80] if g["prompt_used"] else ""]
        for g in gens
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# BUILD UI
# ═══════════════════════════════════════════════════════════════════════════════

with gr.Blocks(title="ViMax - Scene Video Generator") as app:
    gr.Markdown("# 🎬 ViMax — Scene Walking Video Generator")
    gr.Markdown("Upload your photo, pick a location, and generate a walking video!")

    with gr.Tabs():
        # ── Tab 1: Generate Video ──
        with gr.TabItem("🎥 Generate Video"):
            with gr.Row():
                with gr.Column(scale=1):
                    person_input = gr.Image(label="📷 Your Photo (person)", type="filepath")
                    scene_dropdown = gr.Dropdown(
                        label="📍 Select Scene",
                        choices=get_scene_choices(),
                        interactive=True,
                    )
                    scene_preview = gr.Image(label="Scene Preview", interactive=False, height=200)
                    action_input = gr.Textbox(
                        label="Action (what the person is doing)",
                        value="walking naturally",
                        placeholder="e.g., walking, jogging, taking photos, strolling",
                    )
                    duration_input = gr.Dropdown(
                        label="Video Duration", choices=["5", "10"], value="5"
                    )
                    generate_btn = gr.Button("🚀 生成视频", variant="primary", size="lg")

                with gr.Column(scale=1):
                    composite_output = gr.Image(label="🖼️ Composite First Frame")
                    video_output = gr.Video(label="🎬 Walking Video")
                    status_output = gr.Textbox(label="Status", interactive=False)

            # Interactions
            scene_dropdown.change(fn=get_scene_preview, inputs=scene_dropdown, outputs=scene_preview)
            generate_btn.click(
                fn=run_generate,
                inputs=[person_input, scene_dropdown, action_input, duration_input],
                outputs=[composite_output, video_output, status_output],
            )

        # ── Tab 2: Manage Scenes ──
        with gr.TabItem("⚙️ Manage Scenes"):
            gr.Markdown("### Add / Remove Scene Locations")
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("**Add New Scene**")
                    new_name = gr.Textbox(label="Scene Name", placeholder="e.g., 平江路")
                    new_image = gr.Image(label="Scene Photo", type="filepath")
                    new_category = gr.Dropdown(
                        label="Category",
                        choices=["street", "park", "landmark", "indoor", "beach", "mountain"],
                        value="street",
                    )
                    new_desc = gr.Textbox(
                        label="Description (optional — auto-generated if empty)",
                        placeholder="Leave empty to auto-generate with AI vision",
                        lines=3,
                    )
                    add_btn = gr.Button("➕ Add Scene", variant="primary")
                    add_status = gr.Textbox(label="Status", interactive=False)

                with gr.Column(scale=1):
                    gr.Markdown("**Existing Scenes**")
                    scene_table = gr.Dataframe(
                        headers=["Name", "Category", "Description", "Image Path"],
                        value=refresh_scene_table(),
                        interactive=False,
                    )
                    with gr.Row():
                        del_dropdown = gr.Dropdown(
                            label="Select scene to delete",
                            choices=get_scene_choices(),
                        )
                        del_btn = gr.Button("🗑️ Delete", variant="stop")
                    with gr.Row():
                        desc_dropdown = gr.Dropdown(
                            label="Generate AI description for",
                            choices=get_scene_choices(),
                        )
                        desc_btn = gr.Button("🤖 Auto-Describe")
                    desc_result = gr.Textbox(label="Description Result", interactive=False, lines=3)

            add_btn.click(
                fn=add_new_scene,
                inputs=[new_name, new_image, new_category, new_desc],
                outputs=[add_status, scene_table],
            ).then(
                fn=lambda: gr.update(choices=get_scene_choices()),
                outputs=[scene_dropdown],
            ).then(
                fn=lambda: gr.update(choices=get_scene_choices()),
                outputs=[del_dropdown],
            ).then(
                fn=lambda: gr.update(choices=get_scene_choices()),
                outputs=[desc_dropdown],
            )

            del_btn.click(
                fn=remove_scene,
                inputs=[del_dropdown],
                outputs=[add_status, scene_table],
            ).then(
                fn=lambda: gr.update(choices=get_scene_choices()),
                outputs=[scene_dropdown],
            ).then(
                fn=lambda: gr.update(choices=get_scene_choices()),
                outputs=[del_dropdown],
            ).then(
                fn=lambda: gr.update(choices=get_scene_choices()),
                outputs=[desc_dropdown],
            )

            desc_btn.click(
                fn=generate_description_for_scene,
                inputs=[desc_dropdown],
                outputs=[desc_result],
            )

        # ── Tab 3: History ──
        with gr.TabItem("📜 History"):
            gr.Markdown("### Recent Generations")
            history_table = gr.Dataframe(
                headers=["Scene", "Status", "Created", "Video Path", "Prompt"],
                value=refresh_history(),
                interactive=False,
            )
            refresh_btn = gr.Button("🔄 Refresh")
            refresh_btn.click(fn=refresh_history, outputs=[history_table])


if __name__ == "__main__":
    app.launch(server_name="0.0.0.0", server_port=7861, share=False)

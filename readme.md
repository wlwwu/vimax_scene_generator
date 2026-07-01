# ViMax Scene Generator

## 🏗️ Architecture

### 📊 **System Overview**

**ViMax** is a multi-agent video framework that enables automated multi-shot video generation while ensuring character and scene consistency. Our system seamlessly translates your ideas into corresponding videos, allowing you to focus on storytelling rather than technical implementation.

🎯 **Technical Capabilities**:

🧬 **Intelligent Long Script Generation**

RAG-based long script design engine that intelligently analyzes lengthy, novel-like stories and automatically segments them into a multi-scene script format. The process meticulously ensures that all key plot developments and character dialogues are accurately retained within the new structure.

🪄 **Expressive Storyboard Design**

Shot-level storyboard design system that create expressive storyboards through cinematography language based on user requirements and target audiences, which establishes the narrative rhythm for subsequent video generation.

🔮 **Multi-camera Filming Simulation**

Simulates multi-camera filming to deliver an immersive viewing experience while maintaining consistent character positioning and backgrounds within the same scene.

🧸 **Intelligent Reference Images Selection**

Intelligently select the reference image required for the first frame of the current video, including the storyboards that occurred in the previous timeline, to ensure the accuracy of multiple characters and environmental elements as the video becomes longer.

⚙️ **Automated Images Generation**

Based on the selected reference image and the visual logical order on the previous timeline, the prompt of the image generator is automatically generated to reasonably arrange the spatial interaction position between the character and the environment.

✅ **Automated Image Generation Consistency Check**

Generate multiple images in parallel and select the best consistent image as the first frame through MLLM/VLM to imitate the workflow of human creators.

⚡ **High-efficiency Parallel Shot Generation**

Parallel processing for sequential shots captured from the same camera enables highly efficient video production.

### 🤖 **Multi-Agent Video Generation Pipeline**

<div align="center">
  <table align="center" width="100%" style="border: none; border-collapse: collapse;">
    <tr>
      <td colspan="3" align="center" style="padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; color: white; font-weight: bold;">
        🧠 <strong>INPUT LAYER</strong><br/>
        📝 Idea & Scripts & Novels • 💭 Natural Language Prompts • 🖼️ Reference Images • 🎨 Style Directives • 🧩 Configs
      </td>
    </tr>
    <tr><td colspan="3" height="20"></td></tr>
    <tr>
      <td colspan="3" align="center" style="padding: 15px; background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); border-radius: 12px; color: white; font-weight: bold;">
        🧭 <strong>CENTRAL ORCHESTRATION</strong><br/>
        Agent Scheduling • Stage Transitions • Resource Management • Retry/Fallback Logic
      </td>
    </tr>
    <tr><td colspan="3" height="15"></td></tr>
    <tr>
      <td align="center" style="padding: 12px; background: linear-gradient(135deg, #3742fa 0%, #2f3542 100%); border-radius: 10px; color: white; width: 50%;">
        🧾 <strong>SCRIPT UNDERSTANDING</strong><br/>
        <small>Character/Environment Extraction • Scene Boundaries • Style Intent</small>
      </td>
      <td width="10"></td>
      <td align="center" style="padding: 12px; background: linear-gradient(135deg, #8c7ae6 0%, #9c88ff 100%); border-radius: 10px; color: white; width: 50%;">
        🎥 <strong>SCENE & SHOT PLANNING</strong><br/>
        <small>Storyboard Steps • Shot List • Key Frames & Beats</small>
      </td>
    </tr>
    <tr><td colspan="3" height="15"></td></tr>
    <tr>
      <td colspan="3" align="center" style="padding: 15px; background: linear-gradient(135deg, #00d2d3 0%, #54a0ff 100%); border-radius: 12px; color: white; font-weight: bold;">
        🧪 <strong>VISUAL ASSET PLANNING</strong><br/>
        Reference Image Selection • Look/Style Guidance • Prompt Conditioning
      </td>
    </tr>
    <tr><td colspan="3" height="15"></td></tr>
    <tr>
      <td align="center" style="padding: 12px; background: linear-gradient(135deg, #e056fd 0%, #f368e0 100%); border-radius: 10px; color: white; width: 50%;">
        🗂️ <strong>ASSET INDEXING</strong><br/>
        <small>Frames/Refs Catalog • Embeddings • Retrieval for Reuse</small>
      </td>
      <td width="10"></td>
      <td align="center" style="padding: 12px; background: linear-gradient(135deg, #ffa726 0%, #ff7043 100%); border-radius: 10px; color: white; width: 50%;">
        ♻️ <strong>CONSISTENCY & CONTINUITY</strong><br/>
        <small>Character/Environment Tracking • Ref Matching • Temporal Coherence</small>
      </td>
    </tr>
    <tr><td colspan="3" height="15"></td></tr>
    <tr>
      <td colspan="3" align="center" style="padding: 15px; background: linear-gradient(135deg, #26de81 0%, #20bf6b 100%); border-radius: 12px; color: white; font-weight: bold;">
        ✂️ <strong>VISUAL SYNTHESIS & ASSEMBLY</strong><br/>
        Image Generation • Best-Frame Selection • First/Last-Frame→Video • Cut & Timeline Assembly
      </td>
    </tr>
    <tr><td colspan="3" height="15"></td></tr>
    <tr>
      <td colspan="3" align="center" style="padding: 20px; background: linear-gradient(135deg, #045de9 0%, #09c6f9 100%); border-radius: 15px; color: white; font-weight: bold;">
        🚀 <strong>OUTPUT LAYER</strong><br/>
        🖼️ Frames • 🎞️ Clips & Final Videos • 📜 Logs • 📦 Working Directory Artifacts
      </td>
    </tr>
  </table>
</div>

---

## 🚀 Quick Start

### 📥 **Install**

```bash
git clone https://github.com/wlwwu/vimax_scene_generator.git
cd vimax_scene_generator
uv sync
```

### ⚙️ **Configuration**

Copy the example config and fill in your API keys:

```bash
cp configs/agent.example.yaml configs/agent.local.yaml
```

Edit `configs/agent.local.yaml`:

```yaml
llm:
  model_provider: openai          # openai | minimax
  model: <YOUR_LLM_MODEL>        # e.g. gpt-5.5, MiniMax-M3
  base_url: <YOUR_LLM_BASE_URL>
  api_key: <YOUR_API_KEY>

image:
  model: <YOUR_IMAGE_MODEL>       # e.g. gemini-3.1-flash-image-preview
  base_url: <YOUR_IMAGE_BASE_URL>
  api_key: <YOUR_API_KEY>

video:
  model: <YOUR_VIDEO_MODEL>       # e.g. veo3.1-fast
  base_url: <YOUR_VIDEO_BASE_URL>
  api_key: <YOUR_API_KEY>
```

You can also provide API keys through environment variables:

| Variable | Purpose |
|----------|---------|
| `VIMAX_LLM_API_KEY` | LLM provider key |
| `VIMAX_IMAGE_API_KEY` | Image generator key |
| `VIMAX_VIDEO_API_KEY` | Video generator key |

### 🖥️ **Start the UI**

Launch the Gradio web interface:

```bash
uv run python app.py
```

The UI provides scene management, person image upload, and video generation history.

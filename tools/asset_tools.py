"""
Asset generation tools for the Asset Coordinator agent.

- Sprites: Stable Diffusion via ComfyUI REST API (local GPU)
- Music: Suno API
- SFX: ElevenLabs Sound Effects API
- Manifest: JSON file mapping asset names to file paths
"""
import base64
import json
import os
import time
import uuid
from pathlib import Path

import requests
from crewai.tools import tool
from dotenv import load_dotenv

load_dotenv()

COMFYUI_URL = os.getenv("STABLE_DIFFUSION_URL", "http://localhost:8188")
SD_STYLE_PREFIX = os.getenv(
    "SD_STYLE_PREFIX",
    "pixel art, 32x32, sci-fi space station, dark palette, neon accents",
)
SD_MODEL = os.getenv("SD_MODEL_CHECKPOINT", "PixelartSpritesheet_V.1.ckpt")
SUNO_API_KEY = os.getenv("SUNO_API_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
PROJECT_PATH = Path(os.getenv("GODOT_PROJECT_PATH", "parsec_zero"))
MANIFEST_PATH = PROJECT_PATH / "assets" / "manifest.json"


def _load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text())
    return {"sprites": {}, "music": {}, "sfx": {}}


def _save_manifest(manifest: dict) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))


def _build_comfyui_workflow(prompt: str, negative_prompt: str, width: int, height: int, filename_prefix: str) -> dict:
    """Build a basic ComfyUI txt2img workflow JSON."""
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": SD_MODEL}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": negative_prompt, "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "seed": int(time.time()),
                "steps": 20,
                "cfg": 7.5,
                "sampler_name": "dpmpp_2m",
                "scheduler": "karras",
                "denoise": 1.0,
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["4", 0],
            },
        },
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": filename_prefix, "images": ["6", 0]},
        },
    }


@tool("Generate pixel art sprite via ComfyUI")
def generate_sprite(asset_name: str, description: str, width: int = 512, height: int = 512) -> str:
    """
    Generate a pixel art sprite using Stable Diffusion via ComfyUI (local GPU).
    The style prefix is automatically prepended to ensure visual consistency.
    The image is saved to res://assets/sprites/<asset_name>.png.

    Args:
        asset_name: Filename without extension (e.g. "player_idle", "enemy_drone")
        description: What to generate (e.g. "humanoid maintenance drone, front-facing")
        width: Image width in pixels (default 512, downsampled to 32 in Godot)
        height: Image height in pixels (default 512)

    Returns the saved file path or an error message.
    """
    full_prompt = f"{SD_STYLE_PREFIX}, {description}, no background, centered sprite"
    negative_prompt = "blurry, realistic, 3d, photo, watermark, text, ui elements"
    client_id = str(uuid.uuid4())

    workflow = _build_comfyui_workflow(full_prompt, negative_prompt, width, height, asset_name)

    try:
        # Submit workflow
        resp = requests.post(
            f"{COMFYUI_URL}/prompt",
            json={"prompt": workflow, "client_id": client_id},
            timeout=30,
        )
        resp.raise_for_status()
        prompt_id = resp.json()["prompt_id"]

        # Poll for completion
        for _ in range(120):
            time.sleep(2)
            history = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=10).json()
            if prompt_id in history:
                outputs = history[prompt_id]["outputs"]
                for node_output in outputs.values():
                    if "images" in node_output:
                        image_info = node_output["images"][0]
                        image_resp = requests.get(
                            f"{COMFYUI_URL}/view",
                            params={"filename": image_info["filename"], "subfolder": image_info.get("subfolder", ""), "type": image_info["type"]},
                            timeout=30,
                        )
                        out_path = PROJECT_PATH / "assets" / "sprites" / f"{asset_name}.png"
                        out_path.parent.mkdir(parents=True, exist_ok=True)
                        out_path.write_bytes(image_resp.content)
                        manifest = _load_manifest()
                        manifest["sprites"][asset_name] = f"res://assets/sprites/{asset_name}.png"
                        _save_manifest(manifest)
                        return f"OK: Sprite saved to {out_path}. Manifest updated."

        return "ERROR: ComfyUI generation timed out after 4 minutes."

    except requests.exceptions.ConnectionError:
        return (
            f"ERROR: Cannot connect to ComfyUI at {COMFYUI_URL}. "
            "Is ComfyUI running? Start it with: python C:/users/scott/comfyui/main.py"
        )
    except Exception as e:
        return f"ERROR: Sprite generation failed: {e}"

    except requests.exceptions.ConnectionError:
        return (
            "ERROR: Cannot connect to Stable Diffusion at "
            f"{SD_URL}. Is Automatic1111 running?"
        )
    except Exception as e:
        return f"ERROR: Sprite generation failed: {e}"


@tool("Generate background music via Suno API")
def generate_music(track_name: str, description: str, duration_seconds: int = 60) -> str:
    """
    Generate ambient background music using the Suno API.
    Audio is saved to res://assets/audio/music/<track_name>.wav.

    Args:
        track_name: Filename without extension (e.g. "level_1_ambient")
        description: Music style description (e.g. "dark ambient, sci-fi, tension, slow pulse")
        duration_seconds: Target duration

    Returns the saved file path or an error.
    """
    if not SUNO_API_KEY:
        return "ERROR: SUNO_API_KEY not set in .env"

    headers = {"Authorization": f"Bearer {SUNO_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "prompt": description,
        "duration": duration_seconds,
        "make_instrumental": True,
    }

    try:
        resp = requests.post(
            "https://api.suno.ai/v1/generate",
            json=payload,
            headers=headers,
            timeout=300,
        )
        resp.raise_for_status()
        data = resp.json()

        # Poll for completion
        task_id = data.get("id") or data.get("task_id")
        for _ in range(60):
            time.sleep(5)
            poll = requests.get(
                f"https://api.suno.ai/v1/generate/{task_id}",
                headers=headers,
                timeout=30,
            )
            poll_data = poll.json()
            if poll_data.get("status") == "complete":
                audio_url = poll_data["audio_url"]
                audio_resp = requests.get(audio_url, timeout=60)
                out_path = PROJECT_PATH / "assets" / "audio" / "music" / f"{track_name}.wav"
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_bytes(audio_resp.content)
                manifest = _load_manifest()
                manifest["music"][track_name] = f"res://assets/audio/music/{track_name}.wav"
                _save_manifest(manifest)
                return f"OK: Music saved to {out_path}. Manifest updated."

        return "ERROR: Suno generation timed out after 5 minutes."

    except Exception as e:
        return f"ERROR: Music generation failed: {e}"


@tool("Generate sound effect via ElevenLabs")
def generate_sfx(sfx_name: str, description: str) -> str:
    """
    Generate a sound effect using the ElevenLabs Sound Effects API.
    Audio is saved to res://assets/audio/sfx/<sfx_name>.wav.

    Args:
        sfx_name: Filename without extension (e.g. "footstep_metal", "door_hiss")
        description: SFX description (e.g. "metallic footstep on grated floor")

    Returns the saved file path or an error.
    """
    if not ELEVENLABS_API_KEY:
        return "ERROR: ELEVENLABS_API_KEY not set in .env"

    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {"text": description, "duration_seconds": 2.0, "prompt_influence": 0.3}

    try:
        resp = requests.post(
            "https://api.elevenlabs.io/v1/sound-generation",
            json=payload,
            headers=headers,
            timeout=60,
        )
        resp.raise_for_status()

        out_path = PROJECT_PATH / "assets" / "audio" / "sfx" / f"{sfx_name}.wav"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(resp.content)

        manifest = _load_manifest()
        manifest["sfx"][sfx_name] = f"res://assets/audio/sfx/{sfx_name}.wav"
        _save_manifest(manifest)

        return f"OK: SFX saved to {out_path}. Manifest updated."

    except Exception as e:
        return f"ERROR: SFX generation failed: {e}"


@tool("Read asset manifest")
def read_asset_manifest() -> str:
    """
    Read the current asset manifest (res://assets/manifest.json).
    The Developer agent uses this to find file paths for sprites and audio
    when wiring assets into scenes.

    Returns the manifest as a formatted JSON string.
    """
    if not MANIFEST_PATH.exists():
        return '{"sprites": {}, "music": {}, "sfx": {}}'
    return json.dumps(_load_manifest(), indent=2)


@tool("Update asset manifest entry")
def update_asset_manifest(asset_type: str, asset_name: str, res_path: str) -> str:
    """
    Manually add or update an entry in the asset manifest.
    Use this when adding manually placed assets.

    Args:
        asset_type: "sprites", "music", or "sfx"
        asset_name: Key name (e.g. "player_idle")
        res_path: Godot resource path (e.g. "res://assets/sprites/player_idle.png")

    Returns confirmation.
    """
    if asset_type not in ("sprites", "music", "sfx"):
        return "ERROR: asset_type must be 'sprites', 'music', or 'sfx'."
    manifest = _load_manifest()
    manifest[asset_type][asset_name] = res_path
    _save_manifest(manifest)
    return f"OK: Manifest updated — {asset_type}/{asset_name} = {res_path}"

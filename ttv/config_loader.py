"""Module for loading and validating TTV (text-to-video) configuration files."""

import json
from dataclasses import dataclass
from typing import List, Optional, Literal

@dataclass
class MusicConfig:
    """Configuration for background or closing credits music."""
    file: Optional[str] = None
    prompt: Optional[str] = None

@dataclass
class ClosingCreditsConfig:
    """Configuration for closing credits section."""
    music: MusicConfig
    poster: MusicConfig  # Reusing MusicConfig since it has the same file/prompt structure

@dataclass
class TTVConfig:
    """Configuration for text-to-video generation."""
    style: str  # Required
    story: List[str]  # Required
    title: str  # Required
    caption_style: Literal["static", "dynamic"] = "static"  # Optional, defaults to static
    background_music: Optional[MusicConfig] = None
    closing_credits: Optional[ClosingCreditsConfig] = None

    def __iter__(self):
        """Make the config unpackable into (style, story, title)."""
        return iter([self.style, self.story, self.title])

def validate_music_config(config: MusicConfig) -> None:
    """Validate that a music config has either a file or a prompt."""
    if not config.file and not config.prompt:
        raise ValueError("Either file or prompt must be specified")
    if config.file and config.prompt:
        raise ValueError("Cannot specify both file and prompt")

def validate_caption_style(caption_style: Optional[str]) -> str:
    """Validate and normalize the caption style.
    
    Args:
        caption_style: The caption style from config, or None
        
    Returns:
        Normalized caption style ("static" or "dynamic")
        
    Raises:
        ValueError: If caption style is invalid
    """
    if caption_style is None:
        return "static"
    if caption_style not in ["static", "dynamic"]:
        raise ValueError(f"Invalid caption style: {caption_style}. Must be 'static' or 'dynamic'")
    return caption_style

def load_input(ttv_config: str) -> TTVConfig:
    """Load and validate the TTV config file.

    Args:
        ttv_config: Path to the config JSON file

    Returns:
        TTVConfig object with validated configuration

    Raises:
        KeyError: If required fields are missing
        JSONDecodeError: If JSON is invalid
        FileNotFoundError: If config file doesn't exist
        ValueError: If music configuration is invalid"""
    with open(ttv_config, 'r', encoding='utf-8') as json_file:
        data = json.load(json_file)

    # Create music configs if present
    background_music = None
    if "background_music" in data:
        background_music = MusicConfig(**data["background_music"])
        validate_music_config(background_music)

    closing_credits = None
    if "closing_credits" in data:
        music = MusicConfig(**data["closing_credits"]["music"])
        poster = MusicConfig(**data["closing_credits"]["poster"])
        validate_music_config(music)
        validate_music_config(poster)
        closing_credits = ClosingCreditsConfig(music=music, poster=poster)

    # Validate caption style
    caption_style = validate_caption_style(data.get("caption_style"))

    # Create and validate full config
    config = TTVConfig(
        style=data["style"],
        story=data["story"],
        title=data["title"],
        caption_style=caption_style,
        background_music=background_music,
        closing_credits=closing_credits
    )

    return config

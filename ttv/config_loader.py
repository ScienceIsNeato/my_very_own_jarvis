"""Module for loading and validating TTV (text-to-video) configuration files."""

import json
from dataclasses import dataclass
from typing import List, Optional, Literal

@dataclass
class MusicSource:
    """Represents a source for music generation or loading."""
    type: Literal["file", "prompt"]
    path: Optional[str] = None  # Required if type is "file"
    prompt: Optional[str] = None  # Required if type is "prompt"
    enabled: bool = False

@dataclass
class MusicConfig:
    """Configuration for background or closing credits music."""
    sources: List[MusicSource]

@dataclass
class TTVConfig:
    """Configuration for text-to-video generation."""
    style: str  # Required
    story: List[str]  # Required
    title: str  # Required
    background_music: Optional[MusicConfig] = None
    closing_credits: Optional[MusicConfig] = None

    def __iter__(self):
        """Make the config unpackable into (style, story, title)."""
        return iter([self.style, self.story, self.title])

def validate_music_source(source: MusicSource) -> None:
    """Validate that a music source has the correct fields based on its type."""
    if source.type == "file" and not source.path:
        raise ValueError("Path is required for file music source")
    if source.type == "prompt" and not source.prompt:
        raise ValueError("Prompt is required for prompt music source")

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
        sources = [MusicSource(**source) for source in data["background_music"]["sources"]]
        for source in sources:
            validate_music_source(source)
        background_music = MusicConfig(sources=sources)

    closing_credits = None
    if "closing_credits" in data:
        sources = [MusicSource(**source) for source in data["closing_credits"]["sources"]]
        for source in sources:
            validate_music_source(source)
        closing_credits = MusicConfig(sources=sources)

    # Create and validate full config
    config = TTVConfig(
        style=data["style"],
        story=data["story"],
        title=data["title"],
        background_music=background_music,
        closing_credits=closing_credits
    )
    
    return config

"""Module for handling dynamic video captions and SRT subtitle generation."""

from typing import List, Tuple, Optional
import tempfile
from dataclasses import dataclass
from logger import Logger
from .ffmpeg_wrapper import run_ffmpeg_command
import subprocess
from PIL import ImageFont

def get_default_font() -> str:
    """Get default font name."""
    return "Arial"

@dataclass
class Word:
    """Represents a single word in a caption with timing and display properties."""
    text: str
    start_time: float
    end_time: float
    line_number: int = 0
    font_size: int = 0
    x_position: float = 0
    width: float = 0
    font_name: str = get_default_font()

    def calculate_width(self, font_size):
        """Calculate exact text width using PIL's ImageFont."""
        try:
            font = ImageFont.truetype(self.font_name, font_size)
        except OSError:
            # Fallback to loading system font by name
            font = ImageFont.load_default()
        self.width = font.getlength(self.text)

@dataclass
class CaptionWindow:
    """Groups words into a display window with shared timing and font size."""
    words: List[Word]
    start_time: float
    end_time: float
    font_size: int

class CaptionEntry:
    """Represents a complete caption with text and timing information."""
    def __init__(self, text: str, start_time: float, end_time: float):
        self.text = text
        self.start_time = start_time
        self.end_time = end_time

def split_into_words(caption: CaptionEntry, words_per_second: float = 2.0, font_name: str = get_default_font()) -> List[Word]:
    """Split caption text into words with timing."""
    words = caption.text.split()
    total_duration = caption.end_time - caption.start_time
    # Calculate timing for each word
    # If we have more words than would fit at words_per_second,
    # adjust the timing to spread words evenly across available duration
    total_words = len(words)
    min_duration_needed = total_words / words_per_second
    if min_duration_needed > total_duration:
        # If we need more time than available, spread words evenly
        word_duration = total_duration / total_words
    else:
        # Otherwise use the requested words_per_second
        word_duration = 1.0 / words_per_second
    result = []
    current_time = caption.start_time
    for i, word in enumerate(words):
        # For the last word, ensure it ends exactly at caption.end_time
        if i == len(words) - 1:
            end_time = caption.end_time
        else:
            end_time = min(current_time + word_duration, caption.end_time)
        result.append(Word(text=word, start_time=current_time, end_time=end_time, font_name=font_name))
        current_time = end_time
    return result

def create_caption_windows(
    words: List[Word],
    min_font_size: int,
    max_font_size: int,
    safe_width: int,  # Available width for text
    safe_height: int,  # Available height for text
    pause_between_windows: float = 0.5
) -> List[CaptionWindow]:
    """Group words into caption windows with appropriate font sizes and line breaks."""
    windows = []
    def calculate_text_width(text: str, font_size: int) -> float:
        """Estimate text width based on font size."""
        return len(text) * font_size * 0.6  # Approximate character width
    def try_fit_words(words_to_fit: List[Word], font_size: int) -> Tuple[List[List[Word]], bool]:
        """
        Try to fit words into lines with given font size.
        Returns (line_groups, fits) where fits is True if text fits within constraints.
        """
        lines = []
        current_line = []
        current_width = 0
        space_width = font_size * 0.6
        for word in words_to_fit:
            word_width = calculate_text_width(word.text, font_size)
            # Add space width if not first word in line
            if current_line:
                word_width += space_width
            if current_width + word_width <= safe_width:
                current_line.append(word)
                current_width += word_width
            else:
                if current_line:  # If we have words in current line
                    lines.append(current_line)
                    current_line = [word]
                    current_width = calculate_text_width(word.text, font_size)
                else:  # Word is too long for line by itself
                    return [], False
        if current_line:
            lines.append(current_line)
        # Check if total height fits
        total_height = len(lines) * (font_size + 5)  # font size + line spacing
        return lines, total_height <= safe_height
    i = 0
    while i < len(words):
        # Start with maximum font size and try to fit as many words as possible
        current_font_size = max_font_size
        best_fit = None
        while current_font_size >= min_font_size:
            # Try to fit words with current font size
            test_words = words[i:]
            line_groups, fits = try_fit_words(test_words, current_font_size)
            if fits and line_groups:
                # Found a fit, save it
                best_fit = (line_groups, current_font_size)
                break
            # Reduce font size and try again
            current_font_size = int(current_font_size * 0.9)  # Reduce by 10%
        if best_fit is None:
            # Couldn't fit even with minimum font size, force at least one word
            line_groups = [[words[i]]]
            current_font_size = min_font_size
            i += 1
        else:
            line_groups, current_font_size = best_fit
            # Count total words in all lines
            words_used = sum(len(line) for line in line_groups)
            i += words_used
        # Create window with the fitted lines
        flat_words = []
        for line_num, line in enumerate(line_groups):
            for word in line:
                word.line_number = line_num
                flat_words.append(word)
        if flat_words:
            window = CaptionWindow(
                words=flat_words,
                start_time=flat_words[0].start_time,
                end_time=flat_words[-1].end_time + pause_between_windows,
                font_size=current_font_size
            )
            windows.append(window)
    return windows

def create_dynamic_captions(
    input_video: str,
    captions: List[CaptionEntry],
    output_path: str,
    min_font_size: int = 32,
    max_font_size: int = 48,
    font_name: str = get_default_font(),
    box_color: str = "black@0",  # Transparent background
    box_border: int = 0,
    position: str = "bottom",
    margin: int = 40,  # Margin from screen edges in pixels
    words_per_second: float = 2.0,
    max_window_height_ratio: float = 0.3  # Maximum height of caption window as ratio of video height
) -> Optional[str]:
    """
    Add Instagram-style dynamic captions to a video.
    Args:
        input_video: Path to input video file
        captions: List[CaptionEntry] objects
        output_path: Path where the output video will be saved
        min_font_size: Minimum font size for captions
        max_font_size: Maximum font size for captions
        font_name: Name of the font to use (should be a bold sans-serif)
        box_color: Color and opacity of the background box
        box_border: Width of the box border
        position: Vertical position of captions ('bottom' or 'center')
        margin: Margin from screen edges in pixels
        words_per_second: Speed of word display
        max_window_height_ratio: Maximum height of caption window as ratio of video height
    """
    try:
        # Get video dimensions using ffprobe
        ffprobe_cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0",
            input_video
        ]
        dimensions = run_ffmpeg_command(ffprobe_cmd)
        if not dimensions:
            raise ValueError("Could not determine video dimensions")
        # Parse dimensions from ffprobe output
        dimensions_str = dimensions.stdout.decode('utf-8') if hasattr(dimensions, 'stdout') else str(dimensions)
        width, height = map(int, dimensions_str.strip().split(','))
        # Calculate safe text area dimensions (accounting for margins)
        safe_width = width - (2 * margin)
        safe_height = int(height * max_window_height_ratio)  # Maximum height for caption window
        # Adjust font sizes based on video dimensions
        # Rule of thumb: max font size should be about 1/10th of the safe height
        adjusted_max_font_size = min(max_font_size, safe_height // 3)  # Allow for at least 3 lines
        adjusted_min_font_size = min(min_font_size, adjusted_max_font_size // 2)
        # Process all captions into words
        all_words = []
        for caption in captions:
            all_words.extend(split_into_words(caption, words_per_second, font_name))
        # Group words into caption windows with dynamic sizing
        windows = create_caption_windows(
            words=all_words,
            min_font_size=adjusted_min_font_size,
            max_font_size=adjusted_max_font_size,
            safe_width=safe_width,
            safe_height=safe_height
        )
        # Build the complex drawtext filter
        drawtext_filters = []
        for window in windows:
            # Calculate base position for the window
            if position == "bottom":
                # Calculate total height of text block
                max_line_number = max(word.line_number for word in window.words)
                text_block_height = (window.font_size * (max_line_number + 1)) + (max_line_number * 5)  # font size + line spacing
                # Position from bottom, ensuring last line is above margin
                base_y = height - margin - text_block_height
            else:
                # Center the entire text block vertically
                max_line_number = max(word.line_number for word in window.words)
                text_block_height = (window.font_size * (max_line_number + 1)) + (max_line_number * 5)
                base_y = (height - text_block_height) // 2
            for word in window.words:
                # Calculate word position within window
                line_offset = word.line_number * (window.font_size + 5)  # 5px padding between lines
                y_position = base_y + line_offset
                # Calculate x position for each word with safety buffer
                if word == window.words[0] or word.line_number != window.words[window.words.index(word)-1].line_number:
                    # First word in line starts at margin with safety buffer
                    x_position = margin + 2  # Add 2px safety buffer
                else:
                    # Position after previous word with proper spacing
                    prev_word = window.words[window.words.index(word)-1]
                    space_width = window.font_size * 0.3  # Adjust space between words
                    x_position = prev_word.x_position + prev_word.width + space_width
                # Calculate word width before positioning
                word.calculate_width(window.font_size)
                # Ensure word doesn't extend beyond right margin with safety buffer
                if x_position + word.width > width - (margin + 2):  # Add 2px safety buffer
                    # Move to next line if word would extend beyond margin
                    word.line_number += 1
                    line_offset = word.line_number * (window.font_size + 5)
                    y_position = base_y + line_offset
                    x_position = margin + 2  # Add 2px safety buffer
                word.x_position = x_position
                # Escape special characters in text
                escaped_text = word.text.replace("'", "\\'")
                filter_text = (
                    f"drawtext=:text='{escaped_text}'"
                    f":font={font_name}"
                    f":fontsize={window.font_size}"
                    f":fontcolor=white"
                    f":x={x_position}"
                    f":y={y_position}"
                    f":enable=between(t\\,{word.start_time}\\,{word.end_time})"
                    f":box=1"
                    f":boxcolor={box_color}"
                    f":boxborderw={box_border}"
                )
                drawtext_filters.append(filter_text)
        # Combine all filters with comma separation
        complete_filter = ",".join(drawtext_filters)
        # Build and run FFmpeg command
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-i", input_video,
            "-vf", complete_filter,
            "-c:a", "copy",
            output_path
        ]
        result = run_ffmpeg_command(ffmpeg_cmd)
        if result:
            Logger.print_info(f"Successfully added dynamic captions to video: {output_path}")
            return output_path
        else:
            Logger.print_error("Failed to add dynamic captions to video")
            return None
    except (ValueError, OSError, subprocess.CalledProcessError) as e:
        Logger.print_error(f"Error adding dynamic captions: {e}")
        return None

def create_srt_captions(
    captions: List[CaptionEntry],
    output_path: Optional[str] = None
) -> Optional[str]:
    """Create an SRT subtitle file from caption entries."""
    try:
        if output_path is None:
            with tempfile.NamedTemporaryFile(suffix='.srt', mode='w', delete=False) as srt_file:
                output_path = srt_file.name
        def format_time(seconds: float) -> str:
            """Convert seconds to SRT time format (HH:MM:SS,mmm)"""
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            seconds = seconds % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}".replace('.', ',')
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, caption in enumerate(captions, 1):
                f.write(f"{i}\n")
                f.write(f"{format_time(caption.start_time)} --> {format_time(caption.end_time)}\n")
                f.write(f"{caption.text}\n\n")
        return output_path
    except (OSError, IOError) as e:
        Logger.print_error(f"Error creating SRT file: {e}")
        return None 
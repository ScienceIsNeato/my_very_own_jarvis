"""Module for handling dynamic video captions and SRT subtitle generation."""

from typing import List, Tuple, Optional
import tempfile
from dataclasses import dataclass
from logger import Logger
from .ffmpeg_wrapper import run_ffmpeg_command
import subprocess
from PIL import ImageFont, UnidentifiedImageError

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

    @classmethod
    def from_timed_word(cls, text: str, start_time: float, end_time: float, font_name: str = get_default_font()) -> 'Word':
        """Create a Word instance from pre-timed word (e.g. from Whisper alignment)."""
        return cls(text=text, start_time=start_time, end_time=end_time, font_name=font_name)

    @classmethod
    def from_text(cls, text: str, font_name: str = get_default_font()) -> 'Word':
        """Create a Word instance from text only, timing to be calculated later."""
        return cls(text=text, start_time=0.0, end_time=0.0, font_name=font_name)

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
    def __init__(self, text: str, start_time: float, end_time: float, timed_words: Optional[List[Tuple[str, float, float]]] = None):
        self.text = text
        self.start_time = start_time
        self.end_time = end_time
        self.timed_words = timed_words

def split_into_words(caption: CaptionEntry, words_per_second: float = 2.0, font_name: str = get_default_font()) -> List[Word]:
    """Split caption text into words with timing.
    
    If caption.timed_words is provided, uses those timings.
    Otherwise, calculates timing based on words_per_second.
    """
    if caption.timed_words:
        # Use pre-calculated word timings (e.g. from Whisper)
        return [Word.from_timed_word(text, start, end, font_name) 
                for text, start, end in caption.timed_words]
    
    # Fall back to calculating timing based on words_per_second
    words = caption.text.split()
    total_duration = caption.end_time - caption.start_time
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
        adjusted_max_font_size = min(max_font_size, safe_height // 3)  # Allow for at least 3 lines
        adjusted_min_font_size = min(min_font_size, adjusted_max_font_size // 2)
        
        # Process all captions into words
        all_words = []
        for caption in captions:
            words = split_into_words(caption, words_per_second, font_name)
            if words:
                all_words.extend(words)
        
        if not all_words:
            Logger.print_error("No words to display in captions")
            return None
        
        # Group words into caption windows with dynamic sizing
        windows = create_caption_windows(
            words=all_words,
            min_font_size=adjusted_min_font_size,
            max_font_size=adjusted_max_font_size,
            safe_width=safe_width,
            safe_height=safe_height
        )
        
        if not windows:
            Logger.print_error("Failed to create caption windows")
            return None
        
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
            
            # Calculate line widths for centering
            line_words = {}
            for word in window.words:
                if word.line_number not in line_words:
                    line_words[word.line_number] = []
                line_words[word.line_number].append(word)
            
            # Calculate line widths and starting positions
            line_widths = {}
            line_start_x = {}
            for line_num, words in line_words.items():
                # Calculate total width including spaces
                total_width = 0
                for i, word in enumerate(words):
                    word.calculate_width(window.font_size)
                    total_width += word.width
                    if i < len(words) - 1:
                        total_width += window.font_size * 0.3  # Space between words
                
                line_widths[line_num] = total_width
                # Center the line horizontally
                line_start_x[line_num] = (width - total_width) // 2
            
            # Position words within their lines
            for line_num, words in line_words.items():
                current_x = line_start_x[line_num]
                for word in words:
                    word.x_position = current_x
                    current_x += word.width + (window.font_size * 0.3)  # Add space after word
            
            # Create drawtext filters for each word
            for word in window.words:
                # Calculate y position for the word
                y_position = base_y + (word.line_number * (window.font_size + 5))  # 5px padding between lines
                
                # Escape special characters in text
                escaped_text = word.text.replace("'", "\\'")
                
                filter_text = (
                    f"drawtext=text='{escaped_text}'"
                    f":font={font_name}"
                    f":fontsize={window.font_size}"
                    f":fontcolor=white"
                    f":x={word.x_position}"
                    f":y={y_position}"
                    f":enable=between(t\\,{word.start_time}\\,{window.end_time})"
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
            
    except (ValueError, OSError, subprocess.SubprocessError, UnidentifiedImageError) as e:
        Logger.print_error(f"Error adding dynamic captions: {str(e)}")
        import traceback
        Logger.print_error(f"Traceback: {traceback.format_exc()}")
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

def create_static_captions(
    input_video: str,
    captions: List[CaptionEntry],
    output_path: str,
    font_size: int = 40,
    font_name: str = get_default_font(),
    box_color: str = "black@0.5",  # Semi-transparent background
    position: str = "bottom",
    margin: int = 40
) -> Optional[str]:
    """
    Add simple static captions to a video.
    
    Args:
        input_video: Path to input video file
        captions: List of CaptionEntry objects
        output_path: Path where the output video will be saved
        font_size: Font size for captions
        font_name: Name of the font to use
        box_color: Color and opacity of the background box
        position: Vertical position of captions ('bottom' or 'center')
        margin: Margin from screen edges in pixels
    """
    try:
        # Get video dimensions
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
        
        width, height = map(int, dimensions.stdout.decode('utf-8').strip().split(','))
        
        # Build drawtext filters for each caption
        drawtext_filters = []
        for caption in captions:
            # Calculate y position
            if position == "bottom":
                y_position = f"h-{margin}-th"  # Position from bottom with margin
            else:
                y_position = f"(h-th)/2"  # Center vertically
                
            # Escape special characters in text
            escaped_text = caption.text.replace("'", "\\'")
            
            filter_text = (
                f"drawtext=text='{escaped_text}'"
                f":font={font_name}"
                f":fontsize={font_size}"
                f":fontcolor=white"
                f":x=(w-text_w)/2"  # Center horizontally
                f":y={y_position}"
                f":enable=between(t\\,{caption.start_time}\\,{caption.end_time})"
                f":box=1"
                f":boxcolor={box_color}"
            )
            drawtext_filters.append(filter_text)
            
        # Combine all filters
        complete_filter = ",".join(drawtext_filters)
        
        # Run FFmpeg command
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-i", input_video,
            "-vf", complete_filter,
            "-c:a", "copy",
            output_path
        ]
        
        result = run_ffmpeg_command(ffmpeg_cmd)
        if result:
            Logger.print_info(f"Successfully added static captions to video: {output_path}")
            return output_path
        else:
            Logger.print_error("Failed to add static captions to video")
            return None
            
    except (ValueError, OSError, subprocess.CalledProcessError) as e:
        Logger.print_error(f"Error adding static captions: {e}")
        return None 
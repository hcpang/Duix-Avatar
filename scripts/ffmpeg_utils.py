"""
FFmpeg utilities for finding and using FFmpeg tools.

This module provides functions to locate FFmpeg executables
(ffmpeg, ffprobe, etc.) by checking system PATH and the project's
resources folder.
"""

import subprocess
from pathlib import Path


def find_ffmpeg_tool(tool_name):
    """Find FFmpeg tool executable, checking PATH and resources folder

    Args:
        tool_name: Name of the tool (e.g., 'ffmpeg', 'ffprobe', 'ffplay')

    Returns:
        Path to executable or None if not found
    """
    # Try system PATH first
    try:
        result = subprocess.run([tool_name, '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            return tool_name
    except FileNotFoundError:
        pass

    # Check resources folder
    script_dir = Path(__file__).parent.parent
    tool_paths = [
        script_dir / 'resources' / 'ffmpeg' / 'win-amd64' / 'bin' / f'{tool_name}.exe',
        script_dir / 'resources' / 'ffmpeg' / 'linux-amd64' / tool_name,
    ]

    for tool_path in tool_paths:
        if tool_path.exists():
            return str(tool_path)

    return None


def find_ffmpeg():
    """Find ffmpeg executable, checking PATH and resources folder"""
    return find_ffmpeg_tool('ffmpeg')


def find_ffprobe():
    """Find ffprobe executable, checking PATH and resources folder"""
    return find_ffmpeg_tool('ffprobe')

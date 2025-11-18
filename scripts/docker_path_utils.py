#!/usr/bin/env python3
"""
Docker Path Utilities

Centralized path conversion between Windows host and Docker container paths.
Used across scripts that interact with Docker-based TTS/ASR services.
"""

import os


def to_docker_path(windows_path, service='tts'):
    """
    Convert Windows path to Docker container path.

    Args:
        windows_path: Windows file path (absolute or relative)
        service: 'tts' or 'asr' to determine container mapping

    Returns:
        Docker container path

    Examples:
        >>> to_docker_path('D:/duix_avatar_data/face2face/temp/audio.wav')
        '/code/data/temp/audio.wav'

        >>> to_docker_path('inputs/reference.wav')
        '/code/data/origin_audio/reference.wav'
    """
    # Convert to absolute path and normalize
    abs_path = os.path.abspath(windows_path)
    normalized = abs_path.replace('\\', '/')

    # Convert D:/duix_avatar_data/face2face → /code/data
    if 'duix_avatar_data/face2face' in normalized.lower():
        return normalized.replace('D:/duix_avatar_data/face2face', '/code/data').replace('d:/duix_avatar_data/face2face', '/code/data')

    # Convert D:/duix_avatar_data/voice/data → /code/data
    if 'duix_avatar_data/voice/data' in normalized.lower():
        return normalized.replace('D:/duix_avatar_data/voice/data/', '/code/data/').replace('d:/duix_avatar_data/voice/data/', '/code/data/')

    # Files in inputs/ directory → /code/data/origin_audio/
    if 'inputs' in normalized.lower():
        filename = os.path.basename(normalized)
        return f"/code/data/origin_audio/{filename}"

    # Already a Docker path
    if normalized.startswith('/code/'):
        return normalized

    # Default: assume it's a filename in temp directory
    filename = os.path.basename(normalized)
    return f"/code/data/temp/{filename}"


def to_windows_path(docker_path, base_dir='face2face'):
    """
    Convert Docker container path to Windows path.

    Args:
        docker_path: Docker container path
        base_dir: Base directory ('face2face' or 'voice')

    Returns:
        Windows file path

    Examples:
        >>> to_windows_path('/code/data/temp/audio.wav')
        'D:/duix_avatar_data/face2face/temp/audio.wav'

        >>> to_windows_path('/code/data/temp/audio.wav', base_dir='voice')
        'D:/duix_avatar_data/voice/data/temp/audio.wav'
    """
    normalized = docker_path.replace('\\', '/')

    if base_dir == 'voice':
        windows_path = normalized.replace('/code/data/', 'D:/duix_avatar_data/voice/data/')
    else:
        windows_path = normalized.replace('/code/data', 'D:/duix_avatar_data/face2face')

    # Convert forward slashes to backslashes for Windows
    return windows_path.replace('/', '\\')


def convert_reference_audio_path(ref_audio_arg):
    """
    Convert reference audio argument (supports ||| separated multiple files).

    Args:
        ref_audio_arg: Single path or ||| separated paths

    Returns:
        Converted path(s) in same format

    Examples:
        >>> convert_reference_audio_path('inputs/ref.wav')
        '/code/data/origin_audio/ref.wav'

        >>> convert_reference_audio_path('inputs/ref1.wav|||inputs/ref2.wav')
        '/code/data/origin_audio/ref1.wav|||/code/data/origin_audio/ref2.wav'
    """
    if '|||' in ref_audio_arg:
        # Multiple reference audios
        paths = [p.strip() for p in ref_audio_arg.split('|||')]
        converted = [to_docker_path(p) for p in paths]
        return '|||'.join(converted)
    else:
        # Single reference audio
        return to_docker_path(ref_audio_arg)


def is_docker_path(path):
    """Check if a path is already a Docker container path."""
    normalized = path.replace('\\', '/')
    return normalized.startswith('/code/')


def is_windows_data_path(path):
    """Check if a path is in the Windows duix_avatar_data directory."""
    normalized = path.replace('\\', '/').lower()
    return 'duix_avatar_data' in normalized


def ensure_docker_accessible(file_path, service='video'):
    """
    Ensure a file is accessible to Docker container by copying if needed.

    If the file is not in a Docker-mounted directory, copies it to a temporary
    Docker-accessible location and returns the Docker path.

    Args:
        file_path: Path to file (Windows path or Docker path)
        service: Which service needs access ('video' or 'tts')

    Returns:
        Docker path that the container can access

    Examples:
        >>> ensure_docker_accessible('inputs/AlexReference_tiny.mp4')
        '/code/data/temp/AlexReference_tiny.mp4'
        # (file is copied to D:/duix_avatar_data/face2face/temp/)
    """
    import shutil

    # Already a Docker path - return as-is
    if is_docker_path(file_path):
        return file_path

    # Check if file is already in a Docker-accessible location
    if is_windows_data_path(file_path):
        return to_docker_path(file_path, service=service)

    # File is not Docker-accessible - copy to temp directory
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    filename = os.path.basename(file_path)

    if service == 'tts':
        temp_dir = "D:/duix_avatar_data/voice/data/temp"
    else:
        temp_dir = "D:/duix_avatar_data/face2face/temp"

    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, filename)

    # Copy file if it doesn't exist or if source is newer
    if not os.path.exists(temp_path) or \
       os.path.getmtime(file_path) > os.path.getmtime(temp_path):
        print(f"Copying {filename} to Docker-accessible location...")
        print(f"  From: {file_path}")
        print(f"  To: {temp_path}")
        shutil.copy2(file_path, temp_path)
        print(f"  ✓ Copied successfully")

    # Convert to Docker path
    docker_path = to_docker_path(temp_path, service=service)
    print(f"  Docker path: {docker_path}")

    return docker_path

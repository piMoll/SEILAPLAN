import os
from pathlib import Path
from typing import List, Union
from urllib.parse import urlparse

GDAL_VIRTUAL_FILE_PREFIX = [
    "/vsicurl/",  # Streamed resources
    "/vsizip/",  # Zip archives
    "/vsis3/",  # S3 buckets
    "/vsiazure/",  # Azure Blob Storage
    "/vsigs/",  # Google Cloud Storage
    "/vsimem/",  # Memory mapped files
]
CLOUD_SCHEMES = {
    "s3",  # S3 buckets
    "gs",  # Google Cloud Storage
    "az",  # Azure Blob Storage
    "abfs",  # Azure Blob Storage
    "abfss",  # Azure Blob Storage
    "http",  # HTTP
    "https",  # HTTPS
    "ftp",  # FTP
}


def is_remote_or_virtual(path) -> bool:
    """Checks if a path leads to a virtual or remote resource."""
    path = str(path)
    if any(path.startswith(prefix) for prefix in GDAL_VIRTUAL_FILE_PREFIX):
        return True
    parsed = urlparse(path)
    return parsed.scheme.lower() in CLOUD_SCHEMES


def path_exists_or_is_remote(path) -> bool:
    return is_remote_or_virtual(path) or os.path.exists(path)


def get_relative_path(
    target_path: Union[str, Path], relative_to: Union[str, Path]
) -> str:
    """Returns the relative path from relative_to to target_path. If the two paths
    are remote or on different drives (in the case of Windows), returns the target_path.
    This function does not reliably check if the paths exist."""
    target_path = str(target_path)
    relative_to = str(relative_to)

    if is_remote_or_virtual(target_path) or is_remote_or_virtual(relative_to):
        return target_path

    try:
        return os.path.relpath(target_path, relative_to)
    except ValueError:
        # Will throw ValueError on Windows if paths are on two different drives
        return target_path


def get_absolute_path_from_relative(
    relative_path: Union[str, Path], base_path: Union[str, Path]
) -> str:
    """Returns an absolute path from a relative one and a base_path. If the relative
    path is already absolute, it returns it. If either path is remote or on a different
    drive, it returns the relative_path as is."""

    relative_path = str(relative_path)
    base_path = str(base_path)

    if is_remote_or_virtual(base_path) or is_remote_or_virtual(relative_path):
        return str(relative_path)

    if os.path.isabs(relative_path):
        return relative_path
    if not os.path.isabs(base_path):
        base_path = os.path.abspath(base_path)

    return os.path.abspath(os.path.join(base_path, relative_path))


def calculate_path_candidates(relative_path: str, base_path_list: List[str]):
    """Generates a list of possible absolute path candidates based on a relative path
    and a list of possible paths it is relative to.
    Tests if the path exists. If it's a remote resource, it's not tested but added to
    the candidate list directly. Remote resources are dealt with later when using gdal
    to load the geodata."""
    path_candidates = []
    for base_path in base_path_list:
        path_candidates.append(
            get_absolute_path_from_relative(relative_path, base_path)
        )

    return [path for path in path_candidates if path_exists_or_is_remote(path)]

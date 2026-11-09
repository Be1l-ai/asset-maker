"""Asset manifest and provenance tracking."""

from dataclasses import dataclass, field
import hashlib
import json
from importlib.metadata import version
from pathlib import Path
from typing import Any, Dict, Optional, Sequence


def sha256(path_or_bytes: Path | bytes | str) -> str:
    """Calculate SHA-256 digest of a file or byte string."""
    if isinstance(path_or_bytes, (str, Path)):
        return hashlib.sha256(Path(path_or_bytes).read_bytes()).hexdigest()
    return hashlib.sha256(path_or_bytes).hexdigest()


def get_installed_versions(packages: Sequence[str] = (
    "numpy", "scipy", "Pillow", "aggdraw", "trimesh", "manifold3d"
)) -> Dict[str, str]:
    """Retrieve installed versions of core asset libraries."""
    versions = {}
    for pkg in packages:
        try:
            versions[pkg] = version(pkg)
        except Exception:
            pass
    return versions


@dataclass
class Manifest:
    """Class representing a reproducible asset metadata manifest."""
    asset: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    versions: Dict[str, str] = field(default_factory=get_installed_versions)
    sha256: Dict[str, str] = field(default_factory=dict)
    recipe: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def record_artifact(self, file_path: Path | str) -> "Manifest":
        """Record checksum of an output artifact file."""
        p = Path(file_path)
        if p.is_file():
            self.sha256[p.name] = sha256(p)
        return self

    def scan_directory(self, directory: Path | str, exclude_name: str = "manifest.json") -> "Manifest":
        """Scan directory and record checksums of all non-manifest files."""
        dir_path = Path(directory)
        for p in sorted(dir_path.iterdir()):
            if p.is_file() and p.name != exclude_name:
                self.sha256[p.name] = sha256(p)
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convert manifest to serializable dictionary."""
        data: Dict[str, Any] = {
            "asset": self.asset,
            "parameters": self.parameters,
            "versions": self.versions,
            "sha256": self.sha256,
        }
        if self.recipe:
            data["recipe"] = self.recipe
        if self.extra:
            data.update(self.extra)
        return data

    def save(self, directory: Path | str, filename: str = "manifest.json") -> Path:
        """Write manifest JSON to disk."""
        out_path = Path(directory) / filename
        out_path.write_text(json.dumps(self.to_dict(), indent=2) + "\n")
        return out_path


def save_manifest(
    directory: Path | str,
    asset_file: Path | str,
    parameters: Dict[str, Any],
    recipe_file: Optional[Path | str] = None,
    extra_metadata: Optional[Dict[str, Any]] = None,
    manifest_name: str = "manifest.json",
) -> Path:
    """Convenience functional helper to generate and write a standard asset manifest."""
    asset_name = Path(asset_file).name
    recipe_name = Path(recipe_file).name if recipe_file else None

    manifest = Manifest(
        asset=asset_name,
        parameters=parameters,
        recipe=recipe_name,
        extra=extra_metadata or {},
    )
    manifest.scan_directory(directory, exclude_name=manifest_name)
    return manifest.save(directory, filename=manifest_name)

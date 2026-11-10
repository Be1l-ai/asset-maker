"""Asset manifest and provenance tracking."""

from dataclasses import dataclass, field
import hashlib
import json
from importlib.metadata import version
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence


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
    vault_refs: Dict[str, List[str]] = field(default_factory=dict)

    def record_artifact(self, file_path: Path | str) -> "Manifest":
        """Record checksum of an output artifact file."""
        p = Path(file_path)
        if p.is_file():
            self.sha256[p.name] = sha256(p)
        return self

    def scan_directory(
        self,
        directory: Path | str,
        exclude_name: str = "manifest.json",
        only: Optional[Iterable[str]] = None,
    ) -> "Manifest":
        """Record checksums of non-manifest files in ``directory``.

        ``only`` restricts hashing to files whose names start with one of the given
        prefixes (e.g. the asset name), so stale files from other versions are ignored.
        """
        dir_path = Path(directory)
        prefixes = tuple(only) if only is not None else None
        for p in sorted(dir_path.iterdir()):
            if not p.is_file() or p.name == exclude_name:
                continue
            if prefixes is not None and not (p.name.startswith(prefixes) or p.name in ("generate.py", "preview.png", "preview.gif")):
                continue
            self.sha256[p.name] = sha256(p)
        return self

    def declare_vault(self, doc: str, *symbols: str) -> "Manifest":
        """Declare that this recipe applies a vault document, via the named pipeline symbols.

        ``doc`` is relative to ``vault/`` (e.g. ``"mathematics/noise_and_fields/worley_cellular_noise.md"``).
        ``python -m asset_pipeline audit`` verifies each symbol is really called in the recipe.
        """
        self.vault_refs.setdefault(doc, [])
        for sym in symbols:
            if sym not in self.vault_refs[doc]:
                self.vault_refs[doc].append(sym)
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
        if self.vault_refs:
            data["vault_refs"] = self.vault_refs
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

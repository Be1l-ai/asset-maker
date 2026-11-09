"""AssetMaking procedural asset generation library."""

from .cli import init_asset, list_templates
from .manifest import Manifest, get_installed_versions, save_manifest, sha256
from .mesh3d import MeshBuilder, SolidMesh
from .sfx import Sound, SoundSynthesizer
from .sprite2d import SeamlessTile, SpriteCanvas
from .validator import AssetValidator, ValidationReport
from .vfx import Easing, Flipbook, ParticleEmitter

from . import manifest, mesh3d, sfx, sprite2d, validator, vfx

__all__ = [
    # Core domain classes
    "SolidMesh",
    "MeshBuilder",
    "SpriteCanvas",
    "SeamlessTile",
    "Flipbook",
    "ParticleEmitter",
    "Easing",
    "Sound",
    "SoundSynthesizer",
    "AssetValidator",
    "ValidationReport",
    "Manifest",
    # CLI / scaffolding
    "init_asset",
    "list_templates",
    # Submodules
    "mesh3d",
    "sprite2d",
    "vfx",
    "sfx",
    "validator",
    "manifest",
]

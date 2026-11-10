# Contributing & Commit Guidelines

## Git Commit Convention

This repository follows the [Conventional Commits](https://www.conventionalcommits.org/) specification (enforced via `.githooks/commit-msg`).

### Format
```
<type>(<optional scope>): <description>
```

### Types
- **`feat`**: A new feature, library class, generator, or asset capability.
- **`fix`**: A bug fix in generation math, validators, or pipelines.
- **`refactor`**: Code restructuring without changing observable behavior or outputs.
- **`docs`**: Documentation updates (guides, README, AGENTS.md, inline docstrings).
- **`style`**: Code style, formatting, or whitespace adjustments.
- **`test`**: Adding or refactoring test cases in `tests/`.
- **`chore`**: Maintenance tasks, dependency updates, `.gitignore`, or tooling changes.
- **`perf`**: Performance optimizations (downsampling speed, boolean execution).

### Common Scopes
- `(pipeline)`: `asset_pipeline` library and CLI
- `(3d)`: 3D mesh solids, CSG booleans, glTF/OBJ export
- `(2d)`: 2D vector/raster icons, seamless tiles, downsampling
- `(vfx)`: Sprite sheet atlases, particle emitters, GIF playback
- `(sfx)`: Modal synthesis, transient clicks, WAV export
- `(skills)`: Agent skills in `skills/`
- `(templates)`: Starter templates in `templates/`
- `(gallery)`: Interactive web gallery, browser frontend, catalog

### Examples
- `feat(pipeline): add MeshBuilder fluent interface for watertight solids`
- `fix(2d): eliminate border interpolation ringing with 1px gutter`
- `docs(skills): document inharmonic resonance ratios for physical materials`
- `chore(hooks): install conventional commit-msg and syntax-checking pre-commit hooks`

---

## Git Hooks

Hooks are version-controlled in `.githooks/` and configured via `git config core.hooksPath .githooks`:

1. **`commit-msg`**: Validates the Conventional Commits regex pattern.
2. **`pre-commit`**: Syntax-checks staged `.py` files and blocks merge conflict markers.

To set up hooks in a fresh clone:
```sh
git config core.hooksPath .githooks
```

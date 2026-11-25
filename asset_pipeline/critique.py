"""Two-tier cross-modality visual/audio critique log & 5-loop detail-refinement gate.

Tier 1 (Inner Build Loop): ``rounds`` (min 3 rounds for hero assets) — get from blockout to a working Final.
Tier 2 (Outer Detail-Critique Loop): ``detail_passes`` (up to 5 outer loops) — grade the Final 0-10 on
modality-specific hard details (3D joints/paws/optimization, 2D line/value craft, VFX timing/overdraw,
SFX transient/headroom). Any pass scoring below ``target_detail_score`` (default 9.0) MUST re-loop using
that Final as the new starting point until it reaches the target or completes 5 outer passes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .manifest import sha256

RUBRIC_AXES = ("silhouette", "proportions", "surface_materials", "secondary_detail", "lighting_read")

DETAIL_RUBRIC_AXES: Dict[str, tuple[str, ...]] = {
    "3d": (
        "joints_and_extremities",
        "surface_optimization",
        "reference_fidelity",
        "seam_cleanliness",
        "material_read",
    ),
    "2d": (
        "silhouette_readability",
        "edge_and_line_craft",
        "value_and_color_harmony",
        "detail_hierarchy",
        "pixel_or_vector_cleanliness",
    ),
    "vfx": (
        "timing_and_arc",
        "alpha_and_edge_falloff",
        "loop_or_dissolve_cleanliness",
        "color_temperature_progression",
        "overdraw_optimization",
    ),
    "sfx": (
        "transient_punch",
        "spectral_balance",
        "envelope_and_tail_cleanliness",
        "clipping_and_headroom",
        "layer_cohesion",
    ),
}


@dataclass
class CritiqueRound:
    round_number: int
    preview_file: str
    preview_sha256: str
    angles_checked: List[str]
    defects_found: List[str]
    fixes_applied: List[str]
    subsystem: str = "full_asset"
    rubric_scores: Dict[str, int] = field(default_factory=dict)


@dataclass
class DetailCritiquePass:
    pass_number: int
    modality: str
    preview_file: str
    preview_sha256: str
    overall_score: float
    detail_scores: Dict[str, float]
    flaws_found: List[str]
    fixes_for_next_pass: List[str]
    seeded_vault_docs: List[str] = field(default_factory=list)


@dataclass
class CritiqueLog:
    """Tracks Tier-1 inner build rounds AND Tier-2 outer 0-10 detail-critique re-loops (max 5)."""
    asset: str
    min_rounds: int = 3
    modality: str = "3d"
    max_detail_passes: int = 5
    target_detail_score: float = 9.0
    rounds: List[CritiqueRound] = field(default_factory=list)
    detail_passes: List[DetailCritiquePass] = field(default_factory=list)

    def add_round(
        self,
        preview_path: Path | str,
        defects_found: Sequence[str],
        fixes_applied: Sequence[str],
        angles_checked: Sequence[str] = ("3/4", "front", "side", "rear", "closeup"),
        subsystem: str = "full_asset",
        rubric_scores: Optional[Dict[str, int]] = None,
    ) -> CritiqueRound:
        p = Path(preview_path)
        digest = sha256(p) if p.is_file() else ""
        entry = CritiqueRound(
            round_number=len(self.rounds) + 1,
            preview_file=p.name,
            preview_sha256=digest,
            angles_checked=list(angles_checked),
            defects_found=[str(d).strip() for d in defects_found if str(d).strip()],
            fixes_applied=[str(f).strip() for f in fixes_applied if str(f).strip()],
            subsystem=str(subsystem),
            rubric_scores=dict(rubric_scores or {}),
        )
        self.rounds.append(entry)
        return entry

    def add_detail_pass(
        self,
        preview_path: Path | str,
        overall_score: float,
        detail_scores: Dict[str, float],
        flaws_found: Sequence[str],
        fixes_for_next_pass: Sequence[str],
        modality: Optional[str] = None,
        seeded_vault_docs: Sequence[str] = (),
    ) -> DetailCritiquePass:
        """Record an outer macro 0-10 detail critique pass on a Final candidate (up to 5 passes)."""
        if len(self.detail_passes) >= self.max_detail_passes:
            raise ValueError(f"Exceeded max_detail_passes ({self.max_detail_passes})")
        p = Path(preview_path)
        digest = sha256(p) if p.is_file() else ""
        mod = (modality or self.modality).lower()
        entry = DetailCritiquePass(
            pass_number=len(self.detail_passes) + 1,
            modality=mod,
            preview_file=p.name,
            preview_sha256=digest,
            overall_score=round(float(overall_score), 2),
            detail_scores={k: round(float(v), 2) for k, v in detail_scores.items()},
            flaws_found=[str(d).strip() for d in flaws_found if str(d).strip()],
            fixes_for_next_pass=[str(f).strip() for f in fixes_for_next_pass if str(f).strip()],
            seeded_vault_docs=[str(s).strip() for s in seeded_vault_docs if str(s).strip()],
        )
        self.detail_passes.append(entry)
        return entry

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "asset": self.asset,
            "modality": self.modality,
            "min_rounds": self.min_rounds,
            "max_detail_passes": self.max_detail_passes,
            "target_detail_score": self.target_detail_score,
            "rounds": [
                {
                    "round": r.round_number,
                    "subsystem": r.subsystem,
                    "preview_file": r.preview_file,
                    "preview_sha256": r.preview_sha256,
                    "angles_checked": r.angles_checked,
                    "defects_found": r.defects_found,
                    "fixes_applied": r.fixes_applied,
                    "rubric_scores": r.rubric_scores,
                }
                for r in self.rounds
            ],
        }
        if self.detail_passes:
            out["detail_passes"] = [
                {
                    "pass": dp.pass_number,
                    "modality": dp.modality,
                    "preview_file": dp.preview_file,
                    "preview_sha256": dp.preview_sha256,
                    "overall_score": dp.overall_score,
                    "detail_scores": dp.detail_scores,
                    "flaws_found": dp.flaws_found,
                    "fixes_for_next_pass": dp.fixes_for_next_pass,
                    "seeded_vault_docs": dp.seeded_vault_docs,
                }
                for dp in self.detail_passes
            ]
        return out

    def save(self, directory: Path | str, filename: str = "critique_log.json") -> Path:
        out = Path(directory) / filename
        out.write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")
        return out

    @classmethod
    def validate_file(
        cls,
        path: Path | str,
        min_rounds: int = 3,
        min_final_score: int = 8,
        require_detail_pass: bool = False,
    ) -> List[str]:
        """Validate Tier-1 inner rounds and Tier-2 outer 0-10 detail passes (up to 5 loops)."""
        p = Path(path)
        if not p.is_file():
            return [f"{p.name} is missing (hero assets require >= {min_rounds} visual critique rounds)"]
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            return [f"{p.name} is invalid JSON: {exc}"]

        rounds = data.get("rounds", [])
        req = max(min_rounds, int(data.get("min_rounds", min_rounds)))
        errors: List[str] = []
        if len(rounds) < req:
            errors.append(f"{p.name} has {len(rounds)} critique round(s); hero assets require at least {req}")
            return errors

        seen_hashes: List[str] = []
        for idx, r in enumerate(rounds, start=1):
            defects = [d for d in r.get("defects_found", []) if isinstance(d, str) and d.strip()]
            fixes = [f for f in r.get("fixes_applied", []) if isinstance(f, str) and f.strip()]
            h = str(r.get("preview_sha256", "")).strip()
            if idx < len(rounds) and not defects:
                errors.append(f"critique round {idx} lists no concrete defects_found")
            if idx < len(rounds) and not fixes:
                errors.append(f"critique round {idx} lists no fixes_applied")
            if not h:
                errors.append(f"critique round {idx} is missing preview_sha256")
            else:
                if seen_hashes and h == seen_hashes[-1]:
                    errors.append(f"critique round {idx} has identical preview_sha256 to round {idx - 1} (no visual change)")
                seen_hashes.append(h)

        final_scores = rounds[-1].get("rubric_scores") or {}
        if final_scores:
            for axis in RUBRIC_AXES:
                val = final_scores.get(axis)
                if val is None:
                    errors.append(f"final critique round rubric_scores missing axis '{axis}'")
                elif int(val) < min_final_score:
                    errors.append(f"final critique round rubric axis '{axis}' scored {val}/10; hero minimum is {min_final_score}/10")

        # Tier-2 Outer Detail-Critique Loop validation (0-10 scoring, max 5 outer loops)
        detail_passes = data.get("detail_passes") or []
        max_dp = int(data.get("max_detail_passes", 5))
        target_dp = float(data.get("target_detail_score", 9.0))
        if require_detail_pass and not detail_passes:
            errors.append(f"{p.name} is missing outer 'detail_passes' (0-10 hard-detail critique loop)")
        if detail_passes:
            if len(detail_passes) > max_dp:
                errors.append(f"{p.name} has {len(detail_passes)} detail_passes; maximum allowed is {max_dp}")
            dp_hashes: List[str] = []
            for idx, dp in enumerate(detail_passes, start=1):
                mod = str(dp.get("modality", data.get("modality", "3d"))).lower()
                score = float(dp.get("overall_score", -1.0))
                if not (0.0 <= score <= 10.0):
                    errors.append(f"detail pass {idx} overall_score {score} out of 0..10 range")
                h = str(dp.get("preview_sha256", "")).strip()
                if not h:
                    errors.append(f"detail pass {idx} missing preview_sha256")
                elif dp_hashes and h == dp_hashes[-1]:
                    errors.append(f"detail pass {idx} has identical preview_sha256 to pass {idx - 1} (no change on re-loop)")
                if h:
                    dp_hashes.append(h)

                axes = DETAIL_RUBRIC_AXES.get(mod, DETAIL_RUBRIC_AXES["3d"])
                d_scores = dp.get("detail_scores") or {}
                for ax in axes:
                    if ax not in d_scores:
                        errors.append(f"detail pass {idx} missing modality '{mod}' axis '{ax}'")

                if idx < len(detail_passes):
                    if not dp.get("flaws_found"):
                        errors.append(f"detail pass {idx} must list concrete flaws_found before re-looping")
                    if not dp.get("fixes_for_next_pass"):
                        errors.append(f"detail pass {idx} must list fixes_for_next_pass before re-looping")
                else:
                    if score < target_dp and len(detail_passes) < max_dp:
                        errors.append(
                            f"final detail pass {idx} scored {score}/10 (< {target_dp}/10 target); "
                            f"must re-loop from this Final as new starting point (up to {max_dp} outer passes)"
                        )

        return errors

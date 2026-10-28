from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ARMBENCH_PUBLIC_FILE_ROLES = {
    "PickRGB.jpg": "pre_pick_image",
    "ToteWallRGB.jpg": "post_pick_tote_wall_image",
    "OnArmLowRGB.jpg": "transfer_on_arm_image",
    "FarTrayRGB.jpg": "post_place_tray_image",
    "container.json": "container_metadata",
    "annotation.json": "annotation_metadata",
}
_JSON_ROLES = {"container_metadata", "annotation_metadata"}
_HASH_MODES = {"none", "metadata", "all"}


@dataclass(frozen=True, slots=True)
class ArmbenchProbeConfig:
    hash_mode: str = "metadata"
    json_samples_per_role: int = 8
    max_json_bytes: int = 16 * 1024 * 1024
    include_json_key_names: bool = False
    max_shape_depth: int = 5

    def __post_init__(self) -> None:
        if self.hash_mode not in _HASH_MODES:
            raise ValueError(f"hash_mode must be one of: {sorted(_HASH_MODES)}")
        for name in ("json_samples_per_role", "max_json_bytes", "max_shape_depth"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        if not isinstance(self.include_json_key_names, bool):
            raise TypeError("include_json_key_names must be boolean")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _key_label(key: str, include_names: bool) -> str:
    if include_names:
        return key
    return f"key_sha256:{hashlib.sha256(key.encode('utf-8')).hexdigest()}"


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _strict_json_loads(text: str) -> Any:
    return json.loads(
        text,
        parse_constant=_reject_constant,
        object_pairs_hook=_unique_object,
    )


def _json_shape(
    value: Any,
    *,
    include_key_names: bool,
    depth: int,
) -> Any:
    if depth <= 0:
        return {"type": "depth_limit"}
    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        return {"type": "boolean"}
    if isinstance(value, int):
        return {"type": "integer"}
    if isinstance(value, float):
        return {"type": "number"}
    if isinstance(value, str):
        return {"type": "string"}
    if isinstance(value, list):
        shapes = {
            json.dumps(
                _json_shape(
                    item,
                    include_key_names=include_key_names,
                    depth=depth - 1,
                ),
                sort_keys=True,
                separators=(",", ":"),
            )
            for item in value
        }
        return {
            "type": "array",
            "item_shapes": [json.loads(item) for item in sorted(shapes)],
        }
    if isinstance(value, dict):
        return {
            "type": "object",
            "fields": {
                _key_label(str(key), include_key_names): _json_shape(
                    item,
                    include_key_names=include_key_names,
                    depth=depth - 1,
                )
                for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            },
        }
    raise TypeError(f"unsupported JSON value type: {type(value).__name__}")


def _shape_fingerprint(shape: Any) -> str:
    encoded = json.dumps(
        shape,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def probe_armbench_root(
    root: str | Path,
    config: ArmbenchProbeConfig | None = None,
) -> dict[str, Any]:
    """Build a shareable structural inventory without emitting paths or JSON values."""

    policy = config or ArmbenchProbeConfig()
    root_path = Path(root)
    if root_path.is_symlink():
        raise ValueError("ARMBench root must not be a symbolic link")
    if not root_path.is_dir():
        raise ValueError("ARMBench root must be an existing directory")

    files = sorted(
        (
            path
            for path in root_path.rglob("*")
            if path.is_file() or path.is_symlink()
        ),
        key=lambda path: path.relative_to(root_path).as_posix(),
    )
    role_counts: Counter[str] = Counter()
    suffix_counts: Counter[str] = Counter()
    json_candidates: dict[str, list[tuple[str, Path]]] = defaultdict(list)
    inventory_lines: list[str] = []
    symlink_count = 0
    unreadable_count = 0
    total_bytes = 0
    hashed_file_count = 0

    for path in files:
        relative = path.relative_to(root_path).as_posix()
        if path.is_symlink():
            symlink_count += 1
            continue
        role = ARMBENCH_PUBLIC_FILE_ROLES.get(path.name, "other")
        role_counts[role] += 1
        suffix_counts[path.suffix.lower() or "<none>"] += 1
        try:
            size = path.stat().st_size
        except OSError:
            unreadable_count += 1
            continue
        total_bytes += size
        content_sha256: str | None = None
        should_hash = policy.hash_mode == "all" or (
            policy.hash_mode == "metadata" and role in _JSON_ROLES
        )
        if should_hash:
            try:
                content_sha256 = _file_sha256(path)
                hashed_file_count += 1
            except OSError:
                unreadable_count += 1
        inventory_lines.append(
            "\0".join((relative, str(size), content_sha256 or "<not-hashed>"))
        )
        if role in _JSON_ROLES:
            order_key = hashlib.sha256(relative.encode("utf-8")).hexdigest()
            json_candidates[role].append((order_key, path))

    shape_counts: dict[str, Counter[str]] = defaultdict(Counter)
    shape_examples: dict[str, dict[str, Any]] = defaultdict(dict)
    json_sampled_count = 0
    json_invalid_count = 0
    json_oversize_count = 0
    for role in sorted(json_candidates):
        candidates = sorted(json_candidates[role])[: policy.json_samples_per_role]
        for _, path in candidates:
            try:
                if path.stat().st_size > policy.max_json_bytes:
                    json_oversize_count += 1
                    continue
                value = _strict_json_loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
                json_invalid_count += 1
                continue
            shape = _json_shape(
                value,
                include_key_names=policy.include_json_key_names,
                depth=policy.max_shape_depth,
            )
            fingerprint = _shape_fingerprint(shape)
            shape_counts[role][fingerprint] += 1
            shape_examples[role][fingerprint] = shape
            json_sampled_count += 1

    inventory_sha256 = hashlib.sha256(
        json.dumps(
            inventory_lines,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    json_shapes = {
        role: [
            {
                "shape_sha256": fingerprint,
                "sample_count": count,
                "shape": shape_examples[role][fingerprint],
            }
            for fingerprint, count in sorted(shape_counts[role].items())
        ]
        for role in sorted(shape_counts)
    }
    probe_passed = not any(
        (
            symlink_count,
            unreadable_count,
            json_invalid_count,
            json_oversize_count,
        )
    )
    return {
        "schema_version": "tws-belief.armbench-structural-probe.v0.1",
        "shareability": (
            "local_only" if policy.include_json_key_names else "review_required"
        ),
        "contains_json_values": False,
        "contains_relative_paths": False,
        "json_key_mode": (
            "names" if policy.include_json_key_names else "sha256-prefix"
        ),
        "hash_mode": policy.hash_mode,
        "probe_passed": probe_passed,
        "inventory_sha256": inventory_sha256,
        "file_count": sum(role_counts.values()),
        "hashed_file_count": hashed_file_count,
        "total_bytes": total_bytes,
        "role_counts": dict(sorted(role_counts.items())),
        "suffix_counts": dict(sorted(suffix_counts.items())),
        "symlink_count": symlink_count,
        "unreadable_count": unreadable_count,
        "json_sampled_count": json_sampled_count,
        "json_invalid_count": json_invalid_count,
        "json_oversize_count": json_oversize_count,
        "json_shapes": json_shapes,
    }

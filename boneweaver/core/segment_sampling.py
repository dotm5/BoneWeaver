"""Diagnostic-only long segment sampling hints."""

from __future__ import annotations

import math
import statistics

from .models import SegmentSamplingHint


def build_sampling_hints(graph, *, ratio_warning, subdivision_max):
    lengths = [edge.rest_length for edge in graph.edges if edge.kind == "HIERARCHY_SEGMENT"]
    if not lengths:
        return ()
    reference = statistics.median(lengths)
    if reference <= 0.0:
        return ()
    hints = []
    for edge in graph.edges:
        if edge.kind != "HIERARCHY_SEGMENT":
            continue
        ratio = edge.rest_length / reference
        if ratio >= ratio_warning:
            hints.append(
                SegmentSamplingHint(
                    edge.edge_id, edge.rest_length, reference, ratio,
                    min(int(subdivision_max), max(0, math.ceil(ratio) - 1)),
                    "WARNING", "boneweaver.long_segment_sampling_hint",
                )
            )
    return tuple(sorted(hints, key=lambda hint: hint.edge_id))

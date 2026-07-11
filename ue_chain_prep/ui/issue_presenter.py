"""Human-readable presentation helpers for analysis issues."""

_ISSUE_SUMMARIES = {
    "UECP_TERMINAL_CANDIDATE_AMBIGUOUS": "末端方向存在歧义",
    "UECP_BRANCH_AMBIGUOUS": "分支主链存在歧义",
    "UECP_FORWARD_AXIS_AMBIGUOUS": "前向轴存在歧义",
    "UECP_TERMINAL_CANDIDATE_SCORE_TOO_LOW": "末端方向证据不足",
    "UECP_TERMINAL_SAFE_FALLBACK_USED": "末端使用安全推断",
}


def issue_summary(code, message, bone_name):
    """Return a concise issue label suitable for Blender's compact UI lists."""
    useful_message = message and message != code and not message.startswith("UECP_")
    summary = message if useful_message else _ISSUE_SUMMARIES.get(code, "需要检查")
    return f"{bone_name} · {summary}" if bone_name else summary

"""Translation registration; full message catalog is added with the final UI."""

import bpy

from .contracts import ADDON_ID


TRANSLATIONS = {
    "zh_HANS": {
        ("*", "UE Chain Prep"): "UE 骨链准备",
        ("Operator", "Analyze UE Bone Chains"): "分析 UE 骨骼链",
        ("Operator", "Apply Chain Conversion"): "应用骨链转换",
        ("Operator", "Validate Current Conversion"): "验证当前转换",
        ("Operator", "Toggle Chain Preview"): "切换骨链预览",
        ("Operator", "Restore UECP Snapshot"): "恢复 UECP 快照",
        ("Operator", "Export UECP Diagnostic Report"): "导出 UECP 诊断报告",
        ("Operator", "Clear UECP Runtime"): "清除 UECP 运行状态",
        ("Operator", "Inspect Active Hierarchy"): "检查活动骨骼层级",
        ("Operator", "Select Inspected Scope"): "选择检查范围",
        ("Operator", "Use Inspected Scope"): "将检查范围用于转换",
        ("Operator", "Set Branch Continuation"): "指定分叉主延续",
        ("Operator", "Clear Hierarchy Inspection"): "清除骨骼层级检查",
        ("Operator", "Discover Secondary Chains"): "发现次级骨链",
        ("Operator", "Confirm and Select Discovered Chain"): "确认并选择发现骨链",
        ("Operator", "Use Confirmed Discovered Chains"): "将确认骨链用于分析",
        ("Operator", "Clear Semantic Discovery"): "清除语义发现",
        ("Operator", "Export Semantic Discovery"): "导出语义发现",
        ("*", "Hierarchy Chain Inspection"): "骨骼链检查",
        ("*", "Semantic Chain Discovery"): "语义骨链发现",
        ("*", "Hierarchy Overlay Colors"): "骨骼层级叠加颜色",
        ("*", "Plan State"): "计划状态",
        ("*", "Weight Evidence"): "权重证据",
        ("*", "Preview & Diagnostics"): "预览与诊断",
        ("*", "Scope Mode"): "骨骼范围",
        ("*", "Mesh Scope"): "网格范围",
        ("*", "Physics Profile"): "物理配置",
        ("*", "Terminal Mode"): "末端推断模式",
        ("*", "Bone Forward Axis"): "导入前向轴",
        ("*", "Tip Length Mode"): "末端长度模式",
        ("*", "Roll Mode"): "Roll 模式",
        ("*", "Minimum Candidate Score"): "最低候选评分",
        ("*", "Candidate Minimum Margin"): "候选最低分差",
        ("*", "Minimum Confidence"): "最低置信度",
    }
}


def register() -> None:
    bpy.app.translations.register(ADDON_ID, TRANSLATIONS)


def unregister() -> None:
    try:
        bpy.app.translations.unregister(ADDON_ID)
    except RuntimeError:
        pass

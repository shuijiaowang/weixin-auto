"""
诊断微信 PC 版 UIAutomation 暴露模式（mmui::MainWindow vs Qt51514QWindowIcon）

在公司/家里各运行一次，对比输出的 JSON，找出差异项。
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import uiautomation as auto

WECHAT_TITLE = "微信"
MMUI_CLASS = "mmui::MainWindow"
QT_SHELL_PATTERNS = (
    "Qt51514QWindowIcon",
    "Qt51514QWindowForeign",
    "Qt51514QWindow",
    "qt51514QWindowIcon",
)


def _run_ps(script: str, timeout: int = 15) -> str:
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        return (r.stdout or "").strip()
    except Exception as e:
        return f"(error: {e})"


def collect_system_info() -> dict:
    os_info = _run_ps(
        "Get-CimInstance Win32_OperatingSystem | "
        "Select-Object Caption,Version,BuildNumber,OSArchitecture | ConvertTo-Json -Compress"
    )
    dpi = _run_ps(
        "Add-Type -AssemblyName System.Windows.Forms; "
        "[System.Windows.Forms.SystemInformation]::PrimaryMonitorSize; "
        "[System.Windows.Forms.SystemInformation]::WorkingArea; "
        "(Get-ItemProperty 'HKCU:\\Control Panel\\Desktop' -Name LogPixels -ErrorAction SilentlyContinue).LogPixels"
    )
    gpu = _run_ps(
        "Get-CimInstance Win32_VideoController | "
        "Select-Object Name,DriverVersion,AdapterRAM | ConvertTo-Json -Compress"
    )
    displays = _run_ps(
        "Get-CimInstance Win32_DesktopMonitor -ErrorAction SilentlyContinue | "
        "Select-Object ScreenWidth,ScreenHeight | ConvertTo-Json -Compress"
    )
    env_qt = {
        k: os.environ.get(k, "")
        for k in (
            "QT_OPENGL",
            "QT_ANGLE_PLATFORM",
            "QT_QUICK_BACKEND",
            "QT_ENABLE_HIGHDPI_SCALING",
            "QT_SCALE_FACTOR",
            "QT_AUTO_SCREEN_SCALE_FACTOR",
        )
    }
    return {
        "hostname": os.environ.get("COMPUTERNAME", ""),
        "python": sys.version.split()[0],
        "os": os_info,
        "dpi_raw": dpi,
        "gpu": gpu,
        "displays": displays,
        "qt_env": env_qt,
        "is_admin": _run_ps(
            "([Security.Principal.WindowsPrincipal]"
            "[Security.Principal.WindowsIdentity]::GetCurrent()"
            ").IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)"
        ),
    }


def find_wechat_exe() -> dict:
    """常见安装路径 + 正在运行进程"""
    candidates = [
        Path(r"C:\Program Files\Tencent\WeChat\WeChat.exe"),
        Path(r"C:\Program Files (x86)\Tencent\WeChat\WeChat.exe"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Tencent" / "WeChat" / "WeChat.exe",
    ]
    found = []
    for p in candidates:
        if p.is_file():
            try:
                ver = p.stat().st_mtime
            except OSError:
                ver = None
            found.append({"path": str(p), "exists": True, "mtime": ver})
    proc = _run_ps(
        "Get-Process WeChat,Weixin -ErrorAction SilentlyContinue | "
        "Select-Object Name,Id,Path | ConvertTo-Json -Compress"
    )
    return {"install_paths": found, "running_process": proc}


def list_top_level_wechat_windows() -> list[dict]:
    """枚举深度 1 的「微信」相关顶层窗口"""
    results = []
    root = auto.GetRootControl()
    for w in root.GetChildren():
        try:
            name = w.Name or ""
            cls = getattr(w, "ClassName", "") or ""
        except Exception:
            continue
        if WECHAT_TITLE not in name and not any(p.lower() in cls.lower() for p in ("wechat", "mmui", "qt51514")):
            continue
        if WECHAT_TITLE not in name and "mmui" not in cls and "Qt51514" not in cls:
            continue
        try:
            rect = w.BoundingRectangle
            pos = {
                "left": rect.left,
                "top": rect.top,
                "width": rect.width(),
                "height": rect.height(),
            }
        except Exception:
            pos = None
        child_count = -1
        try:
            child_count = len(w.GetChildren())
        except Exception:
            pass
        results.append(
            {
                "name": name,
                "class_name": cls,
                "control_type": w.ControlTypeName,
                "child_count": child_count,
                "rectangle": pos,
            }
        )
    return results


def classify_mode(windows: list[dict]) -> dict:
    mmui = [w for w in windows if w.get("class_name") == MMUI_CLASS]
    qt_shell = [
        w
        for w in windows
        if any(p in (w.get("class_name") or "") for p in QT_SHELL_PATTERNS)
    ]
    if mmui:
        primary = max(mmui, key=lambda x: x.get("child_count") or 0)
        mode = "mmui_full_tree"
        # mmui::MainWindow 出现时，通常意味着 UIA 能继续向下遍历（哪怕直系子节点数很少）
        uia_usable = True
    elif qt_shell:
        primary = qt_shell[0]
        mode = "qt_qwindow_canvas"
        # Qt51514QWindowIcon 往往是“纯画布”壳窗口，默认认为 UIA 不可用
        uia_usable = False
    else:
        primary = windows[0] if windows else {}
        mode = "unknown"
        uia_usable = False
    return {
        "mode": mode,
        "uia_likely_usable": uia_usable,
        "primary_window": primary,
        "mmui_windows": len(mmui),
        "qt_shell_windows": len(qt_shell),
    }


def probe_tree_depth() -> dict:
    """尝试按 ClassName 找主窗口并统计子树规模"""
    stats = {"by_class": {}}
    for cls in (MMUI_CLASS, "Qt51514QWindowIcon", "qt51514QWindowIcon"):
        try:
            w = auto.WindowControl(searchDepth=1, ClassName=cls)
            if not w.Exists(1):
                stats["by_class"][cls] = {"exists": False}
                continue
            n = _count_descendants(w, max_depth=8)
            stats["by_class"][cls] = {
                "exists": True,
                "name": w.Name,
                "direct_children": len(w.GetChildren()),
                "descendants_depth8": n,
            }
        except Exception as e:
            stats["by_class"][cls] = {"exists": False, "error": str(e)}

    w = auto.WindowControl(searchDepth=1, Name=WECHAT_TITLE)
    if w.Exists(1):
        stats["by_name_weixin"] = {
            "class_name": getattr(w, "ClassName", ""),
            "direct_children": len(w.GetChildren()),
            "descendants_depth8": _count_descendants(w, max_depth=8),
        }
    return stats


def _count_descendants(root: auto.Control, max_depth: int) -> int:
    count = 0
    queue = [(root, 0)]
    while queue:
        node, depth = queue.pop(0)
        if depth >= max_depth:
            continue
        try:
            children = node.GetChildren()
        except Exception:
            continue
        count += len(children)
        for c in children:
            queue.append((c, depth + 1))
    return count


def read_wechat_config_hints() -> dict:
    """读取可能相关的配置目录（不保证键名公开）"""
    base = Path(os.environ.get("APPDATA", "")) / "Tencent"
    hints = {"searched": [], "ini_snippets": []}
    if not base.is_dir():
        return hints
    for pattern in ("**/WeChat Files/**/config/*.ini", "**/WeChat/**/config.ini", "**/Weixin/**/config.ini"):
        for p in base.glob(pattern):
            hints["searched"].append(str(p))
            if len(hints["ini_snippets"]) >= 5:
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="replace")[:4000]
            except OSError:
                continue
            for line in text.splitlines():
                low = line.lower()
                if any(
                    k in low
                    for k in (
                        "gpu",
                        "opengl",
                        "angle",
                        "dpi",
                        "render",
                        "access",
                        "a11y",
                        "hardware",
                    )
                ):
                    hints["ini_snippets"].append({"file": str(p), "line": line.strip()})
    return hints


def main():
    print("正在收集系统与微信窗口信息（请先启动并登录微信）...\n")
    windows = list_top_level_wechat_windows()
    classification = classify_mode(windows)
    report = {
        "export_time": datetime.now().isoformat(timespec="seconds"),
        "classification": classification,
        "top_level_windows": windows,
        "tree_probe": probe_tree_depth(),
        "system": collect_system_info(),
        "wechat_binary": find_wechat_exe(),
        "config_hints": read_wechat_config_hints(),
        "recommendations": _recommendations(classification),
    }

    out = Path(f"wechat_ui_diagnose_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=== 结论 ===")
    print(f"模式: {classification['mode']}")
    print(f"UIA 可能可用: {classification['uia_likely_usable']}")
    if classification.get("primary_window"):
        pw = classification["primary_window"]
        print(f"主窗口 class: {pw.get('class_name')}")
        print(f"直接子控件数: {pw.get('child_count')}")
    print(f"\n完整报告: {out}")
    print("\n=== 建议（摘要）===")
    for line in report["recommendations"]:
        print(f"  - {line}")


def _recommendations(classification: dict) -> list[str]:
    mode = classification.get("mode")
    if mode == "mmui_full_tree":
        return [
            "当前为 mmui::MainWindow 模式，example.py 导出应能看到完整控件树。",
            "若要在本机复现家里的 Qt 画布模式：用 launch_wechat_gpu.bat 启动，并关闭讲述人/其它读屏。",
            "微信内：设置 → 关于微信 → 连点版本号 5 次，查看 Render / Composite Window 是否与家里不同。",
        ]
    if mode == "qt_qwindow_canvas":
        return [
            "当前为 Qt51514QWindowIcon 画布模式，子控件不会对 UIA 暴露。",
            "优先尝试：用 launch_wechat_uia.bat（软件渲染）完全退出微信后重启。",
            "其次：WeChat.exe → 兼容性 → 高 DPI →「系统」或「系统(增强)」。",
            "再次：Win+Ctrl+Enter 打开讲述人后再导出（触发无障碍完整 Provider）。",
            "公司机能用、家里不能用时，对比两份 diagnose JSON 的 gpu / dpi_raw / qt_env。",
        ]
    return [
        "未识别到典型微信主窗口，请确认微信已启动且窗口标题为「微信」。",
    ]


if __name__ == "__main__":
    main()

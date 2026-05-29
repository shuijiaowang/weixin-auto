"""
Check whether Weixin/WeChat process inherited Qt env vars.
Run AFTER launching WeChat via launch_wechat_gpu.cmd or launch_wechat_uia.cmd.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime

import uiautomation as auto

QT_KEYS = (
    "QT_OPENGL",
    "QT_ANGLE_PLATFORM",
    "QT_QUICK_BACKEND",
    "QSG_RHI_BACKEND",
    "QT_ENABLE_HIGHDPI_SCALING",
    "QT_GRAPHICSSYSTEM",
)


def list_wechat_pids() -> list[int]:
    ps = (
        "Get-Process Weixin,WeChat -ErrorAction SilentlyContinue | "
        "Select-Object -ExpandProperty Id"
    )
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    pids = []
    for line in (r.stdout or "").splitlines():
        line = line.strip()
        if line.isdigit():
            pids.append(int(line))
    return pids


def read_process_env_wmi(pid: int) -> dict[str, str]:
    """Read process environment block via WMI (may need admin on some systems)."""
    keys = ",".join(f"'{k}'" for k in QT_KEYS)
    ps = f"""
$p = Get-CimInstance Win32_Process -Filter "ProcessId={pid}"
if (-not $p) {{ exit 1 }}
$cmd = $p.CommandLine
$out = @{{ pid = {pid}; command_line = $cmd; qt = @{{}} }}
# Win32_Process does not expose full env; use CIM associator workaround
try {{
  $envs = (Get-WmiObject Win32_Process -Filter "ProcessId={pid}").GetOwner()
}} catch {{}}
# Fallback: parse only what we can from parent cmd if child inherited
$out | ConvertTo-Json -Compress
"""
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    try:
        return json.loads((r.stdout or "").strip() or "{}")
    except json.JSONDecodeError:
        return {"pid": pid, "raw": (r.stdout or "").strip(), "stderr": (r.stderr or "").strip()}


def window_class_for_pid(pid: int) -> list[dict]:
    rows = []
    root = auto.GetRootControl()
    for w in root.GetChildren():
        try:
            if getattr(w, "ProcessId", None) != pid:
                continue
            rows.append(
                {
                    "name": w.Name or "",
                    "class_name": getattr(w, "ClassName", "") or "",
                    "children": len(w.GetChildren()),
                }
            )
        except Exception:
            pass
    return rows


def main():
    pids = list_wechat_pids()
    if not pids:
        print("No Weixin/WeChat process found. Start WeChat first.")
        sys.exit(1)

    print(f"Found PIDs: {pids}\n")
    print("NOTE: diagnose JSON 'qt_env' is from Python shell, NOT WeChat process.\n")

    report = {"time": datetime.now().isoformat(timespec="seconds"), "processes": []}
    for pid in pids:
        info = read_process_env_wmi(pid)
        wins = window_class_for_pid(pid)
        entry = {"pid": pid, "wmi": info, "top_windows": wins}
        report["processes"].append(entry)
        print(f"--- PID {pid} ---")
        if info.get("command_line"):
            print(f"CommandLine: {info['command_line'][:200]}...")
        for w in wins:
            print(f"  window: class={w['class_name']!r} name={w['name']!r} children={w['children']}")
        print()

    out = f"wechat_process_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()

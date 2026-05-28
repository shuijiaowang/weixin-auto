"""
微信自动化脚本
"""
from wechat_automation import WeChatAutomation
import uiautomation as auto
import json
from datetime import datetime
import time
import argparse


def get_control_details(control, depth=0, max_depth=30):
    """递归获取所有控件的详细信息"""
    if depth > max_depth:
        return []
    
    details = []
    
    try:
        # 收集控件的基本信息
        info = {
            "depth": depth,
            "control_type": control.ControlTypeName,
            "name": control.Name if control.Name else "(无名称)",
            "automation_id": control.AutomationId if control.AutomationId else "",
            "class_name": control.ClassName if hasattr(control, 'ClassName') and control.ClassName else "",
        }
        
        # 尝试获取位置信息
        try:
            rect = control.BoundingRectangle
            info["position"] = {
                "x": rect.left,
                "y": rect.top,
                "width": rect.width(),
                "height": rect.height()
            }
        except:
            info["position"] = None
        
        # 尝试获取值
        try:
            if hasattr(control, 'GetValue'):
                info["value"] = control.GetValue()
            else:
                info["value"] = ""
        except:
            info["value"] = ""
        
        details.append(info)
        
        # 递归获取子控件
        try:
            children = control.GetChildren()
            for child in children:
                details.extend(get_control_details(child, depth + 1, max_depth))
        except:
            pass
    
    except Exception as e:
        pass
    
    return details


def export_all_data(wechat):
    """导出所有可见数据"""
    export_data = {
        "export_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "window_info": {
            "title": wechat.window.Name,
            "class": wechat.window.ClassName,
            "rectangle": {
                "left": wechat.window.BoundingRectangle.left,
                "top": wechat.window.BoundingRectangle.top,
                "width": wechat.window.BoundingRectangle.width(),
                "height": wechat.window.BoundingRectangle.height()
            }
        },
        "control_tree": [],
        "special_controls": {
            "buttons": [],
            "lists": [],
            "edit_boxes": [],
            "texts": [],
        }
    }
    
    # 1. 获取完整的控件树
    print("正在获取完整的控件树...")
    # 微信 UI 层级较深（例如 ChatInputView 可能已经在 depth=15），
    # 深度太小会导致输入框/工具按钮等子控件无法导出
    export_data["control_tree"] = get_control_details(wechat.window, max_depth=30)
    
    # 2. 按类型分类控件
    for ctrl_info in export_data["control_tree"]:
        ctrl_type = ctrl_info["control_type"]
        
        if "Button" in ctrl_type:
            export_data["special_controls"]["buttons"].append(ctrl_info)
        elif "List" in ctrl_type:
            export_data["special_controls"]["lists"].append(ctrl_info)
        elif "Edit" in ctrl_type:
            export_data["special_controls"]["edit_boxes"].append(ctrl_info)
        elif "Text" in ctrl_type:
            export_data["special_controls"]["texts"].append(ctrl_info)
    
    # 3. 特别处理：获取聊天列表的详细内容
    print("正在获取聊天列表详情...")
    try:
        session_list = wechat.window.ListControl(Name="会话", searchDepth=15)
        if session_list.Exists(3):
            chat_details = []
            for item in session_list.GetChildren():
                chat_info = {
                    "name": item.Name,
                    "automation_id": item.AutomationId if item.AutomationId else "",
                    "children_count": len(item.GetChildren()),
                    "children_details": []
                }
                
                # 获取子项的详细信息
                for child in item.GetChildren():
                    child_info = {
                        "type": child.ControlTypeName,
                        "name": child.Name if child.Name else "",
                        "value": "",
                    }
                    try:
                        child_info["value"] = child.GetValue()
                    except:
                        pass
                    chat_info["children_details"].append(child_info)
                
                chat_details.append(chat_info)
            
            export_data["chat_list"] = chat_details
            print(f"获取到 {len(chat_details)} 个聊天")
    except Exception as e:
        print(f"获取聊天列表失败: {e}")
    
    return export_data


def test_ctrl_f_search_and_collect(wechat: WeChatAutomation, keyword: str = "拼好饭"):
    """
    测试方法：Ctrl+F 搜索关键字，然后收集控件信息。
    :param wechat: 已 find_wechat_window 的实例
    :param keyword: 要搜索的关键字
    :return: 导出的数据 dict
    """
    if not wechat.window:
        raise RuntimeError("wechat.window 为空，请先执行 find_wechat_window()")

    # 尽量确保焦点在微信窗口上
    try:
        wechat.window.SetActive()
    except Exception:
        try:
            wechat.window.Click()
        except Exception:
            pass

    time.sleep(0.3)

    # Ctrl+F 打开搜索框并输入关键字
    wechat.ctrl_f_search(keyword, submit=False)
    time.sleep(0.3)
    # wechat.window.SendKeys("{Enter}")
    # time.sleep(0.8)

    # 搜索后导出控件信息（便于查看搜索结果界面出现了哪些控件）
    data = export_all_data(wechat)
    data["test_action"] = {"type": "ctrl_f_search", "keyword": keyword}
    return data


def interactive_search_and_open(wechat: WeChatAutomation):
    """
    交互式监听（极简版）：
    输入搜索内容 -> 过滤候选（排除小程序/网络结果）-> 100% 同名则点击进入；否则不执行。
    """
    if not wechat.window:
        raise RuntimeError("wechat.window 为空，请先执行 find_wechat_window()")

    print("\n交互模式：Ctrl+C 退出")
    print("说明：会过滤掉「最近使用过的小程序 / 搜索网络结果 / 互联网」区域，只在「最常使用/联系人/群聊」里精确匹配。\n")

    while True:
        keyword = input("请输入要搜索的内容：").strip()
        if not keyword:
            continue

        ok = wechat.ctrl_f_search(keyword, submit=False)
        if not ok:
            # 搜索失败：按你的要求，啥也不做
            continue

        time.sleep(0.6)
        candidates = wechat.get_search_candidates(allowed_sections=["最常使用", "联系人", "群聊"])

        if not candidates:
            continue

        # 只做 100% 精确匹配；不做选择/兜底
        exact = [c for c in candidates if c.get("name") == keyword]
        if len(exact) != 1:
            continue

        try:
            wechat._open_search_result_control(exact[0]["control"])
        except Exception:
            # 点击失败：按你的要求，啥也不做
            pass


def interactive_menu(wechat: WeChatAutomation):
    """
    简单集成的交互菜单：
    1：搜索用户/群并打开
    2：输入对话内容并回车发送
    3/4/5：预留
    """
    if not wechat.window:
        raise RuntimeError("wechat.window 为空，请先执行 find_wechat_window()")

    print("\n交互菜单：输入数字执行，q 退出")
    print("1) 搜索用户/群")
    print("2) 输入对话内容并回车发送")
    print("3) 粘贴文件并回车发送")
    print("4) (预留)")
    print("5) (预留)\n")

    while True:
        cmd = input("请输入操作（1/2/3/4/5/q）：").strip().lower()
        if cmd in {"q", "quit", "exit"}:
            return

        if cmd == "1":
            keyword = input("请输入要搜索的内容：").strip()
            if not keyword:
                continue

            ok = wechat.ctrl_f_search(keyword, submit=False)
            if not ok:
                continue

            time.sleep(0.6)
            candidates = wechat.get_search_candidates(allowed_sections=["最常使用", "联系人", "群聊"])
            if not candidates:
                continue

            exact = [c for c in candidates if c.get("name") == keyword]
            if len(exact) != 1:
                continue

            try:
                wechat._open_search_result_control(exact[0]["control"])
            except Exception:
                pass
            continue

        if cmd == "2":
            text = input("请输入要输入的文字：").strip()
            if text:
                wechat.input_text_and_enter(text)
            continue

        if cmd == "3":
            file_path = input("请输入要发送的文件完整路径：").strip()
            if file_path:
                wechat.paste_file_and_enter(file_path)
            continue

        if cmd in {"4", "5"}:
            print(f"{cmd} 功能未实现，等待后续需求。")
            continue


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="微信 UI 自动化测试")
    parser.add_argument(
        "--mode",
        choices=["interactive", "export", "ctrl-f-search", "type-enter", "paste-file"],
        default="interactive",
        help="运行模式：interactive=交互选择并点击进入；export=直接导出控件；ctrl-f-search=Ctrl+F 搜索后导出控件；type-enter=输入文字并按回车；paste-file=剪贴板粘贴文件并回车发送",
    )
    parser.add_argument("--keyword", default="拼好饭", help="ctrl-f-search 模式下的搜索关键字")
    parser.add_argument("--text", default="", help="type-enter 模式下要输入的文字（留空则交互输入）")
    parser.add_argument("--file", default="", help="paste-file 模式下要发送的文件完整路径")
    args = parser.parse_args()

    wechat = WeChatAutomation()

    if not wechat.find_wechat_window():
        print("请先启动微信！")
        return

    print("微信已启动")

    if args.mode == "interactive":
        interactive_menu(wechat)
        return
    elif args.mode == "ctrl-f-search":
        print(f"\n开始 Ctrl+F 搜索：{args.keyword}\n")
        all_data = test_ctrl_f_search_and_collect(wechat, args.keyword)
    elif args.mode == "type-enter":
        text = (args.text or "").strip()
        if not text:
            text = input("请输入要输入的文字：").strip()
        if text:
            wechat.input_text_and_enter(text)
        return
    elif args.mode == "paste-file":
        file_path = (args.file or "").strip()
        if not file_path:
            file_path = input("请输入要发送的文件完整路径：").strip()
        if file_path:
            wechat.paste_file_and_enter(file_path)
        return
    else:
        print("\n开始导出所有可见数据...\n")
        all_data = export_all_data(wechat)

    # 保存到文件
    filename = f"wechat_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    print(f"\n数据已导出到: {filename}")
    print(f"总共获取 {len(all_data['control_tree'])} 个控件")
    print(f"按钮: {len(all_data['special_controls']['buttons'])} 个")
    print(f"列表: {len(all_data['special_controls']['lists'])} 个")
    print(f"编辑框: {len(all_data['special_controls']['edit_boxes'])} 个")
    print(f"文本: {len(all_data['special_controls']['texts'])} 个")
    print(f"聊天: {len(all_data.get('chat_list', []))} 个")


if __name__ == "__main__":
    main()

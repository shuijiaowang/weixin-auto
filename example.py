"""
微信自动化脚本
"""
from wechat_automation import WeChatAutomation
import uiautomation as auto
import json
from datetime import datetime


def get_control_details(control, depth=0, max_depth=15):
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
    export_data["control_tree"] = get_control_details(wechat.window)
    
    # 2. 按类型分类控件
    for ctrl_info in export_data["control_tree"]:
        ctrl_type = ctrl_info["control_type"]
        
        if "Button" in ctrl_type:
            export_data["special_controls"]["buttons"].append(ctrl_info)
        elif "List" in ctrl_type:
            export_data["special_controls"]["lists"].append(ctrl_info)
        elif "Edit" in ctrl_type or "Text" in ctrl_type:
            if ctrl_info["value"]:
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


def main():
    """主函数"""
    wechat = WeChatAutomation()
    
    if not wechat.find_wechat_window():
        print("请先启动微信！")
        return
    
    print("微信已启动")
    print("\n开始导出所有可见数据...\n")
    
    # 导出所有数据
    all_data = export_all_data(wechat)
    
    # 保存到文件
    filename = f"wechat_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n数据已导出到: {filename}")
    print(f"总共获取 {len(all_data['control_tree'])} 个控件")
    print(f"按钮: {len(all_data['special_controls']['buttons'])} 个")
    print(f"列表: {len(all_data['special_controls']['lists'])} 个")
    print(f"聊天: {len(all_data.get('chat_list', []))} 个")


if __name__ == "__main__":
    main()

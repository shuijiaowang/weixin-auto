"""
微信自动化核心模块
基于 uiautomation 库实现微信的自动化操作
"""
import time
import uiautomation as auto
from typing import Optional, List
from config import WECHAT_WINDOW_NAME, TIMEOUT, SLEEP_TIME, DEBUG


class WeChatAutomation:
    """微信自动化操作类"""
    
    def __init__(self):
        self.window = None
        self.is_wechat_running = False
        
    def find_wechat_window(self) -> bool:
        """
        查找微信主窗口
        :return: 是否找到微信窗口
        """
        try:
            self.window = auto.WindowControl(searchDepth=1, Name=WECHAT_WINDOW_NAME)
            if self.window.Exists(3):
                self.is_wechat_running = True
                if DEBUG:
                    print(f"[成功] 找到微信窗口: {self.window.Name}")
                return True
            else:
                self.is_wechat_running = False
                if DEBUG:
                    print("[失败] 未找到微信窗口，请确保微信已启动")
                return False
        except Exception as e:
            if DEBUG:
                print(f"[错误] 查找微信窗口时出错: {e}")
            return False
    
    def get_chat_window(self) -> Optional[auto.Control]:
        """
        获取聊天窗口控件
        :return: 聊天窗口控件
        """
        if not self.window:
            return None
        
        try:
            # 获取微信主窗口的聊天区域
            chat_list = self.window.ListControl(searchDepth=8)
            return chat_list
        except Exception as e:
            if DEBUG:
                print(f"[错误] 获取聊天窗口时出错: {e}")
            return None
    
    def search_chat(self, chat_name: str) -> bool:
        """
        搜索并打开指定聊天
        :param chat_name: 聊天名称（联系人或群名）
        :return: 是否成功
        """
        if not self.window:
            return False

        # 兼容旧行为：Ctrl+F -> 输入 -> Enter 直接打开（存在同名误开风险）
        try:
            ok = self.ctrl_f_search(chat_name, submit=True)
            if ok and DEBUG:
                print(f"[成功] 已打开聊天: {chat_name}")
            return ok
        except Exception as e:
            if DEBUG:
                print(f"[错误] 搜索聊天时出错: {e}")
            return False

    def _activate_window(self):
        """激活微信窗口（尽量保证键盘焦点正确）"""
        if not self.window:
            return
        try:
            self.window.SetActive()
        except Exception:
            try:
                self.window.Click()
            except Exception:
                pass

    def ctrl_f_search(self, keyword: str, clear_first: bool = True, submit: bool = False) -> bool:
        """
        Ctrl+F 打开搜索框并输入关键字。
        :param keyword: 搜索关键字
        :param clear_first: 是否先 Ctrl+A 清空再输入
        :param submit: 是否按 Enter 提交（默认 False；避免误打开同名项）
        """
        if not self.window:
            return False

        try:
            self._activate_window()
            time.sleep(0.2)
            self.window.SendKeys("{Ctrl}F")
            time.sleep(0.2)
            if clear_first:
                self.window.SendKeys("{Ctrl}A")
                time.sleep(0.05)
                self.window.SendKeys("{Delete}")
                time.sleep(0.05)
            self.window.SendKeys(keyword)
            time.sleep(max(SLEEP_TIME * 0.5, 0.2))
            if submit:
                self.window.SendKeys("{Enter}")
                time.sleep(max(SLEEP_TIME * 0.8, 0.4))
            return True
        except Exception as e:
            if DEBUG:
                print(f"[错误] Ctrl+F 搜索时出错: {e}")
            return False

    def _open_search_result_control(self, ctrl: auto.Control) -> None:
        """
        打开搜索结果项：优先 Invoke，其次 Click。
        不做额外兜底（按你的要求：失败就失败，不再做 Enter / 聚焦等策略）。
        """
        if hasattr(ctrl, "Invoke"):
            ctrl.Invoke()
            return
        ctrl.Click()

    def _walk_descendants(self, root: auto.Control, max_depth: int = 10):
        """按 UI 顺序粗略遍历子孙控件（避免过深导致性能问题）"""
        queue = [(root, 0)]
        while queue:
            node, depth = queue.pop(0)
            yield node, depth
            if depth >= max_depth:
                continue
            try:
                children = node.GetChildren()
            except Exception:
                children = []
            for child in children:
                queue.append((child, depth + 1))

    def get_search_candidates(
        self,
        allowed_sections: Optional[List[str]] = None,
        max_depth: int = 12,
    ) -> List[dict]:
        """
        获取 Ctrl+F 搜索结果候选项，只在指定分组内返回。
        依赖控件特征：
        - 分组标题：class_name=mmui::XTableCell，name=最常使用/联系人/群聊/...
        - 结果项：class_name=mmui::SearchContentCellView，automation_id=search_item_xxx
        """
        if not self.window:
            return []

        allowed = allowed_sections or ["最常使用", "联系人", "群聊"]
        stop_section_names = {"最近使用过的小程序", "搜索网络结果", "互联网"}

        # 收集所有 ListItemControl（并按屏幕位置排序，尽量还原 UI 顺序）
        items = []
        for ctrl, _depth in self._walk_descendants(self.window, max_depth=max_depth):
            try:
                if ctrl.ControlTypeName != "ListItemControl":
                    continue
            except Exception:
                continue

            try:
                rect = ctrl.BoundingRectangle
                pos = (rect.top, rect.left)
            except Exception:
                pos = (10**9, 10**9)

            try:
                items.append(
                    (
                        pos,
                        {
                            "name": ctrl.Name or "",
                            "automation_id": ctrl.AutomationId or "",
                            "class_name": getattr(ctrl, "ClassName", "") or "",
                            "control": ctrl,
                            "position": pos,
                        },
                    )
                )
            except Exception:
                continue

        items.sort(key=lambda x: x[0])

        current_section = None
        candidates: List[dict] = []

        for _pos, info in items:
            name = info["name"]
            class_name = info["class_name"]
            automation_id = info["automation_id"]

            # 标题分组
            if class_name == "mmui::XTableCell" and not automation_id:
                if name in stop_section_names:
                    current_section = None
                elif name in allowed:
                    current_section = name
                else:
                    current_section = None
                continue

            # 结果项
            if (
                current_section in allowed
                and class_name == "mmui::SearchContentCellView"
                and automation_id.startswith("search_item_")
            ):
                candidates.append(
                    {
                        "section": current_section,
                        "name": name,
                        "automation_id": automation_id,
                        "class_name": class_name,
                        "control": info["control"],
                    }
                )

        return candidates

    def open_from_search_candidates(
        self,
        target_name: str,
        allowed_sections: Optional[List[str]] = None,
        match_mode: str = "exact",
    ) -> dict:
        """
        从 Ctrl+F 搜索候选里精确匹配并点击打开，避免直接 Enter 造成同名误开。
        :return: 选中项信息（包含 section/name/automation_id）
        """
        allowed = allowed_sections or ["最常使用", "联系人", "群聊"]
        candidates = self.get_search_candidates(allowed_sections=allowed)

        def is_match(candidate_name: str) -> bool:
            if match_mode == "exact":
                return candidate_name == target_name
            if match_mode == "contains":
                return target_name in candidate_name
            raise ValueError("match_mode 仅支持 exact/contains")

        # 按分组优先级选择
        matched = [c for c in candidates if is_match(c["name"])]
        if not matched:
            raise RuntimeError(f"未找到匹配项: {target_name}")

        for section in allowed:
            same_section = [c for c in matched if c["section"] == section]
            if len(same_section) == 1:
                chosen = same_section[0]
                self._open_search_result_control(chosen["control"])
                time.sleep(max(SLEEP_TIME * 0.8, 0.4))
                return {k: v for k, v in chosen.items() if k != "control"}
            if len(same_section) > 1:
                names = [c["name"] for c in same_section]
                raise RuntimeError(f"匹配到多个同名项（分组={section}）：{names}")

        # 理论上不会到这里：matched 但不在 allowed
        raise RuntimeError("匹配到了结果，但不在允许分组内")
    
    def send_message(self, message: str) -> bool:
        """
        发送消息
        :param message: 消息内容
        :return: 是否成功
        """
        if not self.window:
            return False

    def input_text_and_enter(self, text: str, clear_first: bool = False) -> bool:
        """
        选中聊天输入框 -> 输入文字 -> 触发回车键。
        :param text: 要输入并发送的文字
        :param clear_first: 是否先 Ctrl+A/Delete 清空输入框（默认 False）
        """
        if not self.window:
            return False

        try:
            self._activate_window()
            time.sleep(0.2)

            # 优先使用稳定的 automation_id（来自导出的控件树：chat_input_field）
            input_box = self.window.EditControl(AutomationId="chat_input_field", searchDepth=20)
            if not input_box.Exists(1):
                # 兜底：兼容旧逻辑（不做更多策略）
                input_box = self.window.EditControl(searchDepth=15)

            if not input_box.Exists(3):
                if DEBUG:
                    print("[失败] 未找到聊天输入框")
                return False

            input_box.Click()
            time.sleep(max(SLEEP_TIME * 0.5, 0.2))

            if clear_first:
                try:
                    input_box.SendKeys("{Ctrl}A")
                    time.sleep(0.05)
                    input_box.SendKeys("{Delete}")
                    time.sleep(0.05)
                except Exception:
                    # 清空失败不影响后续输入（按你的要求：不做额外修复/循环）
                    pass

            input_box.SendKeys(text)
            time.sleep(max(SLEEP_TIME * 0.5, 0.2))
            input_box.SendKeys("{Enter}")
            time.sleep(max(SLEEP_TIME * 0.8, 0.3))

            if DEBUG:
                print(f"[成功] 已输入并回车: {text}")
            return True
        except Exception as e:
            if DEBUG:
                print(f"[错误] 输入并回车时出错: {e}")
            return False
        
        try:
            # 定位到消息输入框
            input_box = self.window.EditControl(searchDepth=15)
            
            if input_box.Exists(3):
                input_box.Click()
                time.sleep(0.5)
                
                # 清空输入框
                input_box.SendKeys('{Ctrl}A')
                input_box.SendKeys('{Delete}')
                time.sleep(0.3)
                
                # 输入消息
                input_box.SendKeys(message)
                time.sleep(0.5)
                
                # 发送消息（Ctrl+Enter 或 Enter）
                input_box.SendKeys('{Ctrl}{Enter}')
                time.sleep(SLEEP_TIME)
                
                if DEBUG:
                    print(f"[成功] 已发送消息: {message}")
                return True
            else:
                if DEBUG:
                    print("[失败] 未找到消息输入框")
                return False
                
        except Exception as e:
            if DEBUG:
                print(f"[错误] 发送消息时出错: {e}")
            return False
    
    def get_chat_list(self) -> List[str]:
        """
        获取聊天列表
        :return: 聊天名称列表
        """
        chat_names = []
        
        if not self.window:
            return chat_names
        
        try:
            # 获取聊天列表控件
            chat_list = self.window.ListControl(Name="会话", searchDepth=8)
            
            if chat_list.Exists(3):
                # 获取所有聊天项
                for item in chat_list.GetChildren():
                    name = item.Name
                    if name:
                        chat_names.append(name)
            
            if DEBUG:
                print(f"[成功] 获取到 {len(chat_names)} 个聊天")
            
        except Exception as e:
            if DEBUG:
                print(f"[错误] 获取聊天列表时出错: {e}")
        
        return chat_names
    
    def get_latest_messages(self, count: int = 10) -> List[str]:
        """
        获取最新的消息
        :param count: 获取消息数量
        :return: 消息列表
        """
        messages = []
        
        if not self.window:
            return messages
        
        try:
            # 获取消息列表控件
            msg_list = self.window.ListControl(searchDepth=15)
            
            if msg_list.Exists(3):
                items = msg_list.GetChildren()
                # 获取最新的消息
                for item in items[-count:]:
                    name = item.Name
                    if name:
                        messages.append(name)
            
            if DEBUG:
                print(f"[成功] 获取到 {len(messages)} 条消息")
            
        except Exception as e:
            if DEBUG:
                print(f"[错误] 获取消息时出错: {e}")
        
        return messages
    
    def screenshot_chat(self, filepath: str = None) -> bool:
        """
        对当前聊天窗口截图
        :param filepath: 保存路径
        :return: 是否成功
        """
        if not self.window:
            return False
        
        try:
            if filepath is None:
                filepath = f"screenshot_{int(time.time())}.png"
            
            # 截图整个微信窗口
            self.window.CaptureToImage(filepath)
            
            if DEBUG:
                print(f"[成功] 截图已保存: {filepath}")
            return True
            
        except Exception as e:
            if DEBUG:
                print(f"[错误] 截图时出错: {e}")
            return False
    
    def minimize_window(self) -> bool:
        """最小化微信窗口"""
        if not self.window:
            return False
        
        try:
            self.window.Minimize()
            if DEBUG:
                print("[成功] 微信窗口已最小化")
            return True
        except Exception as e:
            if DEBUG:
                print(f"[错误] 最小化窗口时出错: {e}")
            return False
    
    def maximize_window(self) -> bool:
        """最大化微信窗口"""
        if not self.window:
            return False
        
        try:
            self.window.Maximize()
            if DEBUG:
                print("[成功] 微信窗口已最大化")
            return True
        except Exception as e:
            if DEBUG:
                print(f"[错误] 最大化窗口时出错: {e}")
            return False


def main():
    """测试示例"""
    wechat = WeChatAutomation()
    
    # 查找微信窗口
    if wechat.find_wechat_window():
        print("微信已启动，可以开始自动化操作")
        
        # 示例：获取聊天列表
        chats = wechat.get_chat_list()
        print(f"当前聊天列表: {chats}")
        
        # 示例：截图
        # wechat.screenshot_chat("test_screenshot.png")
    else:
        print("请先启动微信")


if __name__ == "__main__":
    main()

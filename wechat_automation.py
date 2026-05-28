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
        
        try:
            # 点击搜索按钮（Ctrl+F）
            self.window.SendKeys('{Ctrl}F')
            time.sleep(SLEEP_TIME)
            
            # 输入搜索内容
            self.window.SendKeys(chat_name)
            time.sleep(SLEEP_TIME * 2)
            
            # 按回车打开聊天
            self.window.SendKeys('{Enter}')
            time.sleep(SLEEP_TIME)
            
            if DEBUG:
                print(f"[成功] 已打开聊天: {chat_name}")
            return True
            
        except Exception as e:
            if DEBUG:
                print(f"[错误] 搜索聊天时出错: {e}")
            return False
    
    def send_message(self, message: str) -> bool:
        """
        发送消息
        :param message: 消息内容
        :return: 是否成功
        """
        if not self.window:
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

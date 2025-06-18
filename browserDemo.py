import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog
from datetime import datetime
from openai import OpenAI
import asyncio
from langchain_openai import ChatOpenAI
from browser_use import Agent, Browser, BrowserConfig
from pydantic import SecretStr
import threading
import sys
from dotenv import load_dotenv
import os

# 从.env文件加载环境变量
load_dotenv()

# 选择浏览器路径
def select_browser_path():
    root = tk.Tk()
    root.withdraw()
    browser_path = filedialog.askopenfilename(
        title="选择浏览器",
        filetypes=[("Executable Files", "*.exe")],
        initialdir=""
    )
    return browser_path

chrome_path = select_browser_path()
if not chrome_path:
    print("未选择浏览器路径，程序将退出。")
    sys.exit(1)

try:
    print("浏览器选择：", chrome_path)
    browser = Browser(
        config=BrowserConfig(
            chrome_instance_path=chrome_path,
        )
    )
except Exception as e:
    print(f"浏览器初始化失败: {e}")
    sys.exit(1)

try:
    llm = ChatOpenAI(
        base_url='https://api.deepseek.com/v1',
        model='deepseek-chat',
        api_key=SecretStr(os.getenv("OPENAI_API_KEY"))
    )
except Exception as e:
    print(f"LLM 初始化失败: {e}")
    sys.exit(1)

def save_to_file(file, content, is_question=False):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if is_question:
        file.write(f"\n[{timestamp}] Question:\n{content}\n\n[{timestamp}] Answer:\n")
    else:
        file.write(content)

def send_query_to_openai(query, conversation_history, file, chat_history):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url="https://api.deepseek.com")
    conversation_history.append({"role": "user", "content": query})
    save_to_file(file, query, is_question=True)
    try:
        response1 = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": "你是一个助手"}] + conversation_history,
            max_tokens=1024,
            temperature=0.7,
            stream=True
        )
        answer = ""
        for chunk in response1:
            content = chunk.choices[0].delta.content
            if content:
                print(content)
                answer += content
                chat_history.insert(tk.END, f"{content}")
                chat_history.yview(tk.END)
                chat_history.update()
        save_to_file(file, answer)
        conversation_history.append({"role": "assistant", "content": answer})
        return answer
    except Exception as e:
        error_msg = f"请求错误: {str(e)}\n"
        print(error_msg)
        save_to_file(file, error_msg)
        return error_msg

async def async_open_browser(task_description):
    try:
        agent = Agent(
            task=task_description,
            llm=llm,
            browser=browser,
            use_vision=False
        )
        result = await agent.run(100)
        print("Agent 输出：")
        print(result)
    except Exception as e:
        print(f"执行任务时发生错误：{e}")
    finally:
        await browser.close()

def open_browser(task_description):
    threading.Thread(target=asyncio.run, args=(async_open_browser(task_description),)).start()

def create_gui():
    root = tk.Tk()
    root.title("deepseek 查询助手")
    root.geometry("500x400")

    def show_help():
        messagebox.showinfo("帮助", "欢迎使用 deepseek 查询助手！\n\n"
                            "1. 在输入框中输入您的问题，然后点击“发送”或按回车键。\n"
                            "2. 在任务描述框中输入任务描述，然后点击“打开浏览器”以执行浏览器任务。\n"
                            "3. 所有对话将保存到本地文件 'docling.txt' 中。")

    chat_history = scrolledtext.ScrolledText(root, width=60, height=15, wrap=tk.WORD)
    chat_history.pack(pady=10)

    user_input = tk.Entry(root, width=60)
    user_input.pack(pady=10)

    task_input = tk.Entry(root, width=60)
    task_input.insert(0, "")
    task_input.pack(pady=10)

    with open("docling.txt", "a", encoding="utf-8") as file:
        conversation_history = []

        def on_send_button_click():
            query = user_input.get().strip()
            if query:
                chat_history.insert(tk.END, f"{query}\n\n")
                chat_history.yview(tk.END)
                user_input.delete(0, tk.END)
                send_query_to_openai(query, conversation_history, file, chat_history)

        send_button = tk.Button(root, text="发送", width=20, command=on_send_button_click)
        send_button.pack()
        user_input.bind("<Return>", lambda event: on_send_button_click())

        def on_browser_button_click():
            task_description = task_input.get().strip()
            if task_description:
                open_browser(task_description)
            else:
                messagebox.showwarning("警告", "请输入任务描述！")

        browser_button = tk.Button(root, text="打开浏览器", width=20, command=on_browser_button_click)
        browser_button.pack()

        help_button = tk.Button(root, text="帮助", width=20, command=show_help)
        help_button.pack(pady=10)

        root.mainloop()

if __name__ == "__main__":
    create_gui()
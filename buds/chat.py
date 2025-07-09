#!/usr/bin/env python3
import os
import threading
import logging
from collections import defaultdict, deque
from dotenv import load_dotenv
import telebot
from openai import OpenAI

# ─── Conversation Manager ────────────────────────────────────────────────────────
class ConversationManager:
    """
    Keeps per-chat histories as deques of {role, content} dicts.
    Automatically trims old messages to respect a turn-limit.
    Thread-safe for multi-bot setups.
    """
    def __init__(self, max_turns: int = 30):
        self._histories = defaultdict(lambda: deque(maxlen=max_turns))
        self._lock = threading.Lock()

    def add_message(self, chat_id: int, role: str, content: str):
        with self._lock:
            self._histories[chat_id].append({"role": role, "content": content})

    def get_history(self, chat_id: int):
        with self._lock:
            return list(self._histories[chat_id])

    def clear(self, chat_id: int):
        with self._lock:
            self._histories.pop(chat_id, None)

conv_mgr = ConversationManager(max_turns=30)
SYSTEM_PROMPT = {"role": "system", "content": "You are a helpful assistant that remembers the conversation."}

# Initialize the AI client directly here
load_dotenv()
_ai_client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1"
)

def register(botApp):

    @botApp.cmd('chat', 'Ask DeepSeek anything: /chat <your question>')
    def chat(msg):
        chat_id = msg.chat.id
        prompt = msg.text.partition(' ')[2].strip()
        if not prompt:
            return botApp.bot.reply_to(msg, "Usage: /chat <your question>")

        conv_mgr.add_message(chat_id, "user", prompt)
        history = [SYSTEM_PROMPT] + conv_mgr.get_history(chat_id)

        botApp.bot.send_chat_action(chat_id, 'typing')

        logging.info(f"[{chat_id}] Prompt: {prompt}")
        try:
            resp = _ai_client.chat.completions.create(
                model="deepseek-chat",
                messages=history
            )
            answer = resp.choices[0].message.content.strip()

            conv_mgr.add_message(chat_id, "assistant", answer)

            MAX_MSG_LEN = 4000
            for i in range(0, len(answer), MAX_MSG_LEN):
                botApp.bot.send_message(chat_id, answer[i:i + MAX_MSG_LEN])

        except Exception as e:
            logging.error(f"Chat error: {e}")
            botApp.bot.send_message(chat_id, f"Error: {e}")

    @botApp.cmd('chat_wipe', 'Wipe the memory for this chat')
    def chat_wipe(msg):
        conv_mgr.clear(msg.chat.id)
        botApp.bot.reply_to(msg, "🧠 Memory wiped for this chat.")

    @botApp.cmd('chat_context', 'Show the current conversation context')
    def chat_context(msg):
        chat_id = msg.chat.id
        history = [SYSTEM_PROMPT] + conv_mgr.get_history(chat_id)

        header = f"🧠 Current memory window: *{conv_mgr._histories[chat_id].maxlen} turns*\n"
        formatted = []
        for m in history:
            role = m["role"]
            content = m["content"]
            formatted.append(f"{role.upper()}:\n{content}")

        full_context = header + "\n\n" + "\n\n".join(formatted)

        MAX_MSG_LEN = 4000
        for i in range(0, len(full_context), MAX_MSG_LEN):
            botApp.bot.send_message(chat_id, full_context[i:i + MAX_MSG_LEN])

    @botApp.cmd('chat_range', 'Show the memory range max turns\n/chat_range [<number>] to set it')
    def chat_range(msg):
        chat_id = msg.chat.id
        args = msg.text.split(maxsplit=1)

        with conv_mgr._lock:
            old_max = conv_mgr._histories[chat_id].maxlen

            if len(args) == 1:
                return botApp.bot.send_message(
                    chat_id,
                    f"🔁 Current memory range: *{old_max} turns*\n `/chat_range <number>` to set a new value",
                    parse_mode='Markdown'
                )

            try:
                new_max = int(args[1])
                if new_max < 1 or new_max > 1000:
                    raise ValueError

                new_deque = deque(conv_mgr._histories[chat_id], maxlen=new_max)
                conv_mgr._histories[chat_id] = new_deque

                botApp.bot.send_message(
                    chat_id,
                    f"✅ Memory range updated:\nOld: *{old_max} turns*\nNew: *{new_max} turns*",
                    parse_mode='Markdown'
                )
            except ValueError:
                botApp.bot.send_message(
                    chat_id,
                    "❌ Invalid value. Use: `/chat_range 30` (between 1 and 1000)",
                    parse_mode='Markdown'
                )

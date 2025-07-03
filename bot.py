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
    def __init__(self, max_turns: int = 20):
        self._histories = defaultdict(lambda: deque(maxlen=max_turns))
        self._lock = threading.Lock()

    def add_message(self, chat_id: int, role: str, content: str):
        with self._lock:
            self._histories[chat_id].append({"role": role, "content": content})

    def get_history(self, chat_id: int):
        with self._lock:
            # return a shallow copy to avoid outside mutation
            return list(self._histories[chat_id])

    def clear(self, chat_id: int):
        with self._lock:
            self._histories.pop(chat_id, None)

conv_mgr = ConversationManager(max_turns=30)
SYSTEM_PROMPT = {"role": "system", "content": "You are a helpful assistant that remembers the conversation."}


def register_handlers(bot: telebot.TeleBot, ds_client: OpenAI):
    # per-bot registry of commands
    commands: list[tuple[str, str]] = []

    def cmd(name: str, desc: str, **handler_kwargs):
        def decorator(func):
            commands.append((name, desc))
            bot.message_handler(commands=[name], **handler_kwargs)(func)
            return func
        return decorator

    @cmd('chatid', 'Show this chat’s ID')
    def chat_id(msg):
        bot.reply_to(msg, f"Chat ID is: `{msg.chat.id}`")

    @cmd('chat', 'Ask DeepSeek anything: /chat <your question>')
    def ask_ds(msg):
        chat_id = msg.chat.id
        prompt = msg.text.partition(' ')[2].strip()
        if not prompt:
            return bot.reply_to(msg, "Usage: /chat <your question>")

        # 1) record the user message
        conv_mgr.add_message(chat_id, "user", prompt)

        # 2) build the full context
        history = [SYSTEM_PROMPT] + conv_mgr.get_history(chat_id)

        bot.send_chat_action(chat_id, 'typing')

        logging.info(f"[{chat_id}] Prompt: {prompt}")
        try:
            resp = ds_client.chat.completions.create(
                model="deepseek-chat",
                messages=history
            )
            answer = resp.choices[0].message.content.strip()

            # 3) record the assistant reply
            conv_mgr.add_message(chat_id, "assistant", answer)

            MAX_MSG_LEN = 4000
            for i in range(0, len(answer), MAX_MSG_LEN):
                bot.send_message(chat_id, answer[i:i + MAX_MSG_LEN])

        except Exception as e:
            bot.send_message(chat_id, f"Error: {e}")

    @cmd('chat_wipe', 'Wipe the memory for this chat')
    def wipe_chat(msg):
        conv_mgr.clear(msg.chat.id)
        bot.reply_to(msg, "🧠 Memory wiped for this chat.")

    @cmd('chat_context', 'Show the current conversation context')
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
            bot.send_message(chat_id, full_context[i:i + MAX_MSG_LEN], parse_mode=None)

    @cmd('chat_range', 'Show the memory range max turns\n/chat_range [<number>] to set it')
    def chat_range(msg):
        chat_id = msg.chat.id
        args = msg.text.split(maxsplit=1)

        with conv_mgr._lock:
            old_max = conv_mgr._histories[chat_id].maxlen

            if len(args) == 1:
                return bot.send_message(chat_id, f"🔁 Current memory range: *{old_max} turns*\n `/chat_range <number>` to set a new value", parse_mode='Markdown')

            try:
                new_max = int(args[1])
                if new_max < 1 or new_max > 1000:
                    raise ValueError

                # Replace the old deque with a new one
                new_deque = deque(conv_mgr._histories[chat_id], maxlen=new_max)
                conv_mgr._histories[chat_id] = new_deque

                bot.send_message(chat_id, f"✅ Memory range updated:\nOld: *{old_max} turns*\nNew: *{new_max} turns*", parse_mode='Markdown')
            except ValueError:
                bot.send_message(chat_id, "❌ Invalid value. Use: `/chat_range 30` (between 1 and 1000)", parse_mode='Markdown')

    @cmd('help', 'Show this help message')
    def help_command(msg):
        help_lines = "\n".join(f"/{n} — {d}" for n, d in commands)
        bot.send_message(msg.chat.id, help_lines)

    @bot.message_handler(func=lambda m: True)
    def debug_all(m):
        print(f"[{bot.token[:8]}] got update:", m)

    # register commands with Telegram's command menu
    bot.set_my_commands([
        telebot.types.BotCommand(name, desc)
        for name, desc in commands
    ])


def run_bot(bot: telebot.TeleBot):
    print(f"🤖 Bot {bot.token[:8]} starting…")
    bot.infinity_polling(skip_pending=True)


if __name__ == "__main__":
    load_dotenv()
    TG1 = os.getenv("TG_TOKEN_1")
    TG2 = os.getenv("TG_TOKEN_2")
    DS_KEY = os.getenv("DEEPSEEK_API_KEY")
    if not (TG1 and TG2 and DS_KEY):
        raise RuntimeError("TG_TOKEN_1, TG_TOKEN_2 and DEEPSEEK_API_KEY must all be set")

    logging.basicConfig(level=logging.INFO)
    telebot.logger.setLevel(logging.INFO)
    ds = OpenAI(api_key=DS_KEY, base_url="https://api.deepseek.com/v1")

    bot1 = telebot.TeleBot(TG1)
    #bot2 = telebot.TeleBot(TG2)

    register_handlers(bot1, ds)
    #register_handlers(bot2, ds)

    t1 = threading.Thread(target=run_bot, args=(bot1,), daemon=True)
    #t2 = threading.Thread(target=run_bot, args=(bot2,), daemon=True)
    t1.start()
    #t2.start()
    t1.join()
    #t2.join()


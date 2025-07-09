import os
import logging
from dotenv import load_dotenv
import telebot

# Buds
import buds.basic as basic_bud
import buds.chat as chat_bud
import buds.pm as pm_bud

class BotApp:
    def __init__(self, token):
        self.bot = telebot.TeleBot(token)
        self.commands = []
        self._buds = []

        @self.cmd('help', 'Show this message')
        def _help_handler(msg):
            lines = ["/help - Show this message"]
            for name, desc in self.commands:
                if name != "help":  # avoid repeating /help
                    lines.append(f"/{name} - {desc}")
            self.bot.reply_to(msg, "\n".join(lines))


    def cmd(self, name: str, desc: str, **handler_kwargs):
        def decorator(func):
            self.commands.append((name, desc))
            self.bot.message_handler(commands=[name], **handler_kwargs)(func)
            return func
        return decorator

    def inject_bud(self, bud_module):
        if hasattr(bud_module, 'register'):
            bud_module.register(self)
            self._buds.append(bud_module.__name__)
        else:
            raise ValueError(f"{bud_module} does not define a 'register(bot)' function.")

    def run(self):
        logging.info(f"Running with buds: {self._buds}")
        self.bot.infinity_polling(skip_pending=True)


if __name__ == "__main__":
    load_dotenv()
    TOKEN_1 = os.getenv("TG_TOKEN_1")
    if not TOKEN_1:
        raise RuntimeError("Please set TG_TOKEN_1 in your .env")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    bot1 = BotApp(TOKEN_1)
    bot1.inject_bud(basic_bud)
    bot1.inject_bud(chat_bud)
    bot1.inject_bud(pm_bud)
    bot1.run()


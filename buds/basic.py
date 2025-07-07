# buds/basic.py

def register(bot):
    @bot.cmd('chatid', 'Show chat ID')
    def handle_chatid(msg):
        bot.bot.reply_to(msg, f"Chat ID is `{msg.chat.id}`", parse_mode='Markdown')

    @bot.cmd('hello', 'Respond hello')
    def handle_hello(msg):
        bot.bot.reply_to(msg, "Hello buddy!")


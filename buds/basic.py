# buds/basic.py

def register(botApp):
    @botApp.cmd('chatid', 'Show chat ID')
    def handle_chatid(msg):
        botApp.bot.reply_to(msg, f"Chat ID is `{msg.chat.id}`", parse_mode='Markdown')

    @botApp.cmd('hello', 'Respond hello')
    def handle_hello(msg):
        botApp.bot.reply_to(msg, "Hello buddy!")


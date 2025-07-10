def register(botApp):
    import os
    from github import Github
    import logging

    # Initialize GitHub client
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    REPO_NAME = os.getenv("GITHUB_REPO")  # e.g., "youruser/yourrepo"
    gh = Github(GITHUB_TOKEN)
    repo = gh.get_repo(REPO_NAME)

    @botApp.cmd("ticket_add", "Create a GitHub issue from a formatted block")
    def ticket_add(msg):
        import re

        chat_id = msg.chat.id
        content = msg.text.partition(" ")[2].strip()

        if not content:
            return botApp.bot.reply_to(msg, "Usage:\n/ticket_add <Markdown-formatted issue>")

        # Extract `# Title` using regex
        title_match = re.search(r'^# (.+)', content, re.MULTILINE)
        if not title_match:
            return botApp.bot.reply_to(msg, "❌ Please include a `# Title` line as the first heading.")

        title = title_match.group(1).strip()

        # Compose full body (optionally prepend chat ID)
        body = f"Issue submitted via Telegram... \n\n{content}"

        try:
            issue = repo.create_issue(title=title, body=body)
            botApp.bot.send_message(
                chat_id,
                f"✅ Ticket created: [{issue.title}]({issue.html_url})",
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.error(f"GitHub issue creation failed: {e}")
            botApp.bot.send_message(chat_id, f"❌ Failed to create issue:\n{e}")



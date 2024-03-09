import logging
import os

from telegram import Update, Chat, MessageEntity
from telegram.constants import ChatAction
from telegram.ext import filters, ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler

from chat_buddy.buddy import ChatBuddy

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


class ChatMessageHandler:
    def __init__(self, api_url: str, api_token: str):
        self.api_url = api_url
        self.api_token = api_token

        self.buddy = ChatBuddy(api_url, api_token)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Hi!")

    async def reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['last_messages'] = []
        context.user_data['last_answers'] = []

        await context.bot.send_message(chat_id=update.effective_chat.id, text="Context reset")

    async def message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message is None:  # skipping edited messages
            return

        bot = context.bot
        chat_id = update.effective_chat.id
        chat_type = update.effective_chat.type
        user = update.effective_user
        text = update.message.text

        ignore = True
        if chat_type == Chat.PRIVATE:
            logging.info(f"User {user.username} sent message {text} in private chat (id: {chat_id})")
            ignore = False

        elif chat_type == Chat.GROUP or chat_type == Chat.SUPERGROUP:
            # check if bot was mentioned
            entities = update.message.parse_entities([MessageEntity.MENTION])
            for entity in entities.values():
                if entity == "@" + bot.username:
                    # remove the mention handle
                    text = text.replace(f"@{bot.username}", "")

                    logging.info(f"User {user.username} mentioned the bot in chat {chat_id}")
                    ignore = False

            # check if bot was replied to
            if update.message.reply_to_message:
                if update.message.reply_to_message.from_user.id == bot.id:
                    logging.info(f"User {user.username} replied to the bot in chat {chat_id}")
                    ignore = False

        if ignore:
            return

        # typing
        await bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

        # count messages
        msg_cnt = context.user_data.get('counter', 0) + 1
        context.user_data['counter'] = msg_cnt
        # logging.info(f"Counter: {msg_cnt} messages")

        # retrieve last messages
        last_messages = context.user_data.get('last_messages', [])
        last_bot_answers = context.user_data.get('last_answers', [])

        if len(last_messages) != len(last_bot_answers):
            last_messages = []
            last_bot_answers = []
            logging.warning("Last messages and last bot answers are not in sync. Resetting.")

        logging.info(f"Loaded {len(last_messages)} last messages and bot answers")

        # get response from chat buddy
        response = self.buddy.ask(text, last_messages, last_bot_answers)

        last_messages.append(text)
        last_bot_answers.append(response)

        if len(last_messages) > 5:
            last_messages.pop(0)
            last_bot_answers.pop(0)

        context.user_data['last_messages'] = last_messages
        context.user_data['last_answers'] = last_bot_answers

        # respond to the message
        await bot.send_message(
            chat_id=update.effective_chat.id,
            reply_to_message_id=update.message.message_id,
            text=response
        )


def main(tg_token: str, api_url, api_token):
    builder = ApplicationBuilder()
    builder.token(tg_token)
    # builder.

    application = builder.build()

    handler_service = ChatMessageHandler(api_url, api_token)

    start_handler = CommandHandler('start', handler_service.start)
    reset_handler = CommandHandler('reset', handler_service.reset)

    message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handler_service.message)

    application.add_handler(start_handler)
    application.add_handler(message_handler)
    application.add_handler(reset_handler)

    application.run_polling()


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    # read secrets from env
    tg_token = os.environ.get('TG_TOKEN')
    api_url = os.environ.get('API_URL')
    api_token = os.environ.get('API_TOKEN', 'sk-xxx')

    main(tg_token, api_url, api_token)

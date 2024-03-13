import logging
import os
import time

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
        self.last_typing_time = {}

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
        text = update.message.text

        # check if we can skip the message
        if not self.is_action_required(update, context):
            return

        # send typing action
        await self.indicate_typing(bot, chat_id)

        # retrieve last messages
        last_messages, last_bot_answers = self.get_history(context)

        # get response from chat buddy
        response_list = []
        chunks = self.buddy.ask(text, last_messages, last_bot_answers)
        for chunk in chunks:
            response_list.append(chunk)
            await self.indicate_typing(bot, chat_id)

        response = "".join(response_list)

        # store the last messages and bot answers
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


    async def indicate_typing(self, bot, chat_id, force=False):
        if force or time.time() - self.last_typing_time.get(chat_id, 0) > 3:
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            self.last_typing_time[chat_id] = time.time()

    @staticmethod
    def get_history(context):
        # retrieve last messages
        last_messages = context.user_data.get('last_messages', [])
        last_bot_answers = context.user_data.get('last_answers', [])
        if len(last_messages) != len(last_bot_answers):
            last_messages = []
            last_bot_answers = []
            logging.warning("Last messages and last bot answers are not in sync. Resetting.")
        logging.info(f"Loaded {len(last_messages)} last messages and bot answers")
        return last_messages,  last_bot_answers

    @staticmethod
    def is_action_required(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

        return not ignore


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

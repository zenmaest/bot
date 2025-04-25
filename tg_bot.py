import telegram
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CallbackContext

# Настройки Telegram
TELEGRAM_TOKEN = ''
ADMIN_GROUP_ID = ''

# Словарь для хранения контекста диалогов
user_topics = {}  # user_id -> topic_id

async def create_topic(bot: telegram.Bot, username: str):
    """
    Создаёт новый топик в группе администраторов.
    """
    topic_name = f"Диалог с {username}"
    response = await bot.create_forum_topic(chat_id=ADMIN_GROUP_ID, name=topic_name)
    return response.message_thread_id

async def forward_to_admin(update: Update, context: CallbackContext):
    """
    Пересылает сообщение от пользователя в соответствующий топик.
    """
    message = update.message

    # Проверяем, что сообщение пришло из личного чата, а не из группы администраторов
    if message.chat.type != "private":
        print("Сообщение не из личного чата, игнорируем.")
        return

    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    text = message.text

    # Если топик ещё не создан, создаём его
    if user_id not in user_topics:
        topic_id = await create_topic(context.bot, username)
        user_topics[user_id] = topic_id
    else:
        topic_id = user_topics[user_id]

    # Отправляем сообщение в топик
    admin_message = f"[{username}]: {text}"
    await context.bot.send_message(
        chat_id=ADMIN_GROUP_ID,
        text=admin_message,
        message_thread_id=topic_id
    )

async def handle_admin_reply(update: Update, context: CallbackContext):
    """
    Обрабатывает ответы администраторов и пересылает их обратно пользователю.
    """
    message = update.message
    reply_to_message = message.reply_to_message

    # Игнорируем сообщения, если они не являются ответами
    if not reply_to_message:
        return

    # Парсим информацию о пользователе из текста сообщения
    original_message_text = reply_to_message.text
    if not original_message_text.startswith("[") or "]" not in original_message_text:
        return  # Некорректный формат сообщения

    username = original_message_text.split("[")[1].split("]")[0]
    user_id = None

    # Находим ID пользователя по имени
    for uid, topic_id in user_topics.items():
        try:
            member = await context.bot.get_chat_member(chat_id=ADMIN_GROUP_ID, user_id=uid)
            if member.user.username == username:
                user_id = uid
                break
        except Exception as e:
            print(f"Ошибка при получении участника: {e}")

    if not user_id:
        print(f"Пользователь с именем {username} не найден.")
        return

    # Пересылаем ответ администратора пользователю
    reply_text = message.text
    await context.bot.send_message(chat_id=user_id, text=f"Ответ администратора: {reply_text}")

def main():
    # Создаем и настраиваем бота
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Обработчик личных сообщений от пользователей
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, forward_to_admin))

    # Обработчик ответов администраторов в топиках
    application.add_handler(MessageHandler(filters.Chat(chat_id=ADMIN_GROUP_ID) & filters.REPLY & filters.TEXT, handle_admin_reply))

    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()

import telebot
from telebot import types
import os
import logging
import traceback
from dotenv import load_dotenv
import random

# --- Настройка логирования ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Загружаем переменные окружения из файла .env
load_dotenv()

# Получаем токен бота из переменной окружения
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    logging.critical("Ошибка: Токен бота не найден. Установите переменную окружения BOT_TOKEN.")
    exit()

bot = telebot.TeleBot(BOT_TOKEN)

# --- Админские настройки ---
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(',')))

# --- Курс голды ---
GOLD_RATE = 0.65

# --- Данные (имитация базы данных) ---
user_data = {}

# --- Способы пополнения (динамические, из базы данных) ---
payment_methods = {
    "sberbank": {"name": "Сбербанк", "details": "Переведите {amount} рублей по номеру карты XXXXXXXXXX, после перевода сделайте скрин и пришлите в этот диалог.", "min_amount": GOLD_RATE * 100},
    "tinkoff": {"name": "Тинькофф", "details": "Переведите {amount} рублей по номеру карты YYYYYYYYYY, после перевода сделайте скрин и пришлите в этот диалог.", "min_amount": GOLD_RATE * 100}
}

# --- Очередь заявок на пополнение (заглушка, нужно заменить на реальную БД) ---
pending_deposits = []  # Список словарей: [{'id': 1, 'user_id': 123, 'amount': 100, 'photo': 'file_id', 'payment_method': 'qiwi'}, ...]
deposit_id_counter = 1

# --- Состояние пользователя (для отслеживания процесса пополнения) ---
user_states = {}  # {user_id: {'state': 'waiting_amount', 'payment_method': 'sberbank'}, ...}

# --- Очередь заявок на вывод (заглушка, нужно заменить на реальную БД) ---
pending_withdrawals = []  # Список словарей: [{'id': 1, 'user_id': 123, 'amount': 100, 'photo': 'file_id', 'amount_with_fee':130}, ...]
withdrawal_id_counter = 1

# --- Функции для работы с депозитами ---
def create_deposit(user_id, amount, photo, payment_method):
    """Создает новую заявку на пополнение и возвращает ее ID."""
    try:
        global deposit_id_counter
        deposit = {
            'id': deposit_id_counter,
            'user_id': user_id,
            'amount': amount,
            'photo': photo,
            'payment_method': payment_method
        }
        pending_deposits.append(deposit)
        deposit_id_counter += 1
        logging.info(f"Создана заявка на депозит #{deposit_id_counter - 1} для пользователя {user_id}")
        return deposit['id']
    except Exception as e:
        logging.error(f"Ошибка при создании депозита для пользователя {user_id}: {e}")
        return None

def get_deposit(deposit_id):
    """Получает заявку на пополнение по ID."""
    try:
        for deposit in pending_deposits:
            if deposit['id'] == deposit_id:
                return deposit
        logging.warning(f"Депозит с ID {deposit_id} не найден")
        return None
    except Exception as e:
        logging.error(f"Ошибка при получении депозита с ID {deposit_id}: {e}")
        return None

def remove_deposit(deposit_id):
    """Удаляет заявку на пополнение по ID."""
    try:
        global pending_deposits
        pending_deposits = [deposit for deposit in pending_deposits if deposit['id'] != deposit_id]
        logging.info(f"Депозит с ID {deposit_id} удален")
    except Exception as e:
        logging.error(f"Ошибка при удалении депозита с ID {deposit_id}: {e}")

def has_pending_deposit(user_id):
    """Проверяет, есть ли у пользователя неподтвержденная заявка."""
    try:
        for deposit in pending_deposits:
            if deposit['user_id'] == user_id:
                logging.info(f"У пользователя {user_id} есть ожидающая заявка на депозит")
                return True
        logging.info(f"У пользователя {user_id} нет ожидающих заявок на депозит")
        return False
    except Exception as e:
        logging.error(f"Ошибка при проверке ожидающих депозитов для пользователя {user_id}: {e}")
        return False

# --- Функции для работы с выводами ---
def create_withdrawal(user_id, amount, photo, amount_with_fee):
    """Создает новую заявку на вывод и возвращает ее ID."""
    try:
        global withdrawal_id_counter
        withdrawal = {
            'id': withdrawal_id_counter,
            'user_id': user_id,
            'amount': amount,
            'photo': photo,
            'amount_with_fee': amount_with_fee
        }
        pending_withdrawals.append(withdrawal)
        withdrawal_id_counter += 1
        logging.info(f"Создана заявка на вывод #{withdrawal_id_counter - 1} для пользователя {user_id}")
        return withdrawal['id']
    except Exception as e:
        logging.error(f"Ошибка при создании вывода для пользователя {user_id}: {e}")
        return None

def get_withdrawal(withdrawal_id):
    """Получает заявку на вывод по ID."""
    try:
        for withdrawal in pending_withdrawals:
            if withdrawal['id'] == withdrawal_id:
                return withdrawal
        logging.warning(f"Вывод с ID {withdrawal_id} не найден")
        return None
    except Exception as e:
        logging.error(f"Ошибка при получении вывода с ID {withdrawal_id}: {e}")
        return None

def remove_withdrawal(withdrawal_id):
    """Удаляет заявку на вывод по ID."""
    try:
        global pending_withdrawals
        pending_withdrawals = [withdrawal for withdrawal in pending_withdrawals if withdrawal['id'] != withdrawal_id]
        logging.info(f"Вывод с ID {withdrawal_id} удален")
    except Exception as e:
        logging.error(f"Ошибка при удалении вывода с ID {withdrawal_id}: {e}")

# --- Функции-обработчики ---

def get_user_data(user_id):
    """Получает данные пользователя.  Если пользователь не существует, создает новую запись."""
    try:
        if user_data.get(user_id) is None:
            user_data[user_id] = {
                'balance': 0,
                'name': 'Не указано',
                'city': 'Не указано',
                'deposit_count': 0,
                'withdraw_count': 0,
            }
            logging.info(f"Создан новый пользователь с ID: {user_id}")
        return user_data[user_id]
    except Exception as e:
        logging.error(f"Ошибка при получении данных пользователя {user_id}: {e}")
        return None

def save_user_data(user_id, data):
    """Сохраняет данные пользователя."""
    try:
        user_data[user_id] = data
        logging.debug(f"Данные пользователя {user_id} обновлены: {data}")
    except Exception as e:
        logging.error(f"Ошибка при сохранении данных пользователя {user_id}: {e}")

def is_admin(user_id):
    """Проверяет, является ли пользователь администратором."""
    return user_id in ADMIN_IDS

@bot.message_handler(commands=['start'])
def start(message):
    """Обработчик команды /start."""
    try:
        user_id = message.from_user.id
        user = message.from_user
        user_info = get_user_data(user_id)

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        button_profile = types.KeyboardButton('Профиль')
        button_withdraw = types.KeyboardButton('Вывести')
        button_deposit = types.KeyboardButton('Пополнить')
        button_calculator = types.KeyboardButton('Калькулятор')
        button_exchange_rate = types.KeyboardButton('Курс')
        button_reviews = types.KeyboardButton('Отзывы')
        button_support = types.KeyboardButton('Тех. поддержка')

        keyboard.add(button_profile, button_withdraw)
        keyboard.add(button_deposit, button_calculator)
        keyboard.add(button_exchange_rate, button_reviews)
        keyboard.add(button_support)

        if is_admin(user_id):
            button_admin = types.KeyboardButton('Админ панель')
            keyboard.add(button_admin)

        bot.send_message(user_id, f"Привет, {user.first_name}!  Вот главное меню.", reply_markup=keyboard)
        logging.info(f"Пользователь {user_id} запустил команду /start")

    except Exception as e:
        logging.error(f"Ошибка в start: {e}\n{traceback.format_exc()}")

@bot.message_handler(func=lambda message: message.text == 'Админ панель')
def admin_panel(message):
    """Обработчик кнопки 'Админ панель'."""
    try:
        user_id = message.from_user.id
        if is_admin(user_id):
            # Создаем инлайн-клавиатуру для админ-панели
            inline_keyboard = types.InlineKeyboardMarkup(row_width=2)  # row_width для размещения кнопок в 2 столбца

            button_deposits = types.InlineKeyboardButton(text="Пополнения", callback_data="admin_deposits")
            button_withdrawals = types.InlineKeyboardButton(text="Выводы", callback_data="admin_withdrawals")
            button_broadcast = types.InlineKeyboardButton(text="Рассылка", callback_data="admin_broadcast")
            button_promocodes = types.InlineKeyboardButton(text="Промокоды", callback_data="admin_promocodes")
            button_links = types.InlineKeyboardButton(text="Ссылки", callback_data="admin_links")
            button_ref_system = types.InlineKeyboardButton(text="Реф. система", callback_data="admin_ref_system")
            button_questions = types.InlineKeyboardButton(text="Вопросы", callback_data="admin_questions")
            button_settings = types.InlineKeyboardButton(text="Настройки", callback_data="admin_settings")

            inline_keyboard.add(button_deposits, button_withdrawals,
                                button_broadcast, button_promocodes,
                                button_links, button_ref_system,
                                button_questions, button_settings)

            bot.send_message(user_id, "Добро пожаловать в админ-панель!", reply_markup=inline_keyboard)
            logging.info(f"Администратор {user_id} открыл админ-панель")
        else:
            bot.send_message(user_id, "У вас нет прав для доступа к этой функции.")
            logging.warning(f"Пользователь {user_id} попытался получить доступ к админ-панели без прав")

    except Exception as e:
        logging.error(f"Ошибка в admin_panel: {e}\n{traceback.format_exc()}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
def admin_callback_handler(call):
    """Обработчик callback-запросов из админ-панели."""
    try:
        user_id = call.from_user.id
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "У вас нет прав для доступа к этой функции.")
            logging.warning(f"Пользователь {user_id} попытался выполнить админ-действие без прав: {call.data}")
            return

        if call.data == "admin_deposits":
            # Показать список заявок на пополнение
            if not pending_deposits:
                bot.send_message(user_id, "Нет ожидающих заявок на пополнение.")
                logging.info(f"Администратор {user_id} запросил список пополнений. Список пуст.")
            else:
                # Создаем инлайн-клавиатуру с суммами пополнений (в качестве текста кнопок)
                inline_keyboard = types.InlineKeyboardMarkup(row_width=2)
                for deposit in pending_deposits:
                    button_deposit = types.InlineKeyboardButton(
                        text=f"{deposit['amount']} $",
                        callback_data=f"admin_deposit_{deposit['id']}"  # Добавляем ID заявки
                    )
                    inline_keyboard.add(button_deposit)
                bot.send_message(user_id, "Выберите заявку на пополнение:", reply_markup=inline_keyboard)
                logging.info(f"Администратор {user_id} запросил список пополнений. Отправлено {len(pending_deposits)} заявок.")

        elif call.data.startswith("admin_deposit_"):
            deposit_id = int(call.data[14:])  # Получаем ID заявки из callback_data
            deposit = get_deposit(deposit_id)
            if deposit:
                user = bot.get_chat(deposit['user_id']) #Получаем информацию о пользователе
                # Показываем информацию о заявке
                message_text = (
                    f"ID: {deposit['id']}\n"
                    f"Имя: {user.first_name} {user.last_name or ''}\n"  # Используем данные из объекта User
                    f"ID Пользователя: {deposit['user_id']}\n"
                    f"Сумма: {deposit['amount']} $\n"
                    f"Способ пополнения: {deposit['payment_method']}" #TODO: реализовать сохранение этого в заявке
                )
                inline_keyboard = types.InlineKeyboardMarkup()
                button_approve = types.InlineKeyboardButton(text="Одобрить", callback_data=f"approve_deposit_{deposit_id}")
                button_decline = types.InlineKeyboardButton(text="Отклонить", callback_data=f"decline_deposit_{deposit_id}")
                inline_keyboard.add(button_approve, button_decline)

                #Отправляем фотографию (если она есть) и текст заявки
                if deposit['photo']:
                    bot.send_photo(user_id, deposit['photo'], caption=message_text, reply_markup=inline_keyboard)
                else:
                    bot.send_message(user_id, message_text, reply_markup=inline_keyboard)

                logging.info(f"Администратору {user_id} показана информация о заявке {deposit_id}")
            else:
                bot.send_message(user_id, "Заявка не найдена.")
                logging.warning(f"Администратор {user_id} запросил несуществующую заявку {deposit_id}")

        elif call.data == "admin_withdrawals":
            # Показать список заявок на вывод
            if not pending_withdrawals:
                bot.send_message(user_id, "Нет ожидающих заявок на вывод.")
                logging.info(f"Администратор {user_id} запросил список выводов. Список пуст.")
            else:
                # Создаем инлайн-клавиатуру с суммами вывода (в качестве текста кнопок)
                inline_keyboard = types.InlineKeyboardMarkup(row_width=2)
                for withdrawal in pending_withdrawals:
                    button_withdrawal = types.InlineKeyboardButton(
                        text=f"{withdrawal['amount']} голды",
                        callback_data=f"admin_withdrawal_{withdrawal['id']}"  # Добавляем ID заявки
                    )
                    inline_keyboard.add(button_withdrawal)
                bot.send_message(user_id, "Выберите заявку на вывод:", reply_markup=inline_keyboard)
                logging.info(f"Администратор {user_id} запросил список выводов. Отправлено {len(pending_withdrawals)} заявок.")

        elif call.data.startswith("admin_withdrawal_"):
            withdrawal_id = int(call.data[17:])  # Получаем ID заявки из callback_data
            withdrawal = get_withdrawal(withdrawal_id)
            if withdrawal:
                user = bot.get_chat(withdrawal['user_id']) #Получаем информацию о пользователе
                # Показываем информацию о заявке
                message_text = (
                    f"ID: {withdrawal['id']}\n"
                    f"Имя: {user.first_name} {user.last_name or ''}\n"  # Используем данные из объекта User
                    f"ID Пользователя: {withdrawal['user_id']}\n"
                    f"Сумма: {withdrawal['amount']} голды\n"
                    f"Сумма с комиссией: {withdrawal['amount_with_fee']} голды"
                )
                inline_keyboard = types.InlineKeyboardMarkup()
                button_approve = types.InlineKeyboardButton(text="Одобрить", callback_data=f"approve_withdrawal_{withdrawal_id}")
                button_decline = types.InlineKeyboardButton(text="Отклонить", callback_data=f"decline_withdrawal_{withdrawal_id}")
                inline_keyboard.add(button_approve, button_decline)

                #Отправляем фотографию и текст заявки
                if withdrawal['photo']:
                    bot.send_photo(user_id, withdrawal['photo'], caption=message_text, reply_markup=inline_keyboard)
                else:
                    bot.send_message(user_id, message_text, reply_markup=inline_keyboard)

                logging.info(f"Администратору {user_id} показана информация о заявке на вывод {withdrawal_id}")
            else:
                bot.send_message(user_id, "Заявка не найдена.")
                logging.warning(f"Администратор {user_id} запросил несуществующую заявку на вывод {withdrawal_id}")

        elif call.data == "admin_broadcast":
            # TODO: Реализовать логику рассылки сообщений
            bot.send_message(user_id, "Здесь будет функционал рассылки сообщений.")
            logging.info(f"Администратор {user_id} запросил функционал рассылки")
        elif call.data == "admin_promocodes":
            # TODO: Реализовать логику управления промокодами
            bot.send_message(user_id, "Здесь будет функционал управления промокодами.")
            logging.info(f"Администратор {user_id} запросил функционал управления промокодами")
        elif call.data == "admin_links":
            # TODO: Реализовать логику управления ссылками
            bot.send_message(user_id, "Здесь будет функционал управления ссылками.")
            logging.info(f"Администратор {user_id} запросил функционал управления ссылками")
        elif call.data == "admin_ref_system":
            # TODO: Реализовать логику управления реферальной системой
            bot.send_message(user_id, "Здесь будет функционал управления реферальной системой.")
            logging.info(f"Администратор {user_id} запросил функционал управления реферальной системой")
        elif call.data == "admin_questions":
            # TODO: Реализовать логику просмотра вопросов
            bot.send_message(user_id, "Здесь будет список вопросов.")
            logging.info(f"Администратор {user_id} запросил список вопросов")
        elif call.data == "admin_settings":
            # TODO: Реализовать логику изменения настроек
            bot.send_message(user_id, "Здесь будет функционал изменения настроек.")
            logging.info(f"Администратор {user_id} запросил функционал изменения настроек")
        else:
            bot.answer_callback_query(call.id, "Неизвестная команда")
            logging.warning(f"Администратор {user_id} выполнил неизвестную админ-команду: {call.data}")

        bot.answer_callback_query(call.id)

    except Exception as e:
        logging.error(f"Ошибка в admin_callback_handler: {e}\n{traceback.format_exc()}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_deposit_") or call.data.startswith("decline_deposit_"))
def handle_deposit_approval(call):
     """Обработчик одобрения/отклонения заявки на депозит."""
     try:
         user_id = call.from_user.id
         if not is_admin(user_id):
            bot.answer_callback_query(call.id, "У вас нет прав для доступа к этой функции.")
            logging.warning(f"Пользователь {user_id} попытался выполнить админ-действие без прав: {call.data}")
            return

         deposit_id = int(call.data.split("_")[-1])
         deposit = get_deposit(deposit_id)

         if not deposit:
             bot.send_message(user_id, "Заявка не найдена.")
             logging.warning(f"Администратор {user_id} попытался обработать несуществующую заявку {deposit_id}")
             return

         if call.data.startswith("approve_deposit_"):
             # Одобряем пополнение

             # Рассчитываем количество голды, которое нужно начислить пользователю
             gold_amount = int(deposit['amount'] / GOLD_RATE)

             user_info = get_user_data(deposit['user_id'])
             user_info['balance'] += gold_amount # Начисляем голду, а не рубли
             user_info['deposit_count'] += 1
             save_user_data(deposit['user_id'], user_info)
             remove_deposit(deposit_id)

             bot.send_message(deposit['user_id'], f"Ваша заявка на пополнение одобрена! На ваш баланс зачислено {gold_amount} голды.")
             bot.send_message(user_id, f"Заявка {deposit_id} одобрена. Пользователю {deposit['user_id']} начислено {gold_amount} голды.")
             logging.info(f"Администратор {user_id} одобрил заявку {deposit_id} и начислил {gold_amount} голды пользователю {deposit['user_id']}")


         elif call.data.startswith("decline_deposit_"):
             # Запрашиваем причину отказа
             msg = bot.send_message(user_id, "Введите причину отказа:")
             bot.register_next_step_handler(msg, process_decline_reason, deposit_id)  # Передаем deposit_id

         bot.answer_callback_query(call.id)

     except Exception as e:
         logging.error(f"Ошибка в handle_deposit_approval: {e}\n{traceback.format_exc()}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_withdrawal_") or call.data.startswith("decline_withdrawal_"))
def handle_withdrawal_approval(call):
     """Обработчик одобрения/отклонения заявки на вывод."""
     try:
         user_id = call.from_user.id
         if not is_admin(user_id):
            bot.answer_callback_query(call.id, "У вас нет прав для доступа к этой функции.")
            logging.warning(f"Пользователь {user_id} попытался выполнить админ-действие без прав: {call.data}")
            return

         withdrawal_id = int(call.data.split("_")[-1])
         withdrawal = get_withdrawal(withdrawal_id)

         if not withdrawal:
             bot.send_message(user_id, "Заявка не найдена.")
             logging.warning(f"Администратор {user_id} попытался обработать несуществующую заявку {withdrawal_id}")
             return

         if call.data.startswith("approve_withdrawal_"):
             # Одобряем вывод
             remove_withdrawal(withdrawal_id)

             bot.send_message(withdrawal['user_id'], "Ваша заявка на вывод одобрена!")
             bot.send_message(user_id, f"Заявка на вывод {withdrawal_id} одобрена. Пользователю {withdrawal['user_id']} будет выплачено {withdrawal['amount_with_fee']} голды")
             logging.info(f"Администратор {user_id} одобрил заявку на вывод {withdrawal_id} для пользователя {withdrawal['user_id']}")


         elif call.data.startswith("decline_withdrawal_"):
             # Запрашиваем причину отказа
             msg = bot.send_message(user_id, "Введите причину отказа:")
             bot.register_next_step_handler(msg, process_decline_withdrawal_reason, withdrawal_id)  # Передаем withdrawal_id

         bot.answer_callback_query(call.id)

     except Exception as e:
         logging.error(f"Ошибка в handle_withdrawal_approval: {e}\n{traceback.format_exc()}")

def process_decline_withdrawal_reason(message, withdrawal_id):
    """Обрабатывает причину отклонения заявки на вывод и возвращает средства пользователю."""
    try:
        user_id = message.from_user.id
        if not is_admin(user_id):
            bot.send_message(user_id, "У вас нет прав для доступа к этой функции.")
            return

        reason = message.text
        withdrawal = get_withdrawal(withdrawal_id)
        if not withdrawal:
            bot.send_message(user_id, "Заявка не найдена.")
            return

        user_info = get_user_data(withdrawal['user_id'])
        user_info['balance'] += withdrawal['amount'] #Возвращаем сумму на баланс
        save_user_data(withdrawal['user_id'], user_info)
        remove_withdrawal(withdrawal_id)

        bot.send_message(withdrawal['user_id'], f"Ваша заявка на вывод была отклонена, причина: {reason}. Сумма {withdrawal['amount']} возвращена на баланс")
        bot.send_message(user_id, f"Заявка на вывод {withdrawal_id} отклонена. Пользователю {withdrawal['user_id']} возвращено {withdrawal['amount']} голды. Причина: {reason}")
        logging.info(f"Администратор {user_id} отклонил заявку на вывод {withdrawal_id} для пользователя {withdrawal['user_id']}. Причина: {reason}")

    except Exception as e:
        logging.error(f"Ошибка в process_decline_withdrawal_reason: {e}\n{traceback.format_exc()}")

@bot.message_handler(func=lambda message: message.text == 'Пополнить')
def deposit_menu(message):
    """Обработчик кнопки 'Пополнить'."""
    try:
        user_id = message.from_user.id

        #Проверяем есть ли у пользователя не проверенная заявка
        if has_pending_deposit(user_id):
             bot.send_message(user_id, "У вас уже есть не проверенная заявка на пополнение баланса. Ожидайте её проверки.")
             return

        # Создаем инлайн-клавиатуру со способами пополнения
        inline_keyboard = types.InlineKeyboardMarkup(row_width=2)
        for method_code, method_data in payment_methods.items():
            button = types.InlineKeyboardButton(text=method_data["name"], callback_data=f"deposit_method_{method_code}")
            inline_keyboard.add(button)

        bot.send_message(user_id, "Выберите способ пополнения:", reply_markup=inline_keyboard)
        logging.info(f"Пользователь {user_id} нажал кнопку 'Пополнить'")

    except Exception as e:
        logging.error(f"Ошибка в deposit: {e}\n{traceback.format_exc()}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("deposit_method_"))
def process_payment_method(call):
    """Обработчик выбора способа пополнения."""
    try:
        user_id = call.from_user.id
        method_code = call.data[15:]  # Извлекаем код способа пополнения
        if method_code not in payment_methods:
            bot.send_message(user_id, "Неизвестный способ пополнения.")
            logging.warning(f"Пользователь {user_id} выбрал неизвестный способ пополнения: {method_code}")
            return

        # Сохраняем состояние пользователя (ожидание суммы)
        user_states[user_id] = {"state": "waiting_amount", "payment_method": method_code}
        msg = bot.send_message(user_id, f"Введите сумму пополнения в рублях (не меньше {payment_methods[method_code]['min_amount']:.2f}):")
        bot.register_next_step_handler(msg, process_deposit_amount, method_code)  # Передаем method_code

    except Exception as e:
        logging.error(f"Ошибка в process_payment_method: {e}\n{traceback.format_exc()}")

def process_deposit_amount(message, method_code):
    """Обработчик ввода суммы пополнения."""
    try:
        user_id = message.from_user.id
        try:
            amount = float(message.text)
            if amount < payment_methods[method_code]["min_amount"]:
                bot.send_message(user_id, f"Сумма пополнения должна быть не меньше {payment_methods[method_code]['min_amount']:.2f} рублей.")
                return

            # Сохраняем сумму и переходим к ожиданию фото
            user_states[user_id]["state"] = "waiting_photo"
            user_states[user_id]["amount"] = amount

            # Рассчитываем количество голды
            gold_amount = int(amount / GOLD_RATE) # GOLD_RATE - ваш курс голды

            #Получаем сообщение для пользователя из настроек по способу пополнения
            deposit_details_message = payment_methods[method_code]["details"].format(amount=amount)

            #Добавляем информацию о количестве голды к сообщению
            message_to_user = f"{deposit_details_message}\n\nЗа {amount} рублей вы получите {gold_amount} голды.\nПришлите скриншот перевода в этот диалог."

            bot.send_message(user_id, message_to_user)

        except ValueError:
            bot.send_message(user_id, "Неверный формат суммы. Введите число.")
            return

    except Exception as e:
        logging.error(f"Ошибка в process_deposit_amount: {e}\n{traceback.format_exc()}")

@bot.message_handler(content_types=['photo'], func=lambda message: get_user_state(message.from_user.id) == "waiting_photo")
def process_deposit_photo(message):
    """Обработчик отправки скриншота пополнения."""
    try:
        user_id = message.from_user.id
        #Получаем информацию о пользователе из user_states
        if user_id not in user_states or user_states[user_id]["state"] != "waiting_photo":
            bot.send_message(user_id, "Произошла ошибка. Попробуйте начать процесс пополнения заново.")
            return

        photo_file_id = message.photo[-1].file_id #Сохраняем file_id фотографии
        amount = user_states[user_id]["amount"] #Достаем сумму
        payment_method = user_states[user_id]["payment_method"] #Достаем способ пополнения

        #Создаем заявку на пополнение
        deposit_id = create_deposit(user_id, amount, photo_file_id,         payment_method)
        bot.send_message(user_id, f"Заявка на пополнение #{deposit_id} на сумму {amount} рублей создана. Ожидайте подтверждения администратора. Проверка обычно занимает до 15 минут.")
        logging.info(f"Пользователь {user_id} запросил пополнение баланса на сумму {amount} рублей через {payment_method}")

        #Сбрасываем состояние пользователя
        del user_states[user_id]

    except Exception as e:
        logging.error(f"Ошибка в process_deposit_photo: {e}\n{traceback.format_exc()}")

@bot.message_handler(func=lambda message: message.text == 'Вывести')
def withdraw(message):
    """Обработчик кнопки 'Вывести'."""
    try:
        user_id = message.from_user.id
        user_info = get_user_data(user_id)

        # Проверяем, есть ли у пользователя ожидающая заявка на вывод
        if has_pending_withdrawal(user_id):
            bot.send_message(user_id, "У вас уже есть ожидающая заявка на вывод. Пожалуйста, дождитесь её обработки.")
            logging.warning(f"Пользователь {user_id} попытался создать новую заявку на вывод при наличии ожидающей")
            return

        if user_info['balance'] <= 0:
            bot.send_message(user_id, "У вас недостаточно средств для вывода.")
            logging.warning(f"Пользователь {user_id} попытался вывести средства при нулевом балансе")
            return

        # Устанавливаем состояние пользователя в "ожидание суммы вывода"
        user_states[user_id] = {"state": "waiting_withdrawal_amount"}
        msg = bot.send_message(user_id, "Напишите сумму вывода в голде:")
        bot.register_next_step_handler(msg, process_withdrawal_amount)

        logging.info(f"Пользователь {user_id} начал процесс вывода средств")

    except Exception as e:
        logging.error(f"Ошибка в withdraw: {e}\n{traceback.format_exc()}")


def has_pending_withdrawal(user_id):
    """Проверяет, есть ли у пользователя неподтвержденная заявка на вывод."""
    try:
        for withdrawal in pending_withdrawals:
            if withdrawal['user_id'] == user_id:
                logging.info(f"У пользователя {user_id} есть ожидающая заявка на вывод")
                return True
        logging.info(f"У пользователя {user_id} нет ожидающих заявок на вывод")
        return False
    except Exception as e:
        logging.error(f"Ошибка при проверке ожидающих выводов для пользователя {user_id}: {e}")
        return False

def process_withdrawal_amount(message):
    """Обработчик ввода суммы для вывода."""
    try:
        user_id = message.from_user.id
        #Проверяем, что пользователь находится в нужном состоянии
        if user_id not in user_states or user_states[user_id]["state"] != "waiting_withdrawal_amount":
            bot.send_message(user_id, "Произошла ошибка. Попробуйте начать процесс вывода заново.")
            return

        try:
            amount = float(message.text)
            user_info = get_user_data(user_id)

            if amount <= 0:
                bot.send_message(user_id, "Неверная сумма. Введите положительное число.")
                logging.warning(f"Пользователь {user_id} ввел неверную сумму для вывода: {amount}")
                return

            if amount > user_info['balance']:
                bot.send_message(user_id, "Недостаточно средств на балансе.")
                logging.warning(f"Пользователь {user_id} запросил вывод суммы, превышающей баланс: {amount}")
                return
            #Сумма с комиссией
            fee = amount * 0.25 + random.uniform(0.01, 0.99) #Считаем комиссию
            amount_with_fee = round(amount + fee, 2)

            #Устанавливаем пользователю состояние: ожидание фотографии
            user_states[user_id]["state"] = "waiting_withdrawal_photo"
            user_states[user_id]["amount"] = amount
            user_states[user_id]["amount_with_fee"] = amount_with_fee

            bot.send_message(user_id, f"Выставьте скин: Tec-9 Tie Dye за {amount_with_fee} голды. После того как выставите пришлите сюда фото.")

        except ValueError:
            bot.send_message(user_id, "Неверный формат суммы. Введите число.")
            logging.warning(f"Пользователь {user_id} ввел неверный формат суммы для вывода: {message.text}")

    except Exception as e:
        logging.error(f"Ошибка в process_withdrawal_amount: {e}\n{traceback.format_exc()}")

@bot.message_handler(content_types=['photo'], func=lambda message: get_user_state(message.from_user.id) == "waiting_withdrawal_photo")
def process_withdrawal_photo(message):
    try:
        user_id = message.from_user.id
        #Проверяем что бы у пользователя было нужное состояние
        if user_id not in user_states or user_states[user_id]["state"] != "waiting_withdrawal_photo":  # Отступ исправлен
            bot.send_message(user_id, "Произошла ошибка. Попробуйте начать процесс вывода заново.")
            return

        photo_file_id = message.photo[-1].file_id #Сохраняем file_id фотографии
        amount = user_states[user_id]["amount"] #Достаем сумму
        amount_with_fee = user_states[user_id]["amount_with_fee"] #Достаем сумму с комиссией
        user_info = get_user_data(user_id)

        #Списываем с баланса сумму
        user_info['balance'] -= amount
        user_info['withdraw_count'] += 1
        save_user_data(user_id, user_info)

        #Создаем заявку на вывод
        withdrawal_id = create_withdrawal(user_id, amount, photo_file_id, amount_with_fee)
        bot.send_message(user_id, f"Ожидайте! Вывод происходит в течение 24 часов.")
        logging.info(f"Пользователь {user_id} запросил вывод на сумму {amount}")

        #Сбрасываем состояние
        del user_states[user_id]

    except Exception as e:
        logging.error(f"Ошибка в process_withdrawal_photo: {e}\n{traceback.format_exc()}")

def get_user_state(user_id):
    """Получает состояние пользователя."""
    if user_id in user_states:
        return user_states[user_id]["state"]
    return None

@bot.message_handler(func=lambda message: message.text == 'Профиль')
def profile(message):
    """Обработчик кнопки 'Профиль'."""
    try:
        user_id = message.from_user.id
        user = message.from_user
        user_info = get_user_data(user_id)

        profile_text = (
            f"Ваш профиль:\n"
            f"Имя: {user.first_name} {user.last_name or ''}\n"
            f"ID: {user_id}\n"
            f"Баланс: {user_info['balance']} $\n"
            f"Кол-во пополнений: {user_info['deposit_count']}\n"
            f"Кол-во выводов: {user_info['withdraw_count']}"
        )

        # Создаем инлайн-клавиатуру
        inline_keyboard = types.InlineKeyboardMarkup()
        promo_button = types.InlineKeyboardButton(text="Промокод", callback_data="promo")
        ref_button = types.InlineKeyboardButton(text="Реф. система", callback_data="ref")
        inline_keyboard.add(promo_button, ref_button)

        bot.send_message(user_id, profile_text, reply_markup=inline_keyboard)
        logging.info(f"Пользователь {user_id} запросил профиль")

    except Exception as e:
        logging.error(f"Ошибка в profile: {e}\n{traceback.format_exc()}")

@bot.callback_query_handler(func=lambda call: not call.data.startswith("admin_") and not call.data.startswith("approve_deposit_") and not call.data.startswith("decline_deposit_") and not call.data.startswith("deposit_method_") and not call.data.startswith("approve_withdrawal_") and not call.data.startswith("decline_withdrawal_") and not call.data.startswith("admin_withdrawal_"))
def inline_button_callback(call):
    """Обработчик callback-запросов от inline-кнопок (кроме админских)."""
    try:
        user_id = call.from_user.id
        if call.data == "promo":
            bot.send_message(user_id, "Здесь будет функционал активации промокода.")
            logging.info(f"Пользователь {user_id} нажал на кнопку 'Промокод'")
        elif call.data == "ref":
            referral_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
            bot.send_message(user_id, f"Ваша реферальная ссылка: {referral_link}")
            logging.info(f"Пользователь {user_id} нажал на кнопку 'Реф. система'")
        elif call.data.startswith("calc_"):  # Обрабатываем callback'и калькулятора
            calculation_type = call.data[5:]  # Извлекаем тип расчета (gold_to_rub или rub_to_gold)
            msg = bot.send_message(user_id, "Введите число (не меньше 1):")
            bot.register_next_step_handler(msg, process_calculator_input, calculation_type)
            logging.info(f"Пользователь {user_id} выбрал расчет {calculation_type}")
        else:
            bot.answer_callback_query(call.id, "Неизвестная команда")
            logging.warning(f"Пользователь {user_id} нажал на неизвестную инлайн-кнопку: {call.data}")

        bot.answer_callback_query(call.id)

    except Exception as e:
        logging.error(f"Ошибка в inline_button_callback: {e}\n{traceback.format_exc()}")

def process_calculator_input(message, calculation_type):
    """Обработчик ввода числа для калькулятора."""
    try:
        user_id = message.from_user.id
        try:
            value = float(message.text)
            if value < 1:
                bot.send_message(user_id, "Введите число не меньше 1.")
                return

            if calculation_type == "gold_to_rub":
                result = value * GOLD_RATE
                bot.send_message(user_id, f"{value} голды = {result:.2f} рублей")
                logging.info(f"Пользователь {user_id} расчитал {value} голды в рубли")
            elif calculation_type == "rub_to_gold":
                result = value / GOLD_RATE
                bot.send_message(user_id, f"{value} рублей = {result:.2f} голды")
                logging.info(f"Пользователь {user_id} расчитал {value} рублей в голду")
            else:
                bot.send_message(user_id, "Неизвестный тип расчета.")
                logging.warning(f"Пользователь {user_id} запросил неизвестный тип расчета: {calculation_type}")

        except ValueError:
            bot.send_message(user_id, "Неверный формат числа. Введите число.")
            logging.warning(f"Пользователь {user_id} ввел неверный формат числа для калькулятора: {message.text}")

    except Exception as e:
        logging.error(f"Ошибка в process_calculator_input: {e}\n{traceback.format_exc()}")

@bot.message_handler(func=lambda message: message.text == 'Курс')
def exchange_rate(message):
    """Обработчик кнопки 'Курс'."""
    try:
        user_id = message.from_user.id
        rate = 75.0  # Доллар к рублю (пример)
        bot.send_message(user_id, f"Курс валют:\n1 1  = {rate} RUB (пример)")
        logging.info(f"Пользователь {user_id} запросил курс валют")

    except Exception as e:
        logging.error(f"Ошибка в exchange_rate: {e}\n{traceback.format_exc()}")

@bot.message_handler(func=lambda message: message.text == 'Отзывы')
def reviews(message):
    """Обработчик кнопки 'Отзывы'."""
    try:
        user_id = message.from_user.id
        bot.send_message(user_id, "Пока что здесь нет функционала для отзывов.  Можете оставить свои пожелания разработчику.")
        logging.info(f"Пользователь {user_id} запросил отзывы")

    except Exception as e:
        logging.error(f"Ошибка в reviews: {e}\n{traceback.format_exc()}")

@bot.message_handler(func=lambda message: message.text == 'Тех. поддержка')
def support(message):
    """Обработчик кнопки 'Тех. поддержка'."""
    try:
        user_id = message.from_user.id
        bot.send_message(user_id, "Для связи с техподдержкой напишите на example@mail.com (пример)")
        logging.info(f"Пользователь {user_id} запросил техподдержку")

    except Exception as e:
        logging.error(f"Ошибка в support: {e}\n{traceback.format_exc()}")

#Обработчик для тех кнопок, которые не находятся выше (чтобы не было конфликтов)
@bot.callback_query_handler(func=lambda call: True)
def inline_button_callback_default(call):
    """Дефолтный обработчик callback-запросов."""
    try:
        user_id = call.from_user.id
        if call.data == "promo":
            bot.send_message(user_id, "Здесь будет функционал активации промокода.")
            logging.info(f"Пользователь {user_id} нажал на кнопку 'Промокод'")
        elif call.data == "ref":
            referral_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
            bot.send_message(user_id, f"Ваша реферальная ссылка: {referral_link}")
            logging.info(f"Пользователь {user_id} нажал на кнопку 'Реф. система'")
        else:
            bot.answer_callback_query(call.id, "Неизвестная команда")
            logging.warning(f"Пользователь {user_id} нажал на неизвестную инлайн-кнопку: {call.data}")

        bot.answer_callback_query(call.id)

    except Exception as e:
        logging.error(f"Ошибка в inline_button_callback_default: {e}\n{traceback.format_exc()}")

def process_decline_reason(message, deposit_id):
    """Обработчик причины отклонения депозита."""
    try:
        user_id = message.from_user.id
        if not is_admin(user_id):
            bot.send_message(user_id, "У вас нет прав для доступа к этой функции.")
            return

        reason = message.text
        deposit = get_deposit(deposit_id)

        if not deposit:
            bot.send_message(user_id, "Заявка не найдена.")
            return

        remove_deposit(deposit_id)
        bot.send_message(deposit['user_id'], f"Ваша заявка на пополнение была отклонена. Причина: {reason}")
        bot.send_message(user_id, f"Заявка {deposit_id} отклонена. Указана причина: {reason}")
        logging.info(f"Администратор {user_id} отклонил заявку {deposit_id}. Причина: {reason}")

    except Exception as e:
        logging.error(f"Ошибка в process_decline_reason: {e}\n{traceback.format_exc()}")

# --- Запуск бота ---
if __name__ == '__main__':
    print("Бот запущен...")
    logging.info("Бот запущен")
    try:
        bot.infinity_polling()
    except Exception as e:
        logging.critical(f"Бот остановлен из-за ошибки: {e}\n{traceback.format_exc()}")

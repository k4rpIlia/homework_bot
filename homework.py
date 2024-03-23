
import telegram

import sys

import logging

import os

from dotenv import load_dotenv

import requests
import time



load_dotenv()

PRACTICUM_TOKEN = os.getenv('TOKEN_PRAKTICUM')
TELEGRAM_TOKEN = os.getenv('TOKEN_TELEGRAM')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_PERIOD = 600

ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout)



error_handler = logging.StreamHandler(sys.stdout)
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

'''def error_handler_filter(bot, record):
    if record.levelno == logging.ERROR:
        send_message(bot, record.getMessage())
    return True

error_handler.addFilter(error_handler_filter)'''

logger = logging.getLogger()
logger.addHandler(error_handler)


def check_tokens():
    '''Проверяет доступность переменных окружения,
    которые необходимы для работы программы'''

    required_tokens = ['TOKEN_PRAKTICUM', 'TOKEN_TELEGRAM', 'CHAT_ID']
    for token_name in required_tokens:
        token_value = os.getenv(token_name)
        if token_value == '' or token_value is None:
            error_message = f'Отсутствует переменная окружения: {token_name}'
            logging.critical(error_message)
            raise SystemExit(error_message)


def send_message(bot, message):
    '''Функция отправляет сообщение в чат'''

    try:
        bot.send_message(chat_id=23436567687654, text=message)
        logging.debug('Отправлено сообщение в Telegram')
    except Exception as error:
        logging.error(f'Ошибка отправки {error}')


def get_api_answer(timestamp):
    '''Делает запрос к единственному эндпоинту API-сервиса.
    В случае успешного запроса должна вернуть ответ API,
    приведенный к типу данных Python.'''

    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception('Ошибка при запросе к API')
    except requests.RequestException as error:
        logging.error(f'Ошибка при запросе к API: {error}')
        return None


def check_response(response):
    '''Проверяет ответ API на соответствие документации.
    На вход получает результат функции get_api_answer()'''

    if not isinstance(response, dict):
        err_message = "Полученный ответ не является словарем"
        logging.error(err_message)
        raise TypeError(err_message)

    required_keys = {"homeworks", "current_date"}
    if not required_keys.issubset(response.keys()):
        err_message = ('В ответе API домашки нет ключей '
                       '`homeworks` или `current_date`')
        logging.error(err_message)
        raise Exception(err_message)

    if not isinstance(response["homeworks"], list):
        err_message = ('В ответе API домашки данные под ключом '
                       '"homeworks" приходят не в виде списка.')
        logging.error(err_message)
        raise TypeError(err_message)

    if not response["homeworks"]:
        err_message =('В словаре нет ключа "homeworks"')
        logging.error(err_message)
        return False
      
    if not all(isinstance(hw, dict) for hw in response['homeworks']):
        err_message = 'Тип данных в "homeworks" не является словарем'
        raise TypeError(err_message)

    return True

def parse_status(homework):
    '''Извлекает из информации о конкретной домашней работе
    статус этой работы. В случае успеха, функция возвращает
    подготовленную для отправки в Telegram строку,
    содержащую один из вердиктов словаря HOMEWORK_VERDICTS.'''

    if 'homework_name' in homework:
        homework_name = homework.get('homework_name')
    else:
        raise ValueError('В ответе API домашки нет ключа `homework_name`.')
    if 'status' in homework:
        status = homework.get('status')
        if status in HOMEWORK_VERDICTS:
            verdict = HOMEWORK_VERDICTS[status]
            return str(f'Изменился статус проверки работы "{homework_name}". {verdict}')
        else:
            raise ValueError('Статус не соответствует ожидаемому')
    else:
        raise ValueError('Ошибка при получении статуса')
        

last_sent_message = None

def main():
    '''Основная логика приложения.'''

    global last_sent_message # Переменная для сохранения сообщения
    logging.info('Бот запущен') # Логируем запуск бота

    check_tokens() # Запускаем функцию проверки токенов

    bot = telegram.Bot(token=TELEGRAM_TOKEN) # Создаем экземпляр бота, приязываем его к нашему боту токеном

    timestamp = 0 #int(time.time()) # Получем временную метку со временем "сейчас"

    while True:
        try:
            response = get_api_answer(timestamp) # Делаем запрос к эндпоинту, для получения последней работы
            if check_response(response): # Проверяем ответ API на соответствие документации
                if response['homeworks'] == []:
                    break
                status = parse_status(response.get('homeworks')[0]) # Обрабатываем ответ на запрос эндпоинта проверенный выше и если  
                if status:
                    if status != last_sent_message:
                        send_message(bot, status)
                        last_sent_message = status
            else:
                logging.error('Ответ API не соответствует документации')
                break
        except Exception as error:
            message = f'Ошибка в работе программы: {error}'
            send_message(bot, message)
            logging.error(f'Ошибка при отправке сообщения в Telegram: {error}')

        time.sleep(RETRY_PERIOD)
    time.sleep(RETRY_PERIOD)
    if __name__ == '__main__':
        main()

if __name__ == '__main__':
    main()

import logging
import os
import sys
import time

from dotenv import load_dotenv
import requests
import telegram

from telegram import TelegramError
from exceptions import (
    APIRequestsError,
    UnknownHomeworkStatusError,
    UnknownHomeworkNameError,
    MissingHomeworksKeyError,
)


load_dotenv()


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

TOKENS = {
    'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
    'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
    'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
}

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
PAYLOAD = {'from_date': int(time.time())}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка доступности переменных окружения."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
    }
    for key, value in tokens.items():
        if not value:
            logging.critical(
                f'Отсутствуют необходимые переменные окружения: {key}'
            )
            raise EnvironmentError(
                f'Отсутствуют необходимые переменные окружения: {key}'
            )
    return True


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        response = bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.debug('Сообщение успешно отправлено в Telegram')
        if response:
            logger.debug('Сообщение успешно отправлено в Телеграм')
        else:
            logger.error('Сообщение не отправлено в Телеграм')
    except Exception as error:
        logger.error(f'Ошибка при отправке сообщения в Телеграм: {error}')


def get_api_answer(timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=PAYLOAD,
        )
        if homework_statuses.status_code != 200:
            logger.error('Ошибка при запросе к API')
            raise APIRequestsError(
                homework_statuses.status_code,
                'Ошибка при запросе к API',
            )
        return homework_statuses.json()
    except requests.RequestException as error:
        logger.error(f'Ошибка при запросе к API: {error}')
        return None


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    try:
        if not isinstance(response, dict):
            logger.error('Полученная структура данных не словарь.')
            raise TypeError('Полученная структура данных не словарь.')
        if not isinstance(response['homeworks'], list):
            logger.error('Полученная структура данных не список.')
            raise TypeError('Полученная структура данных не список.')
        if response['homeworks']:
            return response['homeworks'][0]
        else:
            raise IndexError('Полученная структура данных пустой список')
    except KeyError:
        raise MissingHomeworksKeyError()


def parse_status(homework):
    """Извлечение информации о статусе конкретной домашней работы."""
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS:
        raise UnknownHomeworkStatusError(status)
    if not homework_name:
        raise UnknownHomeworkNameError(homework_name)
    verdict = HOMEWORK_VERDICTS.get(status, 'Статус неизвестен')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    errors_dict = {'error': None}

    while True:
        try:
            api_response = get_api_answer(timestamp)
            check_response(api_response)
            homework = api_response['homeworks']
            if not homework:
                message = 'Нет ДЗ для проверки'
                logger.debug(message)
            else:
                message = parse_status(homework[0])
                if errors_dict.get(homework[0]['homework_name']) != message:
                    send_message(bot, message)
                    timestamp = api_response.get('current_date', timestamp)
                    errors_dict[homework[0]['homework_name']] = message
                else:
                    message = 'Статус домашки не изменился.'
                    logger.debug(message)
        except TelegramError as error:
            logger.error(error)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if errors_dict['error'] != message:
                logger.error(message)
                send_message(bot, message)
            errors_dict['error'] = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()

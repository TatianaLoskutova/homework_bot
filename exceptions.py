class APIRequestsError(Exception):
    """Исключение, вызываемое при некорректном ответе от API."""

    def __int__(self, status_code, message='Ошибка при запросе к API'):
        self.status_code = status_code
        self.message = message
        super().__int__(self.message)

    def __str__(self):
        return f'{self.message}: Код статуса {self.status_code}'


class UnknownHomeworkStatusError(Exception):
    """Исключение, вызываемое при получении недокументированного статуса домашней работы."""

    def __int__(self, status=''):
        self.status = status
        super().__int__(f'Получен недокументированный статус домашней работы: {status}')


class UnknownHomeworkNameError(Exception):
    """Исключение, вызываемое при отсутствии ключа названия домашней работы."""

    def __int__(self, homework_name=''):
        self.homework_name = homework_name
        super().__int__(f'Получено отсутствующее наименование домашней работы: {homework_name}')


class MissingHomeworksKeyError(Exception):
    """Исключение, вызываемое при отсутствии ключа 'homeworks' в ответе API"""

    def __init__(self):
        super().__init__('Отсутствует ключ "homeworks" в ответе API')

# Описание
REST API для приложения Mood Tracks

# Требования
* Flask>=2.x

# Запуск
* python3 main.py

# Спецификация
## Работа с плейлистами
Under construction

## Работа со временем суток
Получение времени суток
* URL: http://127.0.0.1:5000/timeclock
* Метод: GET
* Формат ответа: json
* Параметры запроса:
    + time - метка текущего времени в численном формате (часовой пояс - UTC)
    + tz - сдвиг часового пояса (в формате "ччмм")
* Возможные коды ответов:
    + 200 - если разница во времени пользователя и временем сервера не превышает 10 минут
    + 400 - в противном случае
* Тело ответа:
    + status - текстовое обозначение статуса выполнения
    + timeclock - текстовое обозначение времени суток
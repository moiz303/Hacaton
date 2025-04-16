from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/api/data', methods=['POST'])
def receive_data():
    """
    Маршрут для получения данных от фронтенда.
    Принимает POST-запрос с JSON-данными, выводит их и возвращает ответ.
    """
    data = request.json  # Получаем JSON-данные из запроса
    print(f"Получены данные: {data}")  # Выводим данные в консоль для примера
    # Здесь можно добавить любую обработку данных
    return jsonify({'message': 'Данные получены', 'data': data})  # Возвращаем ответ фронтенду

if __name__ == '__main__':
    app.run(debug=True)  # Запускаем сервер в режиме отладки на порту 5000
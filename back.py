import argparse
import requests
import tempfile
import subprocess
import datetime
from smth import generate_report  # Импортируем функцию из main.py

def parse_github_url(url):
    """
    Преобразует ссылку на файл GitHub в сырую ссылку для скачивания.
    
    Например: 
    https://github.com/user/repo/blob/branch/path/to/file.py -> 
    https://raw.githubusercontent.com/user/repo/branch/path/to/file.py
    """
    parts = url.split('/')
    if len(parts) < 7 or parts[2] != 'github.com' or parts[5] != 'blob':
        raise ValueError(f"Неверная ссылка на файл GitHub: {url}")
    user = parts[3]
    repo = parts[4]
    branch = parts[6]
    path = '/'.join(parts[7:])
    raw_url = f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/{path}"
    return raw_url

def download_file(url):
    """Скачивает содержимое файла по ссылке GitHub."""
    raw_url = parse_github_url(url)
    response = requests.get(raw_url)
    if response.status_code != 200:
        raise Exception(f"Не удалось скачать файл по ссылке: {url} (статус: {response.status_code})")
    return response.text

def analyze_code(urls, start_date, end_date):
    """
    Анализирует код из файлов по указанным ссылкам с помощью flake8 и формирует данные для отчёта.
    
    :param urls: Список ссылок на файлы GitHub
    :param start_date: Начальная дата периода
    :param end_date: Конечная дата периода
    :return: Словарь с данными для generate_report
    """
    linter_issues = []
    
    for url in urls:
        try:
            # Скачиваем содержимое файла
            code = download_file(url)
            
            # Сохраняем во временный файл для анализа
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
                temp_file.write(code)
                temp_file_path = temp_file.name
            
            # Запускаем flake8 для анализа кода
            result = subprocess.run(['flake8', temp_file_path], capture_output=True, text=True)
            issues = result.stdout.splitlines()
            for issue in issues:
                linter_issues.append(f"{url}: {issue}")
            
            # Удаляем временный файл
            subprocess.run(['rm', temp_file_path])
        
        except Exception as e:
            linter_issues.append(f"Ошибка при анализе {url}: {str(e)}")
    
    # Формируем данные для отчёта
    data = {
        'Period': f"{start_date} - {end_date}",
        'Language': 'Python',
        'Size': 'N/A',  # Размер проекта не вычисляется в этой версии
        'Score': 8 if not linter_issues else 5,  # Пример: оценка зависит от наличия проблем
        'Linter Issues': linter_issues if linter_issues else ['Нет проблем'],
        'Antipatterns': ['Пример антипаттерна'] if linter_issues else ['Нет данных'],
        'Positives': ['Хорошая структура кода'],
        'Additions': 0,  # Статистика изменений не вычисляется в этой версии
        'Deletions': 0
    }
    
    return data

def main():
    # Настраиваем парсер аргументов командной строки
    parser = argparse.ArgumentParser(description='Генерация отчёта о качестве кода')
    parser.add_argument('--urls', nargs='+', required=True, help='Ссылки на файлы GitHub')
    parser.add_argument('--start-date', required=True, help='Начальная дата периода (YYYY-MM-DD)')
    parser.add_argument('--end-date', required=True, help='Конечная дата периода (YYYY-MM-DD)')
    parser.add_argument('--output', default='code_quality_report.rpt', help='Имя выходного файла')
    
    # Парсим аргументы
    args = parser.parse_args()
    
    # Анализируем код и получаем данные
    data = analyze_code(args.urls, args.start_date, args.end_date)
    
    # Генерируем отчёт
    generate_report(data, args.output)

if __name__ == '__main__':
    main()

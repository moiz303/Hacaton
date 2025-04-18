import datetime
def generate_report(input_data, output_file):
    """
    Генерирует отчёт в формате .rpt из входных данных JSON.

    :param input_data: Словарь с входными данными
    :param output_file: Имя выходного файла (с расширением .rpt)
    """
    try:
        # Формируем содержимое отчёта
        report_content = f"""Отчёт о качестве кода
{'=' * 40}

Период анализа: {input_data.get('Period', 'N/A')}
Язык программирования: {input_data.get('Language', 'N/A').capitalize()}
Размер проекта: {input_data.get('Size', 'N/A')}
Общая оценка: {input_data.get('Score', 0)}/10

{'=' * 40}
Проблемы линтера:
{format_linter_issues(input_data.get('Linter Issues', []))}

{'=' * 40}
Антипаттерны:
{format_list_items(input_data.get('Antipatterns', []))}

{'=' * 40}
Положительные аспекты:
{format_list_items(input_data.get('Positives', []))}

{'=' * 40}
Статистика изменений:
Добавлено строк: {input_data.get('Additions', 0)}
Удалено строк: {input_data.get('Deletions', 0)}

{'=' * 40}
Отчёт сформирован: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        # Записываем отчёт в файл
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_content)

        print(f"Отчёт успешно сформирован и сохранён в файл: {output_file}")

    except Exception as e:
        print(f"Ошибка при формировании отчёта: {str(e)}")


def format_linter_issues(issues):
    """Форматирует список проблем линтера для отчёта."""
    if not issues:
        return "  Нет проблем"
    return '\n'.join(f"  • {issue}" for issue in issues)


def format_list_items(items):
    """Форматирует список элементов для отчёта."""
    if not items:
        return "  Нет данных"
    return '\n'.join(f"  • {item}" for item in items)


if __name__ == '__main__':
    # ▶️ Пример использования
    example_mr = MergeRequestReport(
        github_file_urls=["https://github.com/moiz303/lode_runner/blob/master/levels.py"],  # файл, который хотим проанализировать
        positives=["Хорошие тесты", "Чистый код"],
        created_at=dt.datetime(2023, 12, 23),
        merged_at=dt.datetime(2025, 4, 16),
    )
    # Генерируем отчёт
    generate_report(example_mr.to_dict(), "code_quality_report.rpt")
    

import datetime as dt
from test_all import MergeRequestReport, generate_report

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

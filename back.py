from test_all import MergeRequestReport
from gitlab import Gitlab
from typing import List, Tuple
import datetime as dt

def get_merge_requests(email: str, date_period: Tuple[dt.datetime, dt.datetime], repo_url: str) -> List['MergeRequestReport']:
    """
    Централизованная функция для получения отчетов по merge requests из GitLab.

    Args:
        email (str): Email автора merge requests.
        date_period (Tuple[dt.datetime, dt.datetime]): Период дат (начало, конец) для фильтрации MR.
        repo_url (str): Ссылка на репозиторий в формате 'namespace/project'.

    Returns:
        List[MergeRequestReport]: Список объектов MergeRequestReport для каждого merge request.

    Notes:
        - Требуется токен GitLab API.
        - Предполагается, что класс MergeRequestReport доступен в текущем модуле.
        - Репозиторий должен быть доступен через GitLab API.
    """
    # Инициализация клиента GitLab
    gl = Gitlab('https://gitlab.com', private_token='your_gitlab_token_here')  # Замените на ваш токен
    try:
        project = gl.projects.get(repo_url)
    except Exception as e:
        print(f"Ошибка при доступе к репозиторию {repo_url}: {e}")
        return []

    # Получение merge requests за указанный период
    start_date, end_date = date_period
    try:
        mrs = project.mergerequests.list(
            state='merged',
            created_after=start_date,
            created_before=end_date
        )
    except Exception as e:
        print(f"Ошибка при получении merge requests: {e}")
        return []

    reports = []
    for mr in mrs:
        # Фильтрация по email автора
        if mr.author['email'] == email:
            # Получение списка измененных файлов
            try:
                changes = mr.changes()['changes']
                file_paths = [change['new_path'] for change in changes]
            except Exception as e:
                print(f"Ошибка при получении изменений для MR {mr.iid}: {e}")
                file_paths = []

            # Формирование отчета
            try:
                report = MergeRequestReport(
                    id=mr.iid,
                    title=mr.title,
                    link=mr.web_url,
                    created_at=dt.datetime.fromisoformat(mr.created_at.replace('Z', '+00:00')),
                    merged_at=dt.datetime.fromisoformat(mr.merged_at.replace('Z', '+00:00')),
                    file_paths=file_paths,
                    positives=["Хорошие тесты", "Чистый код"],  # Можно заменить на динамическую логику
                    base_commit=mr.diff_refs['base_sha'],
                    head_commit=mr.diff_refs['head_sha']
                )
                reports.append(report)
            except Exception as e:
                print(f"Ошибка при создании отчета для MR {mr.iid}: {e}")

    return reports

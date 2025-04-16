import subprocess
import os
import json
import datetime as dt
import flake8
from typing import List


class MergeRequestReport:
    def __init__(self, id, title, link, created_at, merged_at, file_paths: List[str], positives: List[str],
                 base_commit: str, head_commit: str):
        self.id = id
        self.title = title
        self.link = link
        self.created_at = created_at
        self.merged_at = merged_at
        self.file_paths = file_paths
        self.positives = positives
        self.flake8_issues = self.run_flake8()
        self.antipatterns = self.detect_antipatterns()

        self.base_commit = base_commit
        self.head_commit = head_commit

        self.additions, self.deletions = self.estimate_changes()

    def run_flake8(self) -> List[str]:
        """Запускает flake8 на указанных файлах и возвращает список проблем."""
        issues = []
        for path in self.file_paths:
            try:
                result = subprocess.run(['flake8', path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if result.stdout:
                    issues.extend(result.stdout.strip().split('\n'))
            except Exception as e:
                print(f"Ошибка при запуске flake8: {e}")
        return issues

    def detect_antipatterns(self) -> List[str]:
        """Простая эвристика для антипаттернов (можно улучшить)"""
        antipatterns = []
        for issue in self.flake8_issues:
            if 'E501' in issue:
                antipatterns.append("слишком длинная строка (E501)")
            if 'C901' in issue:
                antipatterns.append("слишком сложная функция (C901)")
            if 'F401' in issue:
                antipatterns.append("неиспользуемый импорт (F401)")
        return list(set(antipatterns))

    def estimate_changes(self):
        additions = 0
        deletions = 0
        for path in self.file_paths:
            try:
                result = subprocess.run(
                    ['git', 'diff', '--numstat', self.base_commit, self.head_commit, '--', path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                for line in result.stdout.strip().split('\n'):
                    if not line:
                        continue
                    add_str, del_str, _ = line.split('\t')
                    if add_str != '-':
                        additions += int(add_str)
                    if del_str != '-':
                        deletions += int(del_str)
            except Exception as e:
                print(f"Ошибка при анализе git diff для {path}: {e}")
        return additions, deletions

    def size_category(self):
        total_changes = self.additions + self.deletions
        if total_changes <= 50:
            return 'S'
        elif total_changes <= 300:
            return 'M'
        else:
            return 'L'

    def quality_score(self):
        base = 10
        penalty = len(self.flake8_issues) * 0.5 + len(self.antipatterns)
        return max(1, int(base - penalty))

    def period(self):
        return f"{self.created_at.date()} — {self.merged_at.date()}"

    def to_dict(self):
        return {
            "ID": self.id,
            "Title": self.title,
            "Link": self.link,
            "Period": self.period(),
            "Size": self.size_category(),
            "Score": self.quality_score(),
            "Issues (flake8)": self.flake8_issues,
            "Antipatterns": self.antipatterns,
            "Positives": self.positives,
        }

    # ▶️ Пример использования
example_mr = MergeRequestReport(
    created_at=dt.datetime(2023, 11, 21),
    merged_at=dt.datetime(2024, 5, 17),
    file_paths=["main.py"],  # файл, который хотим проанализировать - меняется твоим кодом
    positives=["Хорошие тесты", "Чистый код"],
    base_commit="db57f1e98583824741154d37312c5a727ecac3a6",
    head_commit="c364b98e7f068e49e004bbd301dc1f68dd0fb106"
)

# 📤 Печать отчёта
print(json.dumps(example_mr.to_dict(), indent=4, ensure_ascii=False))

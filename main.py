import subprocess
import os
from datetime import datetime
import json
from typing import List

class MergeRequestReport:
    def __init__(self, id, title, link, created_at, merged_at, file_paths: List[str], positives: List[str]):
        self.id = id
        self.title = title
        self.link = link
        self.created_at = created_at
        self.merged_at = merged_at
        self.file_paths = file_paths
        self.positives = positives
        self.flake8_issues = self.run_flake8()
        self.antipatterns = self.detect_antipatterns()
        self.additions = self.estimate_additions()
        self.deletions = 0  # можно доработать через Git diff

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
        """Простая эвристика для антипаттернов (можно улучшить)."""
        antipatterns = []
        for issue in self.flake8_issues:
            if 'E501' in issue:
                antipatterns.append("слишком длинная строка (E501)")
            if 'C901' in issue:
                antipatterns.append("слишком сложная функция (C901)")
            if 'F401' in issue:
                antipatterns.append("неиспользуемый импорт (F401)")
        return list(set(antipatterns))

    def estimate_additions(self):
        # Можно доработать через git diff, пока просто симуляция
        return sum(os.path.getsize(path) // 50 for path in self.file_paths)  # очень грубая оценка

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

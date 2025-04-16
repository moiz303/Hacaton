import subprocess
from typing import List, Dict, Optional
from datetime import datetime
import json


class MergeRequestReport:
    # Конфигурация линтеров для разных языков
    LINTERS_CONFIG = {
        'python': {
            'command': 'flake8',
            'file_extensions': ['.py'],
            'antipatterns': {
                'E501': "слишком длинная строка",
                'C901': "слишком сложная функция",
                'F401': "неиспользуемый импорт"
            }
        },
        'javascript': {
            'command': 'eslint',
            'file_extensions': ['.js', '.jsx', '.ts', '.tsx'],
            'antipatterns': {
                'no-unused-vars': "неиспользуемая переменная",
                'complexity': "слишком сложная функция",
                'max-len': "слишком длинная строка"
            }
        },
        'ruby': {
            'command': 'rubocop',
            'file_extensions': ['.rb'],
            'antipatterns': {
                'Metrics/LineLength': "слишком длинная строка",
                'Metrics/CyclomaticComplexity': "слишком сложная функция",
                'Lint/UnusedMethodArgument': "неиспользуемый аргумент метода"
            }
        },
        'java': {
            'command': 'java -jar checkstyle-10.12.4-all.jar -c google_checks.xml',
            'file_extensions': ['.java'],
            'antipatterns': {
                'JavadocMethod': "отсутствует Javadoc для метода",
                'AvoidStarImport': "использование импорта через *",
                'LineLength': "слишком длинная строка",
                'CyclomaticComplexity': "слишком сложный метод",
                'UnusedImports': "неиспользуемый импорт"
            },
            'output_parser': lambda x: x.split('\n')[1:-1]  # Парсинг вывода Checkstyle
        },
        'php': {
            'command': 'phpcs',
            'file_extensions': ['.php'],
            'antipatterns': {
                'PSR1.Methods.CamelCapsMethodName': "метод не в camelCase",
                'Squiz.WhiteSpace.ScopeClosingBrace': "неправильный отступ закрывающей скобки",
                'Generic.Files.LineLength': "слишком длинная строка",
                'PSR12.Operators.SpreadOperatorSpacing': "неправильные пробелы вокруг ...",
                'PSR2.Methods.MethodDeclaration.Underscore': "использование _ в именах методов"
            },
            'output_parser': lambda x: [line.strip() for line in x.split('\n') if line.strip()]
        }
    }

    def __init__(
            self,
            created_at: datetime,
            merged_at: datetime,
            file_paths: List[str],
            positives: List[str],
            base_commit: str,
            head_commit: str,
            language: str = 'python'
    ):
        self.created_at = created_at
        self.merged_at = merged_at
        self.file_paths = self._filter_files_by_language(file_paths, language)
        self.positives = positives
        self.language = language.lower()

        self.base_commit = base_commit
        self.head_commit = head_commit

        # Аналитические данные
        self.linter_issues = self.run_linter()
        self.antipatterns = self.detect_antipatterns()
        self.additions, self.deletions = self.estimate_changes()

    def _filter_files_by_language(self, file_paths: List[str], language: str) -> List[str]:
        """Фильтрует файлы по расширениям, соответствующим языку"""
        if language not in self.LINTERS_CONFIG:
            raise ValueError(f"Unsupported language: {language}")

        extensions = self.LINTERS_CONFIG[language]['file_extensions']
        return [f for f in file_paths if any(f.endswith(ext) for ext in extensions)]


    def run_linter(self) -> List[str]:
        if self.language not in self.LINTERS_CONFIG:
            return []

        config = self.LINTERS_CONFIG[self.language]
        issues = []

        for path in self.file_paths:
            try:
                # Специальная обработка Java (Checkstyle)
                if self.language == 'java':
                    cmd = config['command'].split() + [path]
                else:
                    cmd = [config['command'], path]

                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                if result.stdout:
                    output = result.stdout
                    if 'output_parser' in config:
                        issues.extend(config['output_parser'](output))
                    else:
                        issues.extend(output.strip().split('\n'))

            except Exception as e:
                print(f"Ошибка при запуске линтера {config['command']}: {e}")

        return issues


    def detect_antipatterns(self) -> List[str]:
        """Ищет антипаттерны для текущего языка"""
        if self.language not in self.LINTERS_CONFIG:
            return []

        antipatterns_config = self.LINTERS_CONFIG[self.language]['antipatterns']
        found_antipatterns = []

        for issue in self.linter_issues:
            for code, description in antipatterns_config.items():
                if code in issue:
                    found_antipatterns.append(description)

        return list(set(found_antipatterns))

    def estimate_changes(self) -> tuple[int, int]:
        """Подсчитывает добавления и удаления через git diff"""
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
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        add_str, del_str = parts[0], parts[1]
                        if add_str != '-':
                            additions += int(add_str)
                        if del_str != '-':
                            deletions += int(del_str)
            except Exception as e:
                print(f"Ошибка при анализе git diff для {path}: {e}")

        return additions, deletions

    def size_category(self) -> str:
        """Классифицирует MR по размеру изменений"""
        total_changes = self.additions + self.deletions
        if total_changes <= 50:
            return 'S'
        elif total_changes <= 300:
            return 'M'
        else:
            return 'L'

    def quality_score(self) -> int:
        """Вычисляет оценку качества кода"""
        base = 10
        penalty = len(self.linter_issues) * 0.5 + len(self.antipatterns)
        return max(1, int(base - penalty))

    def period(self) -> str:
        """Возвращает период жизни MR"""
        return f"{self.created_at.date()} — {self.merged_at.date()}"

    def to_dict(self) -> Dict:
        """Преобразует отчет в словарь"""
        return {
            "Language": self.language,
            "Period": self.period(),
            "Size": self.size_category(),
            "Score": self.quality_score(),
            "Linter Issues": self.linter_issues,
            "Antipatterns": self.antipatterns,
            "Positives": self.positives,
            "Additions": self.additions,
            "Deletions": self.deletions,
        }


if __name__ == '__main__':
    # ▶️ Пример использования
    example_mr = MergeRequestReport(
        created_at=datetime(2023, 11, 21),
        merged_at=datetime(2024, 5, 17),
        file_paths=["main.py"],  # файл, который хотим проанализировать - меняется твоим кодом
        positives=["Хорошие тесты", "Чистый код"],
        base_commit="db57f1e98583824741154d37312c5a727ecac3a6",
        head_commit="c364b98e7f068e49e004bbd301dc1f68dd0fb106"
    )

    # 📤 Печать отчёта
    print(json.dumps(example_mr.to_dict(), indent=4, ensure_ascii=False))

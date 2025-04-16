import subprocess
import os
import json
import datetime as dt
import requests
import tempfile
from typing import List, Dict


class MergeRequestReport:
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
        created_at,
        merged_at,
        github_file_urls: List[str],
        positives: List[str],
        base_commit: str,
        head_commit: str,
        language: str = 'python'
    ):
        self.created_at = created_at
        self.merged_at = merged_at
        self.language = language.lower()
        self.file_urls = self._filter_files_by_language(github_file_urls, language)
        self.positives = positives
        self.base_commit = base_commit
        self.head_commit = head_commit

        # Кэш для загруженных временных файлов
        self.temp_files = self._download_files()

        self.linter_issues = self.run_linter()
        self.antipatterns = self.detect_antipatterns()
        self.additions, self.deletions = self.estimate_changes()

        # Очистка временных файлов
        self._cleanup_temp_files()

    def _filter_files_by_language(self, urls: List[str], language: str) -> List[str]:
        extensions = self.LINTERS_CONFIG[language]['file_extensions']
        return [url for url in urls if any(url.endswith(ext) for ext in extensions)]

    def _download_files(self) -> Dict[str, str]:
        """Скачивает файлы по ссылке и сохраняет во временные файлы"""
        temp_files = {}
        for url in self.file_urls:
            try:
                response = requests.get(url)
                response.raise_for_status()
                ext = os.path.splitext(url)[1]
                with tempfile.NamedTemporaryFile(delete=False, suffix=ext, mode='w', encoding='utf-8') as tmp_file:
                    tmp_file.write(response.text)
                    temp_files[url] = tmp_file.name
            except Exception as e:
                print(f"Ошибка при загрузке {url}: {e}")
        return temp_files

    def run_linter(self) -> List[str]:
        config = self.LINTERS_CONFIG.get(self.language)
        if not config:
            return []

        issues = []
        for url, local_path in self.temp_files.items():
            try:
                cmd = (
                    config['command'].split() + [local_path]
                    if self.language == 'java' else
                    [config['command'], local_path]
                )
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

                output = result.stdout.strip()
                if output:
                    if 'output_parser' in config:
                        issues.extend(config['output_parser'](output))
                    else:
                        issues.extend(output.split('\n'))

            except Exception as e:
                print(f"Ошибка линтинга {url}: {e}")
        return issues

    def detect_antipatterns(self) -> List[str]:
        config = self.LINTERS_CONFIG.get(self.language)
        if not config:
            return []
        patterns = config['antipatterns']
        found = []

        for issue in self.linter_issues:
            for code, description in patterns.items():
                if code in issue:
                    found.append(description)

        return list(set(found))

    def estimate_changes(self) -> tuple[int, int]:
        # Эмуляция - у нас нет git diff, но можно добавить API GitHub диффа
        # Здесь пока просто нули
        return 0, 0

    def _cleanup_temp_files(self):
        for path in self.temp_files.values():
            try:
                os.remove(path)
            except Exception as e:
                print(f"Не удалось удалить временный файл {path}: {e}")

    def size_category(self) -> str:
        total_changes = self.additions + self.deletions
        if total_changes <= 50:
            return 'S'
        elif total_changes <= 300:
            return 'M'
        return 'L'

    def quality_score(self) -> int:
        base = 10
        penalty = len(self.linter_issues) * 0.5 + len(self.antipatterns)
        return max(1, int(base - penalty))

    def period(self):
        return f"{self.created_at.date()} — {self.merged_at.date()}"

    def to_dict(self) -> Dict:
        """Преобразует отчет в словарь"""
        return {
            "Period": self.period(),
            "Language": self.language,
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
        github_file_urls=["https://raw.githubusercontent.com/moiz303/Hacaton/refs/heads/master/test_all.py"],  # файл, который хотим проанализировать
        positives=["Хорошие тесты", "Чистый код"],
        base_commit="db57f1e98583824741154d37312c5a727ecac3a6",
        head_commit="c364b98e7f068e49e004bbd301dc1f68dd0fb106",
        created_at=dt.datetime(2023, 11, 7),
        merged_at=dt.datetime(2024, 5, 13)
    )

    # 📤 Печать отчёта
    print(json.dumps(example_mr.to_dict(), indent=4, ensure_ascii=False))

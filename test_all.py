import json
import os
import tempfile
import requests
import subprocess
from typing import List, Dict, Optional
import datetime as dt


class DeepSeekAPI:
    def __init__(self):
        self.api_key = "sk-c036153a3e834d83b96d8988b4b6b66a"
        self.base_url = "https://api.deepseek.com/v1"

    def generate(self, model: str, prompt: str, max_tokens: int, temperature: float):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        response = requests.post(f"{self.base_url}/completions", json=data, headers=headers)
        return response.json()


class MergeRequestReport:
    # Базовые настройки для линтеров (можно использовать как fallback)
    BASE_LINTERS_CONFIG = {
        'python': {
            'command': 'flake8',
            'file_extensions': ['.py'],
        },
        'javascript': {
            'command': 'eslint',
            'file_extensions': ['.js', '.jsx', '.ts', '.tsx'],
        },
        'ruby': {
            'command': 'rubocop',
            'file_extensions': ['.rb'],
        },
        'java': {
            'command': 'java -jar checkstyle-10.12.4-all.jar -c google_checks.xml',
            'file_extensions': ['.java'],
            'output_parser': lambda x: x.split('\n')[1:-1]
        },
        'php': {
            'command': 'phpcs',
            'file_extensions': ['.php'],
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
            language: str = 'python',
            deepseek_api_key: Optional[str] = None
    ):
        self.created_at = created_at
        self.merged_at = merged_at
        self.language = language.lower()
        self.positives = positives
        self.base_commit = base_commit
        self.head_commit = head_commit

        # Инициализация DeepSeek
        self.deepseek = DeepSeekAPI() if deepseek_api_key else None

        # Получаем конфиг линтера
        self.linter_config = self._get_linter_config()

        # Фильтрация и обработка файлов
        self.file_urls = self._filter_files_by_language(github_file_urls, language)
        self.temp_files = self._download_files()
        self.linter_issues = self.run_linter()
        self.antipatterns = self.detect_antipatterns()
        self.additions, self.deletions = self.estimate_changes()
        self._cleanup_temp_files()

    def _get_linter_config(self) -> Dict:
        """Получаем конфигурацию линтера через DeepSeek API"""
        if not self.deepseek:
            return self.BASE_LINTERS_CONFIG.get(self.language, {})

        try:
            prompt = (
                f"Provide configuration for {self.language} linter including:\n"
                "1. Command to run\n"
                "2. File extensions\n"
                "3. Common antipatterns with codes and Russian descriptions\n"
                "Return only valid JSON without any additional text."
            )

            response = self.deepseek.generate(
                model="deepseek-coder",
                prompt=prompt,
                max_tokens=1000,
                temperature=0.3
            )

            # Парсинг ответа (может потребоваться адаптация под формат ответа DeepSeek)
            config = self._parse_deepseek_response(response)

            # Объединяем с базовой конфигурацией
            base_config = self.BASE_LINTERS_CONFIG.get(self.language, {})
            return {**base_config, **config}

        except Exception as e:
            print(f"Error getting linter config from DeepSeek: {e}")
            return self.BASE_LINTERS_CONFIG.get(self.language, {})

    def _parse_deepseek_response(self, response) -> Dict:
        """Парсит ответ от DeepSeek API в словарь"""
        # Реализация зависит от формата ответа DeepSeek API
        # Это примерная реализация - возможно, потребуется адаптация
        try:
            # Предполагаем, что ответ содержит JSON в тексте
            json_str = response.choices[0].text
            return eval(json_str)
        except Exception as e:
            print(f"Error parsing DeepSeek response: {e}")
            return {}

    def _filter_files_by_language(self, urls: List[str], language: str) -> List[str]:
        if not hasattr(self, 'linter_config') or not self.linter_config:
            return []
        extensions = self.linter_config.get('file_extensions', [])
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
        if not self.linter_config:
            return []

        issues = []
        for url, local_path in self.temp_files.items():
            try:
                cmd = (
                    self.linter_config['command'].split() + [local_path]
                    if self.language == 'java' else
                    [self.linter_config['command'], local_path]
                )
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

                output = result.stdout.strip()
                if output:
                    if 'output_parser' in self.linter_config:
                        issues.extend(self.linter_config['output_parser'](output))
                    else:
                        issues.extend(output.split('\n'))

            except Exception as e:
                print(f"Ошибка линтинга {url}: {e}")
        return issues

    def detect_antipatterns(self) -> List[str]:
        if not self.linter_config or 'antipatterns' not in self.linter_config:
            return []

        patterns = self.linter_config['antipatterns']
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
        github_file_urls=["https://raw.githubusercontent.com/moiz303/Hacaton/refs/heads/master/back.py"],  # файл, который хотим проанализировать
        positives=["Хорошие тесты", "Чистый код"],
        base_commit="db57f1e98583824741154d37312c5a727ecac3a6",
        head_commit="c364b98e7f068e49e004bbd301dc1f68dd0fb106",
        created_at=dt.datetime(2023, 11, 7),
        merged_at=dt.datetime(2024, 5, 13),
    )

    # 📤 Печать отчёта
    print(json.dumps(example_mr.to_dict(), indent=4, ensure_ascii=False))

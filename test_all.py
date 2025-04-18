import json
import os
import tempfile
import requests
import subprocess
from typing import List, Dict, Optional, Tuple
import datetime as dt


class DeepSeekAPI:
    def __init__(self):
        #self.api_key = "sk-c036153a3e834d83b96d8988b4b6b66a"
        self.api_key = "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"
        #self.api_key = "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"
        self.base_url = "https://openrouter.ai/api/v1/chat"

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
            created_at: dt.datetime,
            merged_at: dt.datetime,
            github_file_urls: List[str],
            positives: List[str],
            language: str = 'python'
    ):
        self.created_at = created_at
        self.merged_at = merged_at
        self.language = language.lower()
        self.positives = positives
        self.repo_path = os.path.abspath("") # Сохраняем абсолютный путь

        # Получаем коммиты по датам
        self.base_commit = self._get_commit_by_date(created_at)
        self.head_commit = self._get_commit_by_date(merged_at)

        # Инициализация DeepSeek
        self.deepseek = DeepSeekAPI()

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
                "Return only valid JSON with first 20 antipatterns without any additional text."
            )

            response = self.deepseek.generate(
                model="deepseek/deepseek-chat:free",
                prompt=prompt,
                max_tokens=2500,
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

    def _parse_deepseek_response(self, response: dict) -> dict:
        """Парсит ответ от DeepSeek API"""
        # Default values if parsing fails
        default_result = {
            'command': 'flake8',
            'file_extensions': ['.py'],
            'antipatterns': {}
        }

        try:
            # 1. Validate response structure
            if not isinstance(response, dict):
                print("Error: Response is not a dictionary")
                return default_result

            if 'choices' not in response or not response['choices']:
                print("Error: No 'choices' in response")
                return default_result

            first_choice = response['choices'][0]['text']
            if not first_choice:
                print("Error: No 'text' in choices")
                return default_result

            # 2. Parse JSON content
            try:
                content = json.loads(first_choice[7:-4])
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                return default_result

            # 3. Extract command and extensions
            result = {
                'command': content.get('command', default_result['command']),
                'file_extensions': content.get('extensions', default_result['file_extensions']),
                'antipatterns': {}
            }

            # 4. Process antipatterns
            antipatterns = content.get('antipatterns', [])
            if not isinstance(antipatterns, list):
                print("Warning: 'antipatterns' is not a list")
                return result

            for item in antipatterns:
                if isinstance(item, dict):
                    code = item.get('code', '').strip()
                    desc = item.get('description', '').strip()
                    if code and desc:
                        result['antipatterns'][code] = desc

            return result

        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return default_result

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
                with tempfile.NamedTemporaryFile(
                        delete=False,
                        suffix=ext,
                        mode='w',
                        encoding='utf-8'
                ) as tmp_file:
                    tmp_file.write(response.text)
                    temp_files[url] = tmp_file.name
            except Exception as e:
                print(f"Ошибка при загрузке {url}: {e}")
        return temp_files

    def run_linter(self) -> List[str]:
        if not self.linter_config or not hasattr(self, 'temp_files') or not self.temp_files:
            return []

        issues = []
        for url, local_path in self.temp_files.items():
            try:
                # Формируем команду для линтера
                base_cmd = self.linter_config['command'].split()
                if self.language == 'java':
                    cmd = base_cmd + [local_path]
                else:
                    cmd = [self.linter_config['command'], local_path]

                # Выполняем линтер
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    check=False  # Не бросаем исключение при ненулевом коде возврата
                )

                # Обрабатываем вывод
                output = result.stdout.strip()
                if not output and result.stderr:
                    output = result.stderr.strip()

                if output:
                    if 'output_parser' in self.linter_config:
                        issues.extend(self.linter_config['output_parser'](output))
                    else:
                        issues.extend(output.split('\n'))

            except FileNotFoundError as e:
                print(f"Линтер не найден: {e}")
            except Exception as e:
                print(f"Неожиданная ошибка при линтинге {url}: {e}")

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

    def _get_commit_by_date(self, target_date: dt.datetime) -> str:
        """Возвращает последний коммит до указанной даты в локальном репозитории."""
        date_str = target_date.strftime("%Y-%m-%d %H:%M:%S")
        cmd = [
            "git", "-C", self.repo_path, "log",
            "--until", date_str,
            "--format=%H",
            "-n", "1",
            "HEAD"
        ]
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"Git error: {result.stderr}")
            return result.stdout.strip()
        except Exception as e:
            print(f"Error getting commit by date: {e}")
            return ""

    def estimate_changes(self) -> Tuple[int, int]:
        """Calculate additions and deletions between commits in local repo."""
        if not self.base_commit or not self.head_commit:
            return 0, 0

        try:
            cmd = [
                'git', '-C', self.repo_path, 'diff',
                '--numstat',
                '--diff-filter=AM',
                f"{self.base_commit}..{self.head_commit}"  # Используем диапазон коммитов
            ]
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )

            additions = deletions = 0
            for line in result.stdout.splitlines():
                parts = line.split('\t')
                if len(parts) >= 2:
                    try:
                        additions += int(parts[0]) if parts[0].isdigit() else 0
                        deletions += int(parts[1]) if parts[1].isdigit() else 0
                    except ValueError:
                        continue

            return additions, deletions

        except subprocess.CalledProcessError as e:
            print(f"Git diff error: {e.stderr}")
            return 0, 0
        except Exception as e:
            print(f"Error estimating changes: {e}")
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
        github_file_urls=["https://github.com/moiz303/Hacaton/blob/master/test_all.py",
                          "https://github.com/moiz303/lode_runner/blob/master/main.py"],  # файлы, который хотим проанализировать
        positives=["Хорошие тесты", "Чистый код"],
        created_at=dt.datetime(2023, 12, 23),
        merged_at=dt.datetime(2025, 4, 16),
    )

    # 📤 Печать отчёта
    print(json.dumps(example_mr.to_dict(), indent=4, ensure_ascii=False))
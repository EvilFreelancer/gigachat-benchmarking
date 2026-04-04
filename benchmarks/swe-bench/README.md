# SWE-bench Lite - Software Engineering Benchmark

**Что тестируется:** способность модели решать реальные задачи из GitHub issues - понять баг, найти нужный файл, сгенерировать патч и пройти тесты. Это один из самых сложных бенчмарков, требующий понимания кода, рассуждения и генерации точных изменений.

**Репозиторий:** https://github.com/SWE-bench/SWE-bench

## Результаты GigaChat3.1-10B-A1.8B

### Подходы и результаты

| Запуск | Метод | Score | Патчей применилось |
|--------|-------|-------|--------------------|
| Run 1 - Baseline | Single-pass, простой промпт | 0/300 (0%) | 14/300 (4.7%) |
| Run 2 - Few-shot | Single-pass, пример diff | 0/300 (0%) | 24/300 (8.0%) |
| Run 3 - CoT | Single-pass, chain-of-thought | прервано | - |
| Run 4 - DEVSYSTEM | Single-pass, кастомный chat template | 0/300 (0%) | 16/300 (5.3%) |
| Run 5 - Agentic | Multi-turn tool loop (пилот) | ожидает eval | 3/10 (30%) |

### Основная проблема

Модель генерирует невалидный unified diff формат:
- 179 инстансов - невалидный заголовок `@@` (например `@@ at line...` вместо `@@ -N,N +N,N @@`)
- 121 инстанс - нет заголовка diff вообще
- 0 инстансов - валидный формат `@@`

14 патчей прошли `git apply` благодаря толерантности утилиты `patch`, но ни один не прошел тесты.

## Что тестирует SWE-bench

300 реальных задач из открытых Python-проектов (Django, scikit-learn, matplotlib, sympy и др.). Каждая задача:
1. Содержит описание бага из GitHub issue
2. Предоставляет контекст кода (BM25-ретривер, топ-13K токенов)
3. Имеет набор тестов, которые должны пройти после применения патча

## Как запустить

### Предварительные требования

- Python 3.10+
- Docker (для запуска тестов в изолированных контейнерах)
- vLLM сервер с GigaChat
- ~120 GB свободного места (Docker-образы для оценки)

### Установка

```bash
pip install swebench datasets

# Или из исходников
git clone https://github.com/SWE-bench/SWE-bench.git
cd SWE-bench
pip install -e .
```

### Инференс (генерация патчей)

Скрипт инференса находится в `../../scripts/run_gigachat_inference.py`:

```bash
python scripts/run_gigachat_inference.py \
  --api-base http://gpu02:8083/v1 \
  --model ai-sage/GigaChat3.1-10B-A1.8B \
  --dataset princeton-nlp/SWE-bench_bm25_13K \
  --split test \
  --output predictions/output.jsonl \
  --max-tokens 4096 \
  --temperature 0
```

Параметры:
- `--api-base` - URL vLLM сервера
- `--dataset` - датасет с BM25-контекстом (13K токенов релевантного кода)
- `--max-tokens 4096` - лимит генерации (достаточно для большинства патчей)
- Время: ~80 мин на 300 задач

### Оценка (запуск тестов)

```bash
python -m swebench.harness.run_evaluation \
  --predictions_path predictions/output.jsonl \
  --swe_bench_tasks princeton-nlp/SWE-bench_Lite \
  --log_dir logs \
  --testbed testbed \
  --skip_existing \
  --timeout 900 \
  --cache_level env \
  --max_workers 4
```

Параметры:
- `--cache_level env` - кэширование Docker-окружений (ускоряет повторные запуски)
- `--max_workers 4` - параллельная оценка в 4 потока
- `--timeout 900` - 15 мин на тест каждого инстанса
- Время первого запуска: ~2-4 часа (сборка Docker-образов)
- Время повторного запуска: ~30-60 мин

### Агентный подход (Run 5)

Скрипт агента в `../../scripts/run_gigachat_agent.py`. Использует инструменты:
- `view_file(path, start, end)` - просмотр файла
- `str_replace(path, old, new)` - замена строки в файле
- `finish(patch)` - завершение с патчем

```bash
python scripts/run_gigachat_agent.py \
  --api-base http://gpu02:8083/v1 \
  --model ai-sage/GigaChat3.1-10B-A1.8B \
  --output predictions/agent_output.jsonl \
  --max-steps 15 \
  --instances 10
```

## Файлы в этой папке

- Этот README с описанием бенчмарка

Основные скрипты и результаты SWE-bench находятся в:
- `../../scripts/` - скрипты инференса и агента
- `../../predictions/` - сгенерированные патчи
- `../../results/` - результаты оценки
- `../../patches/` - кастомный chat template

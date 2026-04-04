# BFCL - Berkeley Function Calling Leaderboard

**Что тестируется:** способность модели корректно вызывать функции (tool calling) - правильно выбирать нужную функцию из набора и передавать аргументы нужных типов.

**Репозиторий:** https://github.com/ShishirPatil/gorilla/tree/main/berkeley-function-call-leaderboard

## Результаты GigaChat3.1-10B-A1.8B

| Категория | Accuracy | Тестов | Описание |
|-----------|----------|--------|----------|
| Simple Python | **89.50%** | 400 | Один вызов, Python-функции |
| Multiple | **91.00%** | 100 | Несколько последовательных вызовов в ответе |
| Simple Java | 61.00% | 50 | Один вызов, Java-функции |
| Simple JavaScript | 58.00% | 50 | Один вызов, JS-функции |
| Parallel | 0.00% | 100 | Несколько одновременных вызовов |
| Parallel Multiple | 0.00% | 50 | Комбинация parallel + multiple |
| **Non-Live AST Overall** | **40.12%** | 750 | Средний по всем non-live |

## Категории тестов

- **Simple** - модели дают одну функцию и просят её вызвать с правильными аргументами. Варианты для Python, Java, JavaScript
- **Multiple** - в промпте несколько функций, модель должна вызвать их по очереди в правильном порядке
- **Parallel** - модель должна вернуть несколько tool_calls в одном сообщении (параллельное выполнение)
- **Parallel Multiple** - комбинация parallel и multiple

## Как запустить

### Предварительные требования

- Python 3.11+
- vLLM сервер с GigaChat и включенным `--enable-auto-tool-choice --tool-call-parser gigachat3`
- Доступ к эндпоинту (по умолчанию `http://gpu02:8083/v1`)

### Установка BFCL

```bash
git clone https://github.com/ShishirPatil/gorilla.git
cd gorilla/berkeley-function-call-leaderboard
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
pip install soundfile  # необходимая зависимость qwen-agent
```

### Добавление GigaChat в конфиг

В файл `bfcl_eval/constants/model_config.py` добавить перед `MODEL_CONFIG_MAPPING`:

```python
from bfcl_eval.model_handler.api_inference.openai_completion import OpenAICompletionsHandler

gigachat_model_map = {
    "ai-sage/GigaChat3.1-10B-A1.8B-FC": ModelConfig(
        model_name="ai-sage/GigaChat3.1-10B-A1.8B",
        display_name="GigaChat3.1-10B-A1.8B (FC)",
        url="https://huggingface.co/ai-sage/GigaChat3.1-10B-A1.8B",
        org="AI-Sage",
        license="MIT",
        model_handler=OpenAICompletionsHandler,
        input_price=0,
        output_price=0,
        is_fc_model=True,
        underscore_to_dot=True,
    ),
}
```

И добавить `**gigachat_model_map` в `MODEL_CONFIG_MAPPING`.

### Настройка .env

Создать файл `.env` в корне проекта (или в `BFCL_PROJECT_ROOT`):

```bash
OPENAI_API_KEY=none
OPENAI_BASE_URL=http://gpu02:8083/v1
```

### Запуск генерации

```bash
export BFCL_PROJECT_ROOT=/path/to/results

# Все основные категории
bfcl generate \
  --model "ai-sage/GigaChat3.1-10B-A1.8B-FC" \
  --test-category simple_python,parallel,multiple,parallel_multiple,simple_java,simple_javascript \
  --num-threads 1

# Только простые Python-тесты (быстрый прогон ~8 мин)
bfcl generate \
  --model "ai-sage/GigaChat3.1-10B-A1.8B-FC" \
  --test-category simple_python \
  --num-threads 1
```

### Запуск оценки

```bash
bfcl evaluate \
  --model "ai-sage/GigaChat3.1-10B-A1.8B-FC" \
  --test-category simple_python,parallel,multiple,parallel_multiple,simple_java,simple_javascript
```

### Время выполнения

- simple_python (400 тестов) - ~8 мин
- Все 6 категорий (750 тестов) - ~10 мин
- Оценка - ~5 секунд

## Файлы в этой папке

- `data_overall.csv` - сводная таблица результатов
- `data_non_live.csv` - детализация по non-live категориям
- `BFCL_v4_*_result.json` - сырые ответы модели по каждой категории
- `BFCL_v4_*_score.json` - оценки по каждой категории

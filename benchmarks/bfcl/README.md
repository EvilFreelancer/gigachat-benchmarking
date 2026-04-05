# BFCL - Berkeley Function Calling Leaderboard

**Что тестируется:** способность модели корректно вызывать функции (tool calling) - правильно выбирать нужную функцию из набора и передавать аргументы нужных типов. Включает single-turn, multi-turn, агентные (memory + web search) категории.

**Репозиторий:** https://github.com/ShishirPatil/gorilla/tree/main/berkeley-function-call-leaderboard

## Результаты GigaChat3.1-10B-A1.8B

### Single-turn (v1/v2)

| Категория | Accuracy | Тестов | Описание |
|-----------|----------|--------|----------|
| Simple Python | **89.50%** | 400 | Один вызов, Python-функции |
| Multiple | **91.00%** | 100 | Несколько последовательных вызовов в ответе |
| Simple Java | 61.00% | 50 | Один вызов, Java-функции |
| Simple JavaScript | 58.00% | 50 | Один вызов, JS-функции |
| Parallel | 0.00% | 100 | Несколько одновременных вызовов |
| Parallel Multiple | 0.00% | 50 | Комбинация parallel + multiple |
| **Non-Live AST Overall** | **40.12%** | 750 | Средний по всем non-live |

### Multi-turn (v3)

| Категория | Accuracy | Тестов | Описание |
|-----------|----------|--------|----------|
| Base | **15.00%** | 200 | Базовые многоходовые диалоги с tool calls |
| Miss Param | **13.00%** | 200 | В описании функции отсутствует параметр |
| Miss Func | 8.50% | 200 | Отсутствует одна из доступных функций |
| Long Context | 6.00% | 200 | Длинный контекст описания функций |
| **Multi-turn Overall** | **10.62%** | 800 | Средний по всем multi-turn |

### Agentic (v4) - Memory + Web Search

| Категория | Accuracy | Тестов | Описание |
|-----------|----------|--------|----------|
| Memory KV | 0.00% | ~50 | Чтение/запись в key-value хранилище |
| Memory Vector | 0.00% | ~50 | Чтение/запись в векторную БД |
| Memory Rec Sum | 0.00% | ~55 | Recursive summarization memory |
| Web Search Base | 0.00% | ~50 | Поиск с DuckDuckGo через SerpApi |
| Web Search No Snippet | 0.00% | ~49 | Поиск без сниппетов, нужно открывать страницы |
| **Agentic Overall** | **0.00%** | ~254 | Средний по всем agentic |

## Описание категорий

### Single-turn
- **Simple** - модели дают одну функцию и просят её вызвать с правильными аргументами. Варианты для Python, Java, JavaScript
- **Multiple** - в промпте несколько функций, модель должна вызвать их по очереди в правильном порядке
- **Parallel** - модель должна вернуть несколько tool_calls в одном сообщении (параллельное выполнение)

### Multi-turn
Многоходовые диалоги с симуляцией API (file system, trading bot, ticket system и др.). Модель вызывает функцию, получает результат, и должна продолжить работу - вызвать следующую функцию или ответить пользователю.

- **Base** - стандартные многоходовые задачи
- **Miss Func** - одна из функций отсутствует в описании, модель должна справиться без неё
- **Miss Param** - у одной из функций пропущен обязательный параметр
- **Long Context** - описания функций очень длинные (~4K+ токенов)

### Agentic (Memory + Web Search)
Агентные сценарии, требующие работы с внешними системами:

- **Memory KV/Vector/Rec Sum** - модель должна сохранять и извлекать информацию из разных типов памяти (key-value, векторная БД, recursive summarization)
- **Web Search** - модель должна формулировать поисковые запросы и обрабатывать результаты поиска. Base - с сниппетами, No Snippet - нужно самостоятельно открывать страницы

## Анализ ошибок

### Multi-turn (10.62%)
Основные проблемы:
1. **Empty response** - после получения результата tool call модель часто отвечает пустым сообщением вместо продолжения работы
2. **Неправильные пути** - модель использует абсолютные пути вместо `cd` + относительных
3. **Не восстанавливается после ошибки** - получив ошибку (mkdir: directory exists), не пробует альтернативный подход

### Agentic (0%)
Модель не справляется с prerequisite-диалогами для memory (нужно "запомнить" информацию из 8-10 ходов), и не формирует корректные цепочки web search + fetch + parse.

## Как запустить

### Предварительные требования

- Python 3.11+
- vLLM сервер с GigaChat и включенным `--enable-auto-tool-choice --tool-call-parser gigachat3`
- Доступ к эндпоинту (по умолчанию `http://gpu02:8083/v1`)
- Для eval web_search - ключ SerpApi (`SERPAPI_API_KEY`)

### Установка BFCL

```bash
git clone https://github.com/ShishirPatil/gorilla.git
cd gorilla/berkeley-function-call-leaderboard
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
pip install soundfile  # необходимая зависимость qwen-agent
```

### Добавление GigaChat в конфиг

В файл `bfcl_eval/constants/model_config.py` после `MODEL_CONFIG_MAPPING` добавить:

```python
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

MODEL_CONFIG_MAPPING["ai-sage/GigaChat3.1-10B-A1.8B-FC"] = gigachat_model_map["ai-sage/GigaChat3.1-10B-A1.8B-FC"]
```

### Настройка .env

```bash
OPENAI_API_KEY=none
OPENAI_BASE_URL=http://gpu02:8083/v1
SERPAPI_API_KEY=     # опционально, нужен только для eval web_search
```

### Запуск

```bash
# Single-turn (v1/v2) - ~10 мин
bfcl generate \
  --model "ai-sage/GigaChat3.1-10B-A1.8B-FC" \
  --test-category simple_python,parallel,multiple,parallel_multiple,simple_java,simple_javascript \
  --num-threads 1

# Multi-turn (v3) - ~65 мин
bfcl generate \
  --model "ai-sage/GigaChat3.1-10B-A1.8B-FC" \
  --test-category multi_turn \
  --num-threads 1

# Agentic memory (v4) - ~60 мин
bfcl generate \
  --model "ai-sage/GigaChat3.1-10B-A1.8B-FC" \
  --test-category memory \
  --num-threads 1

# Agentic web_search (v4) - ~15 мин
bfcl generate \
  --model "ai-sage/GigaChat3.1-10B-A1.8B-FC" \
  --test-category web_search \
  --num-threads 1

# Оценка
bfcl evaluate \
  --model "ai-sage/GigaChat3.1-10B-A1.8B-FC" \
  --test-category multi_turn

bfcl evaluate \
  --model "ai-sage/GigaChat3.1-10B-A1.8B-FC" \
  --test-category memory,web_search
```

### Время выполнения

| Категория | Генерация | Оценка |
|-----------|-----------|--------|
| Single-turn (750 тестов) | ~10 мин | ~5 сек |
| Multi-turn (800 тестов) | ~65 мин | ~2 сек |
| Memory (576 тестов с prereq) | ~60 мин | ~1 сек |
| Web search (200 тестов) | ~15 мин | ~1 сек |

## Файлы в этой папке

```
bfcl/
  README.md                      # Этот файл
  REPORT.md                      # Подробный отчет (первый прогон)
  data_overall.csv               # Сводная таблица (v1/v2)
  data_overall_v2.csv            # Сводная таблица (все категории)
  data_non_live.csv              # Non-live категории
  BFCL_v4_*_result.json          # Single-turn сырые ответы
  BFCL_v4_*_score.json           # Single-turn оценки
  v3_multi_turn/
    data_multi_turn.csv          # Сводка multi-turn
    results/                     # Сырые ответы модели
    scores/                      # Оценки по подкатегориям
  v4_agentic/
    data_agentic.csv             # Сводка agentic
    results/                     # Сырые ответы модели
    scores/                      # Оценки по подкатегориям
```

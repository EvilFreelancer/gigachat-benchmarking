# tau2-bench - Agent Benchmark

**Что тестируется:** способность модели вести многоходовый диалог с пользователем, используя tool calls для выполнения реальных задач (бронирование, отмена, поиск рейсов и т.д.). Оценивается конечный результат - изменилось ли состояние системы так, как ожидал пользователь.

**Репозиторий:** https://github.com/sierra-research/tau2-bench

## Результаты GigaChat3.1-10B-A1.8B

### Домен airline (50 задач)

| Метрика | Значение |
|---------|----------|
| **Average Reward** | **0.00** |
| **Pass^1** | **0.000** |
| Всего симуляций | 50 |
| Завершено | 40 |
| Infra errors (сетевые ошибки API) | 10 |
| Max steps (зацикливание) | 38 |
| Error (галлюцинация несуществующих инструментов) | 2 |
| Normal stop (задача решена) | 0 |

### Поведение модели

Модель активно вызывает инструменты, но не может довести задачу до конца:

- Многократно вызывает одни и те же функции (`get_reservation_details` по 6-8 раз)
- Не формулирует финальный ответ пользователю с подтверждением действия
- Галлюцинирует инструменты, которых нет в окружении (`calculate_baggage_allowance`, `human_agent_transfer`)
- Упирается в лимит шагов (30) на всех задачах

## Домены в tau2-bench

- **airline** - обслуживание клиентов авиакомпании (бронирование, отмена, изменение рейсов)
- **retail** - онлайн-магазин (возвраты, обмены, трекинг)
- **telecom** - телеком-оператор
- **banking_knowledge** - банковское обслуживание

## Как запустить

### Предварительные требования

- Python 3.11+, `uv` (менеджер пакетов)
- vLLM сервер с GigaChat и включенным tool calling
- Внешний LLM для user simulator (нужна модель, которая будет изображать пользователя)

### Установка

```bash
git clone https://github.com/sierra-research/tau2-bench.git
cd tau2-bench
uv sync
```

### Настройка user simulator

tau2-bench требует два LLM - agent (тестируемая модель) и user simulator (изображает пользователя).

Для user simulator нужен OpenAI-совместимый API. В нашем случае использовался `gpt-oss:120b` через `api.rpa.icu`:

```bash
# .env файл в корне tau2-bench
OPENAI_API_KEY=your-api-key
```

### Запуск

```bash
# Быстрый тест (5 задач, домен airline)
uv run tau2 run \
  --domain airline \
  --agent-llm 'hosted_vllm/ai-sage/GigaChat3.1-10B-A1.8B' \
  --agent-llm-args '{"api_key": "none", "api_base": "http://localhost:8083/v1"}' \
  --user-llm 'hosted_vllm/gpt-oss:120b' \
  --user-llm-args '{"api_key": "YOUR_KEY", "api_base": "https://api.rpa.icu/v1"}' \
  --num-trials 1 \
  --num-tasks 5 \
  --max-steps 30 \
  --max-concurrency 1

# Полный прогон (все 50 задач airline)
uv run tau2 run \
  --domain airline \
  --agent-llm 'hosted_vllm/ai-sage/GigaChat3.1-10B-A1.8B' \
  --agent-llm-args '{"api_key": "none", "api_base": "http://localhost:8083/v1"}' \
  --user-llm 'hosted_vllm/gpt-oss:120b' \
  --user-llm-args '{"api_key": "YOUR_KEY", "api_base": "https://api.rpa.icu/v1"}' \
  --num-trials 1 \
  --max-steps 30 \
  --max-concurrency 1 \
  --max-retries 6 \
  --log-level WARNING
```

### Важные нюансы

1. **Провайдер `hosted_vllm/`** - использовать для обеих моделей, чтобы LiteLLM не пытался обращаться к настоящему OpenAI API

2. **Ошибка "Country, region, or territory not supported"** - возникает если использовать провайдер `openai/` вместо `hosted_vllm/`. LiteLLM пытается проверить модель через OpenAI API, который блокирует запросы из РФ

3. **nohup для длинных прогонов** - SSH сессия может оборваться, запускайте через nohup:

```bash
nohup uv run tau2 run ... > airline_run.log 2>&1 &
```

4. **Infra errors** - часть задач падает из-за нестабильности API user simulator. `--max-retries 6` помогает, но не решает полностью

### Просмотр результатов

```bash
# Интерактивный просмотр
uv run tau2 view

# Результаты сохраняются в
# data/simulations/<timestamp>_<domain>_<agent>_<user>/results.json
```

### Время выполнения

- 5 задач - ~3 мин
- 50 задач (полный airline) - ~30 мин

## Файлы в этой папке

- `results_airline.json` - полные результаты прогона (50 задач airline), включая все сообщения, tool calls, rewards

# Отчет: BFCL + tau2-bench - GigaChat 3.1 10B A1.8B

**Дата:** 4 апреля 2026
**Модель:** `ai-sage/GigaChat3.1-10B-A1.8B` (10B total / 1.8B active, MoE)
**Эндпоинт:** `http://gpu02:8083/v1` (vLLM v0.19.0, `--tool-call-parser gigachat3`, fp8 KV-cache)

---

## BFCL (Berkeley Function Calling Leaderboard)

### Итоговые результаты

| Категория | Accuracy | Кол-во тестов |
|-----------|----------|---------------|
| **Simple Python** | **89.50%** | 400 |
| **Multiple** (несколько вызовов в одном ответе) | **91.00%** | 100 |
| Simple Java | 61.00% | 50 |
| Simple JavaScript | 58.00% | 50 |
| Parallel (одновременные вызовы) | 0.00% | 100 |
| Parallel Multiple | 0.00% | 50 |
| **Non-Live AST Overall** | **40.12%** | 750 |
| **Simple AST Overall** | **69.50%** | 500 |

### Ключевые наблюдения

1. **Сильные стороны:**
   - Отличная точность на одиночных Python-вызовах (89.5%) - на уровне крупных моделей
   - Лучший результат на Multiple (91%) - модель корректно генерирует несколько последовательных tool calls
   - Средняя латентность 0.93с/вызов - быстрая генерация

2. **Слабые стороны:**
   - Parallel tool calls - 0%. Модель не поддерживает формат параллельных вызовов (несколько tool_calls в одном сообщении одновременно)
   - Java/JavaScript - 58-61%, что ниже Python из-за менее стабильной генерации аргументов в этих языках

### Методология

- **Фреймворк:** [BFCL v4](https://github.com/ShishirPatil/gorilla)
- **Handler:** `OpenAICompletionsHandler` (OpenAI-совместимый API через vLLM)
- **Режим:** FC (function calling) - нативные tool_calls через API
- **Параметры:** temperature=0.001, num-threads=1

---

## tau2-bench (Sierra Research)

### Итоговые результаты (домен airline, 50 задач)

| Метрика | Значение |
|---------|----------|
| **Average Reward** | **0.00** |
| **Pass^1** | **0.000** |
| Всего симуляций | 50 |
| Успешно выполнено | 40 |
| Infra errors | 10 |
| Max steps termination | 38 |
| Error termination | 2 |
| Normal stop | 0 |

### Анализ поведения модели

Модель активно использует tool calls в диалоге:

| Задача | Вызовы инструментов | Причина завершения |
|--------|---------------------|-------------------|
| Task 1 | `get_user_details`, `get_reservation_details` x6, `list_all_airports` | max_steps |
| Task 2 | `search_direct_flight` x3, `search_onestop_flight` x7, `get_user_details` | max_steps |
| Task 4 | `get_user_details` x2, `get_reservation_details` x8, `transfer_to_human_agents` | max_steps |

**Типичные проблемы:**
- Модель зацикливается на вызовах одних и тех же инструментов (многократные вызовы `get_reservation_details`)
- Не может завершить задачу за 30 шагов - не хватает стратегического планирования
- Иногда галлюцинирует инструменты (`calculate_baggage_allowance`, `human_agent_transfer`), которых нет в окружении

### Методология

- **Фреймворк:** [tau2-bench](https://github.com/sierra-research/tau2-bench) (v0.1.x)
- **Домен:** airline (50 задач по обслуживанию клиентов авиакомпании)
- **Agent LLM:** `hosted_vllm/ai-sage/GigaChat3.1-10B-A1.8B` (localhost:8083)
- **User Simulator:** `gpt-oss:120b` через `api.rpa.icu` (OpenAI-совместимый API)
- **Max steps:** 30, trials: 1, max retries: 6

---

## Сравнение с другими моделями

### BFCL Simple Python AST (ориентировочное сравнение)

| Модель | Параметры (active) | Simple Python |
|--------|-------------------|---------------|
| GPT-4o | - | ~90-95% |
| Claude 3.5 Sonnet | - | ~90% |
| Qwen2.5 72B | 72B | ~85% |
| **GigaChat3.1-10B** | **1.8B** | **89.5%** |
| Llama 3.1 8B | 8B | ~60-70% |
| Mistral 7B | 7B | ~50-60% |

**Вывод:** Для модели с 1.8B активных параметров результат 89.5% на simple Python FC - это выдающийся показатель, сравнимый с GPT-4o и Claude 3.5.

### tau2-bench (ориентировочное сравнение)

| Модель | tau2 airline Pass^1 |
|--------|---------------------|
| GPT-4o | ~50-60% |
| Claude 3.5 Sonnet | ~40-50% |
| GPT-4o-mini | ~20-30% |
| **GigaChat3.1-10B** | **0%** |

**Вывод:** tau2-bench требует длительного стратегического планирования и сложных диалогов. Маленькие модели предсказуемо не справляются.

---

## Общие выводы

### Что работает хорошо

1. **Одиночные tool calls** - модель отлично парсит описания функций и генерирует правильные аргументы (89-91%)
2. **Формат вызовов** - нативная поддержка через vLLM `gigachat3` parser работает корректно
3. **Скорость** - средняя латентность <1с делает модель практичной для реальных приложений
4. **Multiple calls** - модель может генерировать несколько последовательных вызовов

### Что требует улучшения

1. **Parallel tool calls** - не поддерживаются (0% на BFCL parallel)
2. **Агентные сценарии** - модель не справляется с длинными цепочками рассуждений (tau2 = 0%)
3. **Java/JavaScript** - точность ниже Python (58-61% vs 89.5%)
4. **Галлюцинации инструментов** - модель иногда вызывает несуществующие функции

### Рекомендации

1. **Для продакшена** - модель подходит для простых tool-calling сценариев (1-3 инструмента, Python API)
2. **Для агентных задач** - нужна модель большего размера или специализированный fine-tuning
3. **Parallel calls** - потенциально решается через обучение на примерах параллельных вызовов

---

## Артефакты

### BFCL
- Результаты генерации: `/tmp/bfcl-results/result/`
- Оценки: `/tmp/bfcl-results/score/data_overall.csv`
- Детализация: `/tmp/bfcl-results/score/data_non_live.csv`

### tau2-bench
- Лог прогона: `gpu02:/home/pasha/tests/tau2-bench/airline_run.log`
- Результаты симуляций: `gpu02:/home/pasha/tests/tau2-bench/data/simulations/`

### Конфигурация vLLM
```yaml
serve ai-sage/GigaChat3.1-10B-A1.8B
  --served-model-name ai-sage/GigaChat3.1-10B-A1.8B
  --trust-remote-code --dtype auto
  --gpu-memory-utilization 0.95 --max-num-seqs 1
  --max-model-len 60000 --max-num-batched-tokens 60000
  --kv-cache-dtype fp8 --no-enable-prefix-caching
  --enable-auto-tool-choice --tool-call-parser gigachat3
```

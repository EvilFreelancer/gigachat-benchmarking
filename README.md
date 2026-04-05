# GigaChat 3.1 10B A1.8B - Benchmark Suite

**Модель:** [`ai-sage/GigaChat3.1-10B-A1.8B`](https://huggingface.co/ai-sage/GigaChat3.1-10B-A1.8B) (10B total / 1.8B active, MoE)
**Дата:** апрель 2026
**Инференс:** vLLM v0.19.0, `--tool-call-parser gigachat3`, fp8 KV-cache

---

## Сводка результатов

| Бенчмарк | Что тестирует | Лучший результат | Папка |
|----------|---------------|------------------|-------|
| **BFCL Single-turn** | Tool calling (вызов функций) | Simple Python **89.5%**, Multiple **91.0%** | [`benchmarks/bfcl/`](benchmarks/bfcl/) |
| **BFCL Multi-turn** | Многоходовые tool calls | Base **15.0%**, Overall **10.6%** | [`benchmarks/bfcl/`](benchmarks/bfcl/) |
| **BFCL Agentic** | Memory + Web Search | Overall **0.0%** | [`benchmarks/bfcl/`](benchmarks/bfcl/) |
| **tau2-bench** | Агентные диалоги | Pass^1 **0.0%** (airline, 50 задач) | [`benchmarks/tau2-bench/`](benchmarks/tau2-bench/) |
| **SWE-bench Lite** | Решение GitHub issues | Score **0%**, best patch rate **8%** | [`benchmarks/swe-bench/`](benchmarks/swe-bench/) |

---

## BFCL - Berkeley Function Calling Leaderboard

Полный прогон всех категорий BFCL v4.

### Single-turn (v1/v2)

| Категория | Accuracy | Описание |
|-----------|----------|----------|
| Simple Python | **89.50%** | Один вызов, Python-функции |
| Multiple | **91.00%** | Несколько последовательных вызовов |
| Simple Java | 61.00% | Один вызов, Java-функции |
| Simple JavaScript | 58.00% | Один вызов, JS-функции |
| Parallel | 0.00% | Параллельные вызовы (не поддерживается) |

### Multi-turn (v3)

| Категория | Accuracy | Описание |
|-----------|----------|----------|
| Base | **15.00%** | Базовые многоходовые задачи (file system, API) |
| Miss Param | **13.00%** | Пропущен обязательный параметр функции |
| Miss Func | 8.50% | Отсутствует одна из функций |
| Long Context | 6.00% | Длинный контекст описания функций |
| **Overall** | **10.62%** | |

### Agentic (v4) - Memory + Web Search

| Категория | Accuracy | Описание |
|-----------|----------|----------|
| Memory KV / Vector / Rec Sum | 0.00% | Key-value, вектор, recursive summary |
| Web Search Base / No Snippet | 0.00% | Поиск DuckDuckGo, без сниппетов |
| **Overall** | **0.00%** | |

Подробности: [`benchmarks/bfcl/README.md`](benchmarks/bfcl/README.md)

### Сравнение с BFCL V4 Leaderboard

Данные с [официального лидерборда BFCL V4](https://gorilla.cs.berkeley.edu/leaderboard.html) (108 моделей, обновление 2025-12-16).
Qwen3.5-4B - из [model card на HuggingFace](https://huggingface.co/Qwen/Qwen3.5-4B) (BFCL-V4 overall, на лидерборде отсутствует).

#### Multi-Turn (v3)

| Модель | Params (active) | Overall | Base | Miss Func | Miss Param | Long Ctx |
|--------|-----------------|---------|------|-----------|------------|----------|
| Claude Opus 4.5 (FC) | - | **68.38%** | 81.00% | 64.00% | 58.00% | 70.50% |
| xLAM-2-32b (FC) | 32B | **69.50%** | 81.50% | 72.50% | 67.50% | 56.50% |
| Qwen3-235B-A22B (Prompt) | 22B | **44.62%** | 54.00% | 42.50% | 31.50% | 50.50% |
| Qwen3-8B (FC) | 8B | **41.75%** | 50.50% | 42.00% | 40.00% | 34.50% |
| Qwen3-4B (FC) | 4B | **22.12%** | 26.50% | 21.00% | 15.50% | 25.50% |
| Qwen3-4B (Prompt) | 4B | **20.50%** | 24.50% | 21.50% | 16.00% | 20.00% |
| Qwen3-1.7B (FC) | 1.7B | **11.00%** | 15.00% | 6.00% | 12.00% | 11.00% |
| **GigaChat3.1-10B (FC)** | **1.8B** | **10.62%** | 15.00% | 8.50% | 13.00% | 6.00% |
| Qwen3-0.6B (FC) | 0.6B | **3.62%** | 5.50% | 2.00% | 3.00% | 4.00% |

GigaChat (1.8B active) на уровне Qwen3-1.7B (11.00% vs 10.62%). Обе модели значительно уступают Qwen3-4B (22.12%).

#### Agentic - Web Search (v4)

| Модель | Params (active) | Overall | Base | No Snippet |
|--------|-----------------|---------|------|------------|
| Claude Opus 4.5 (FC) | - | **84.50%** | 84.00% | 85.00% |
| GPT-5-mini (FC) | - | **82.00%** | 87.00% | 77.00% |
| Qwen3-235B-A22B (Prompt) | 22B | **50.50%** | 56.00% | 45.00% |
| Qwen3-8B (FC) | 8B | **12.00%** | 15.00% | 9.00% |
| Qwen3-4B (Prompt) | 4B | **4.50%** | 4.00% | 5.00% |
| Qwen3-4B (FC) | 4B | **3.00%** | 4.00% | 2.00% |
| Qwen3-1.7B (FC) | 1.7B | **2.50%** | 3.00% | 2.00% |
| Qwen3-0.6B (FC) | 0.6B | **1.00%** | 1.00% | 1.00% |
| **GigaChat3.1-10B (FC)** | **1.8B** | **0.00%** | 0.00% | 0.00% |

Web search - практически нерешаемая задача для маленьких моделей. Даже Qwen3-4B набирает только 3-4.5%.

#### Agentic - Memory (v4)

| Модель | Params (active) | Overall | KV | Vector | Rec Sum |
|--------|-----------------|---------|-----|--------|---------|
| Claude Opus 4.5 (FC) | - | **73.76%** | 70.97% | 72.90% | 77.42% |
| DeepSeek-V3.2 (FC) | 37B | **54.19%** | 41.94% | 61.29% | 59.35% |
| Qwen3-4B (Prompt) | 4B | **23.87%** | 12.90% | 14.19% | 44.52% |
| Qwen3-4B (FC) | 4B | **17.63%** | 16.13% | 12.26% | 24.52% |
| Qwen3-8B (FC) | 8B | **14.62%** | 5.16% | 7.10% | 31.61% |
| Qwen3-1.7B (FC) | 1.7B | **6.02%** | 4.52% | 7.74% | 5.81% |
| **GigaChat3.1-10B (FC)** | **1.8B** | **0.00%** | 0.00% | 0.00% | 0.00% |

#### Non-Live AST (Simple + Multiple + Parallel)

| Модель | Params (active) | Overall | Simple | Multiple | Parallel | Par.Mult. |
|--------|-----------------|---------|--------|----------|----------|-----------|
| Qwen3-4B (FC) | 4B | **87.88%** | 75.50% | 93.50% | 92.50% | 90.00% |
| Qwen3-8B (FC) | 8B | **87.58%** | 72.83% | 96.50% | 92.00% | 89.00% |
| Qwen3-1.7B (FC) | 1.7B | **82.92%** | 70.67% | 92.50% | 88.50% | 80.00% |
| **GigaChat3.1-10B (FC)** | **1.8B** | **40.12%*** | **89.50%** | **91.00%** | 0.00% | 0.00% |

*GigaChat показывает лучшие Simple Python (89.50%) и Multiple (91.00%) среди всех моделей класса 4B-, но получает 0% на Parallel, что обрушивает средний балл.

#### BFCL V4 Overall (взвешенный скор)

Формула: Agentic 40% + Multi-Turn 30% + Live 10% + Non-Live 10% + Hallucination 10%.

| # | Модель | Params (active) | Overall |
|---|--------|-----------------|---------|
| 1 | Claude Opus 4.5 (FC) | - | **77.47%** |
| 4 | GLM-4.6 (FC thinking) | - | **72.38%** |
| 16 | GPT-5.2 (FC) | - | **55.87%** |
| 23 | Qwen3-235B-A22B (Prompt) | 22B | **52.15%** |
| - | Qwen3.5-4B | 4B | **50.30%** |
| 39 | Qwen3-8B (FC) | 8B | **42.57%** |
| 54 | Qwen3-4B (FC) | 4B | **35.68%** |
| 71 | Qwen3-1.7B (FC) | 1.7B | **28.41%** |
| 92 | Qwen3-0.6B (FC) | 0.6B | **23.93%** |

GigaChat не прогонялся через Live + Hallucination, поэтому V4 Overall скор нельзя рассчитать напрямую. Ориентировочно по замеренным категориям GigaChat попадает между Qwen3-0.6B и Qwen3-1.7B.

Источники:
- [BFCL V4 Leaderboard](https://gorilla.cs.berkeley.edu/leaderboard.html) (108 моделей, 2025-12-16)
- [Qwen3.5-4B Model Card](https://huggingface.co/Qwen/Qwen3.5-4B) (BFCL-V4 = 50.3, TAU2-Bench = 79.9)
- [Qwen3 Technical Report](https://arxiv.org/abs/2505.09388) (BFCL v3 Multi-Turn только)

---

## tau2-bench - Agent Benchmark

Тестирует многоходовые агентные диалоги: модель выступает агентом поддержки авиакомпании, общается с пользователем и вызывает инструменты для решения задачи.

- **Average Reward: 0.00** из 40 оцененных задач
- Модель вызывает инструменты (10-12 tool calls на задачу), но зацикливается
- Типичная проблема - многократный вызов `get_reservation_details` без продвижения к решению
- Все задачи завершились по лимиту шагов (max_steps=30)

Для сравнения, Qwen3.5-4B набирает **79.9** на TAU2-Bench ([model card](https://huggingface.co/Qwen/Qwen3.5-4B)).

Подробности: [`benchmarks/tau2-bench/README.md`](benchmarks/tau2-bench/README.md)

---

## SWE-bench Lite - Software Engineering

Тестирует решение реальных задач из GitHub issues - 300 инстансов из Django, scikit-learn, matplotlib и др.

- **Score: 0%** при single-pass prompting (5 подходов)
- Лучший patch apply rate: **8%** (few-shot)
- Агентный подход (Run 5, пилот): **30%** инстансов с правильными редакциями
- Основная проблема: модель не генерирует валидный unified diff формат

Подробности: [`benchmarks/swe-bench/README.md`](benchmarks/swe-bench/README.md)

---

## Общие выводы

### Сильные стороны

1. **Одиночные tool calls** - Simple Python 89.5%, Multiple 91.0% - лучший результат среди моделей класса <=4B на BFCL. Qwen3-4B набирает 75.5% Simple, 93.5% Multiple
2. **Скорость** - средняя латентность <1с на вызов
3. **Нативный tool calling** - vLLM `gigachat3` parser работает корректно

### Слабые стороны

1. **Parallel tool calls** - 0% (Qwen3-4B: 92.5%, Qwen3-1.7B: 88.5%). Отсутствие parallel вызовов обрушивает Non-Live AST average до 40% против 88% у Qwen3-4B
2. **Multi-turn** - 10.62%, на уровне Qwen3-1.7B (11.0%), но в 2 раза ниже Qwen3-4B (22.1%)
3. **Agentic** - memory 0%, web search 0%. Даже Qwen3-1.7B набирает 6% memory и 2.5% web search
4. **TAU2-Bench** - 0.0 reward (Qwen3.5-4B: 79.9)
5. **SWE-bench** - 0% resolve rate

### Рекомендации

- **Для продакшена** - подходит для простых single-turn tool-calling сценариев (1-3 инструмента, Python API)
- **Для агентных задач** - требуется модель большего размера или fine-tuning на multi-turn/agentic данных
- **Parallel calls** - критический gap, потенциально решается дообучением
- **Multi-turn recovery** - модель часто дает пустой ответ после ошибки вместо альтернативного подхода

---

## Конфигурация vLLM

```yaml
serve ai-sage/GigaChat3.1-10B-A1.8B
  --served-model-name ai-sage/GigaChat3.1-10B-A1.8B
  --trust-remote-code --dtype auto
  --gpu-memory-utilization 0.95 --max-num-seqs 1
  --max-model-len 60000 --max-num-batched-tokens 60000
  --kv-cache-dtype fp8 --no-enable-prefix-caching
  --enable-auto-tool-choice --tool-call-parser gigachat3
```

## Структура репозитория

```
gigachat-bench/
  README.md                          # Этот файл - обзор всех бенчмарков
  requirements.txt                   # Зависимости для SWE-bench
  scripts/                           # Скрипты инференса SWE-bench
    run_gigachat_inference.py         # Single-pass инференс
    run_gigachat_agent.py             # Агентный инференс с tool calling
    run_evaluation.sh                 # Оценка через swebench harness
  predictions/                       # Сгенерированные патчи SWE-bench
  results/                           # Результаты оценки SWE-bench
  patches/                           # Кастомный chat template
  benchmarks/
    bfcl/                            # BFCL - все категории
      README.md                      # Как запустить, описание категорий
      data_overall.csv               # Сводная таблица (v1/v2)
      data_overall_v2.csv            # Сводная таблица (все категории)
      BFCL_v4_*_result.json          # Single-turn сырые ответы
      BFCL_v4_*_score.json           # Single-turn оценки
      v3_multi_turn/                 # Multi-turn (v3) результаты
        data_multi_turn.csv          # Сводка
        results/                     # Сырые ответы
        scores/                      # Оценки
      v4_agentic/                    # Agentic (v4) результаты
        data_agentic.csv             # Сводка
        results/                     # Сырые ответы (memory + web_search)
        scores/                      # Оценки
    tau2-bench/                      # tau2-bench
      README.md                      # Как запустить
      results_airline.json           # Полные результаты (50 задач)
    swe-bench/                       # SWE-bench
      README.md                      # Как запустить
      REPORT.md                      # Подробный отчет (EN)
      REPORT_RU.md                   # Подробный отчет (RU)
```

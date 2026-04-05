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

Для модели с 1.8B активных параметров - 89.5% на Python FC сопоставимо с GPT-4o (~90-95%). Multi-turn 10.6% - ожидаемый результат для маленькой модели.

Подробности: [`benchmarks/bfcl/README.md`](benchmarks/bfcl/README.md)

---

## tau2-bench - Agent Benchmark

Тестирует многоходовые агентные диалоги: модель выступает агентом поддержки авиакомпании, общается с пользователем и вызывает инструменты для решения задачи.

- **Average Reward: 0.00** из 40 оцененных задач
- Модель вызывает инструменты (10-12 tool calls на задачу), но зацикливается
- Типичная проблема - многократный вызов `get_reservation_details` без продвижения к решению
- Все задачи завершились по лимиту шагов (max_steps=30)

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

1. **Одиночные tool calls** - отличная точность 89-91%, на уровне топовых моделей
2. **Скорость** - средняя латентность <1с на вызов
3. **Нативный tool calling** - vLLM `gigachat3` parser работает корректно
4. **Multiple calls** - модель генерирует несколько последовательных вызовов

### Слабые стороны

1. **Parallel tool calls** - не поддерживаются (0%)
2. **Multi-turn recovery** - после ошибки модель часто дает пустой ответ вместо альтернативного подхода
3. **Агентные сценарии** - memory и web search требуют длинных цепочек рассуждений, 0%
4. **Генерация diff** - не может стабильно генерировать unified diff формат
5. **Галлюцинации инструментов** - иногда вызывает несуществующие функции

### Рекомендации

- **Для продакшена** - подходит для простых tool-calling сценариев (1-3 инструмента, Python API)
- **Для агентных задач** - требуется модель большего размера или fine-tuning
- **Parallel calls** - потенциально решается через дообучение

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

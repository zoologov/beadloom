# Beadloom

> Read this in other languages: [English](README.md)

**Архитектура вашего проекта не должна жить в голове одного человека.**

[![License: MIT](https://img.shields.io/github/license/zoologov/beadloom)](LICENSE)
[![GitHub release](https://img.shields.io/github/v/release/zoologov/beadloom?include_prereleases&sort=semver)](https://github.com/zoologov/beadloom/releases)
[![PyPI](https://img.shields.io/pypi/v/beadloom)](https://pypi.org/project/beadloom/)
[![Python](https://img.shields.io/pypi/pyversions/beadloom)](https://pypi.org/project/beadloom/)
[![Tests](https://img.shields.io/github/actions/workflow/status/zoologov/beadloom/tests.yml?label=Tests)](https://github.com/zoologov/beadloom/actions)
[![mypy: strict](https://img.shields.io/badge/mypy-strict-blue)](https://mypy-lang.org/)
[![code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![coverage: 80%+](https://img.shields.io/badge/coverage-80%25%2B-green)](pyproject.toml)

---

Beadloom — инструмент управления знаниями о кодовой базе. Он превращает разрозненные архитектурные знания в явный, запрашиваемый граф, который живёт в вашем Git-репозитории и доступен людям и AI-агентам.

> IDE ищет код. Beadloom объясняет, что этот код значит в контексте всей системы.

**Платформы:** macOS, Linux, Windows &nbsp;|&nbsp; **Python:** 3.10+

## Зачем Beadloom?

В больших кодовых базах есть проблема знаний, которую поиск по коду не решает:

- **«Только два человека понимают, как устроена система.»** Архитектурные знания живут в головах, а не в репозитории. Когда эти люди уходят, знания уходят вместе с ними.
- **«Документация врёт.»** Доки устаревают за недели. Никто не замечает, пока агент или новый разработчик не начнёт работать на основе устаревших спецификаций.
- **«AI-агенты каждую сессию начинают с нуля.»** Каждый запуск агента — это заново grep, чтение README, угадывание, какие файлы важны. Большая часть контекстного окна сгорает на ориентировку, а не на работу.

Beadloom решает это тремя механизмами:

1. **Context Oracle** — архитектурный граф (YAML в Git), который описывает домены, фичи, сервисы и их связи. Запросите любой узел и получите детерминированный, компактный пакет контекста за <20мс. Один запрос — один результат — каждый раз.

2. **Doc Sync Engine** — отслеживает, какие документы соответствуют какому коду. Обнаруживает устаревшую документацию при каждом коммите. Больше никакого «в спеке написано X, а в коде Y».

3. **Architecture as Code** — архитектурные правила в YAML, валидация через `beadloom lint`, блокировка нарушений в CI. Агенты получают не только контекст, но и ограничения — и соблюдают границы архитектуры конструктивно, а не случайно.

### Детерминированный контекст, а не вероятностное угадывание

Индексаторы IDE используют семантический поиск — LLM сама решает, что релевантно. Это работает для «найди похожий код», но не для «объясни эту фичу в контексте всей системы».

Beadloom использует **детерминированный обход графа**: команда определяет архитектурный граф, а BFS каждый раз выдаёт один и тот же пакет контекста. Граф — это YAML в Git: ревьюируется в PR, аудируется, версионируется.

|  | Семантический поиск (IDE) | Beadloom |
|---|---|---|
| **Отвечает на** | «Где этот класс?» | «Что это за фича и как она вписывается в систему?» |
| **Метод** | Эмбеддинги + LLM-ранжирование | Явный граф + BFS-обход |
| **Результат** | Вероятностный список файлов | Детерминированный пакет контекста |
| **Документация** | Не отслеживает актуальность | Ловит устаревшие доки при каждом коммите |
| **Архитектура** | Не валидирует | Проверяет границы импортов, блокирует нарушения |
| **Знания** | Умирают с сессией | Живут в Git, переживают смену команды |

Beadloom не заменяет IDE. Он даёт вашей IDE — и вашим агентам — архитектурный контекст, который невозможно вывести из одного только кода.

## Установка

```bash
uv tool install beadloom        # рекомендуется
pipx install beadloom            # альтернатива
```

## Быстрый старт

```bash
# 1. Сканируем кодовую базу и генерируем архитектурный граф
beadloom init --bootstrap

# 2. Просматриваем сгенерированный граф (редактируем домены, переименовываем узлы, добавляем связи)
vi .beadloom/_graph/services.yml

# 3. Строим индекс и начинаем использовать
beadloom reindex
beadloom ctx AUTH-001              # получить контекст по фиче
beadloom sync-check                # проверить актуальность документации
beadloom lint                      # проверить архитектурные правила
```

Документация не нужна для старта — Beadloom строит граф из структуры кода.

### Подключение AI-агентов через MCP

```bash
beadloom setup-mcp                 # создаёт .mcp.json автоматически
```

Агенты вызывают `get_context("AUTH-001")` и получают готовый пакет контекста с ограничениями — ноль токенов на поиск:

```json
{
  "mcpServers": {
    "beadloom": {
      "command": "beadloom",
      "args": ["mcp-serve"]
    }
  }
}
```

Работает с Claude Code, Cursor и любым MCP-совместимым инструментом.

## Для кого?

**Tech Lead / Архитектор** — Вы хотите, чтобы архитектурные знания были явными, версионируемыми и пережили ротацию команды. Beadloom делает неявное явным: домены, фичи, сервисы, зависимости — всё в YAML, всё в Git. А `beadloom lint` гарантирует, что границы соблюдаются.

**Platform / DevEx-инженер** — Вы строите инструментарий для команды. Beadloom даёт вашим агентам структурированный контекст из коробки (через MCP), вашему CI — проверку актуальности документации и архитектурных границ.

**Разработчик** — Вы устали тратить первый час каждой задачи на выяснение «как устроена эта часть системы?». `beadloom ctx FEATURE-ID` даёт ответ за секунды. `beadloom why NODE` покажет, что зависит от этого узла и что сломается при изменении.

## Ключевые возможности

- **Context Oracle** — детерминированный обход графа, компактный JSON-пакет за <20мс
- **Doc Sync Engine** — отслеживает связи код↔документация, обнаруживает устаревшие доки, интегрируется с git-хуками
- **Architecture as Code** — правила границ в YAML, валидация через `beadloom lint`, контроль в CI
- **Полнотекстовый поиск** — FTS5-поиск по узлам, документам и символам кода
- **Анализ влияния** — `beadloom why` показывает, что зависит от узла и что сломается при изменении
- **Code-first онбординг** — архитектурный граф строится из структуры кода; документация не нужна для старта
- **MCP-сервер** — 10 инструментов для AI-агентов, включая запись и поиск
- **Интерактивный TUI** — `beadloom ui` — терминальный дашборд для навигации по графу
- **Local-first** — один CLI + один файл SQLite, без Docker, без облачных зависимостей

## Как это работает

Beadloom поддерживает **архитектурный граф**, определённый в YAML-файлах в `.beadloom/_graph/`. Граф состоит из **узлов** (фичи, сервисы, домены, сущности, ADR) и **рёбер** (part_of, uses, depends_on и др.).

Конвейер индексации объединяет три источника в единую базу SQLite:

1. **Graph YAML** — узлы и рёбра, описывающие архитектуру проекта
2. **Документация** — Markdown-файлы, привязанные к узлам графа, разбитые на поисковые чанки
3. **Код** — исходники, разобранные tree-sitter для извлечения символов и аннотаций `# beadloom:feature=AUTH-001`

При запросе контекста по узлу Context Oracle выполняет обход в ширину (BFS), собирает релевантный подграф, документацию и символы кода и возвращает компактный пакет.

Doc Sync Engine отслеживает, какие файлы документации соответствуют каким файлам кода. При каждом коммите (через git-хук) он обнаруживает устаревшие доки и предупреждает или блокирует коммит.

## Architecture as Code

Beadloom не просто описывает архитектуру — он её защищает. Определяйте правила границ в YAML, валидируйте через `beadloom lint`, блокируйте нарушения в CI.

**Правила** (`.beadloom/_graph/rules.yml`) — реальные правила из этого проекта:

```yaml
rules:
  - name: domain-needs-parent
    description: "Every domain must be part_of the beadloom service"
    require:
      for: { kind: domain }
      has_edge_to: { ref_id: beadloom }
      edge_kind: part_of

  - name: feature-needs-domain
    description: "Every feature must be part_of a domain"
    require:
      for: { kind: feature }
      has_edge_to: { kind: domain }
      edge_kind: part_of
```

**Валидация:**

```bash
beadloom lint                 # rich-вывод в терминале
beadloom lint --strict        # exit 1 при нарушениях (для CI)
beadloom lint --format json   # машиночитаемый вывод
```

**Ограничения для агентов** — когда агент вызывает `get_context("why")`, ответ включает активные правила для этого узла. Агенты соблюдают архитектурные границы не случайно, а конструктивно — это заложено в протокол.

Поддерживаемые языки для анализа импортов: **Python, TypeScript/JavaScript, Go, Rust**.

## Команды CLI

| Команда | Описание |
|---------|----------|
| `init --bootstrap` | Сканировать код и сгенерировать архитектурный граф |
| `init --import DIR` | Импортировать и классифицировать существующую документацию |
| `reindex` | Пересобрать индекс SQLite из графа, доков и кода |
| `ctx REF_ID` | Получить пакет контекста (Markdown или `--json`) |
| `graph [REF_ID]` | Визуализировать архитектурный граф (Mermaid или JSON) |
| `search QUERY` | Полнотекстовый поиск по узлам, документам и символам кода |
| `status` | Статистика индекса и покрытие документацией |
| `doctor` | Валидация архитектурного графа |
| `sync-check` | Проверить синхронизацию док↔код |
| `sync-update REF_ID` | Просмотреть и обновить устаревшие доки |
| `lint` | Проверить код на соответствие архитектурным правилам |
| `why REF_ID` | Анализ влияния — зависимости вверх и вниз по графу |
| `diff` | Показать изменения графа относительно git-ревизии |
| `link REF_ID [URL]` | Управление ссылками на внешние трекеры |
| `ui` | Интерактивный терминальный дашборд (требует `beadloom[tui]`) |
| `watch` | Авто-реиндекс при изменении файлов (требует `beadloom[watch]`) |
| `install-hooks` | Установить pre-commit хук beadloom |
| `setup-mcp` | Настроить MCP-сервер для AI-агентов |
| `mcp-serve` | Запустить MCP-сервер (stdio-транспорт) |

## MCP-инструменты

| Инструмент | Описание |
|------------|----------|
| `get_context` | Пакет контекста по ref_id (граф + доки + символы кода + ограничения) |
| `get_graph` | Подграф вокруг узла (узлы и рёбра в JSON) |
| `list_nodes` | Список узлов графа с фильтрацией по типу |
| `sync_check` | Проверка актуальности документации |
| `get_status` | Покрытие документацией и статистика индекса |
| `update_node` | Обновить summary или метаданные узла в YAML и SQLite |
| `mark_synced` | Отметить документацию как синхронизированную с кодом |
| `search` | Полнотекстовый поиск по узлам, документам и символам кода |

## Конфигурация

Все данные проекта хранятся в `.beadloom/` в корне репозитория:

- **`.beadloom/config.yml`** — пути сканирования, языки, настройки sync engine
- **`.beadloom/_graph/*.yml`** — определение архитектурного графа (YAML, под версионным контролем)
- **`.beadloom/_graph/rules.yml`** — правила архитектурных границ
- **`.beadloom/beadloom.db`** — индекс SQLite (автогенерируемый, добавьте в `.gitignore`)

Привязка кода к узлам графа через аннотации:

```python
# beadloom:feature=AUTH-001
# beadloom:service=user-service
def authenticate(user_id: str) -> bool:
    ...
```

## Структура документации

Beadloom использует domain-first раскладку. Вот реальная структура этого проекта:

```
docs/
  architecture.md                                  # архитектура системы
  getting-started.md                               # быстрый старт
  guides/
    ci-setup.md                                    # интеграция с CI
  domains/
    context-oracle/
      README.md                                    # обзор домена
      features/
        cache/SPEC.md                              # спецификация L1+L2 кэша
        search/SPEC.md                             # спецификация FTS5 поиска
        why/SPEC.md                                # спецификация анализа влияния
    graph/
      README.md
      features/
        graph-diff/SPEC.md
        rule-engine/SPEC.md
        import-resolver/SPEC.md
    doc-sync/
      README.md
    onboarding/
      README.md
    infrastructure/
      README.md
      features/
        doctor/SPEC.md
        reindex/SPEC.md
        watcher/SPEC.md
  services/
    cli.md                                         # 21 CLI-команд
    mcp.md                                         # 10 MCP-инструментов
    tui.md                                         # TUI-дашборд
```

Каждый домен получает `README.md` (обзор, инварианты, API). Каждая фича — `SPEC.md` (назначение, структуры данных, алгоритм, ограничения).

## Пример контекстного бандла

`beadloom ctx why --json` возвращает детерминированный пакет контекста — граф, документация и символы кода, собранные через BFS за <20мс:

```json
{
  "version": 2,
  "focus": {
    "ref_id": "why",
    "kind": "feature",
    "summary": "Impact analysis — upstream deps and downstream consumers via bidirectional BFS"
  },
  "graph": {
    "nodes": [
      { "ref_id": "why", "kind": "feature", "summary": "Impact analysis ..." },
      { "ref_id": "context-oracle", "kind": "domain", "summary": "BFS graph traversal, caching, search" },
      { "ref_id": "beadloom", "kind": "service", "summary": "CLI + MCP server" },
      { "ref_id": "search", "kind": "feature", "summary": "FTS5 full-text search" },
      { "ref_id": "cache", "kind": "feature", "summary": "ETag-based bundle cache" }
    ],
    "edges": [
      { "src": "why", "dst": "context-oracle", "kind": "part_of" },
      { "src": "context-oracle", "dst": "beadloom", "kind": "part_of" },
      { "src": "cli", "dst": "context-oracle", "kind": "uses" }
    ]
  },
  "text_chunks": ["... 10 чанков из SPEC.md файлов ..."],
  "code_symbols": ["... 146 символов из модулей подграфа ..."],
  "sync_status": { "stale_docs": [], "last_reindex": "2026-02-13T..." }
}
```

BFS depth=2 от ноды `why` обходит: `why` → `context-oracle` (родительский домен) → соседние фичи (`search`, `cache`), сервисы (`cli`, `mcp-server`), кросс-доменные зависимости (`infrastructure`, `graph`) — 10 нод, 12 рёбер.

## Интеграция с Beads

*Контекстный станок для ваших [beads](https://github.com/steveyegge/beads).*

Beadloom дополняет [Beads](https://github.com/steveyegge/beads), предоставляя структурированный контекст агентам-планировщикам, кодерам и ревьюерам. Beads-воркеры вызывают `get_context(feature_id)` через MCP и получают готовый пакет вместо поиска по кодовой базе с нуля.

Beadloom работает независимо от Beads — интеграция опциональна.

## Разработка

```bash
uv sync --dev              # установка с dev-зависимостями
uv run pytest              # запуск тестов
uv run ruff check src/     # линтинг
uv run ruff format src/    # форматирование
uv run mypy                # проверка типов (strict mode)
```

## Документация

| Документ | Описание |
|----------|----------|
| [architecture.md](docs/architecture.md) | Архитектура системы и обзор компонентов |
| [getting-started.md](docs/getting-started.md) | Руководство по быстрому старту |
| **Домены** | |
| [Context Oracle](docs/domains/context-oracle/README.md) | Алгоритм BFS, сборка контекста, кэширование, поиск |
| &nbsp;&nbsp;[Cache](docs/domains/context-oracle/features/cache/SPEC.md) | L1 in-memory + L2 SQLite кэш бандлов |
| &nbsp;&nbsp;[Search](docs/domains/context-oracle/features/search/SPEC.md) | Полнотекстовый поиск FTS5 |
| &nbsp;&nbsp;[Why](docs/domains/context-oracle/features/why/SPEC.md) | Анализ влияния через двунаправленный BFS |
| [Graph](docs/domains/graph/README.md) | Формат YAML-графа, diff, rule engine, линтер |
| &nbsp;&nbsp;[Graph Diff](docs/domains/graph/features/graph-diff/SPEC.md) | Сравнение графа с git ref |
| &nbsp;&nbsp;[Rule Engine](docs/domains/graph/features/rule-engine/SPEC.md) | Architecture-as-Code правила deny/require |
| &nbsp;&nbsp;[Import Resolver](docs/domains/graph/features/import-resolver/SPEC.md) | Мультиязычный анализ импортов |
| [Doc Sync](docs/domains/doc-sync/README.md) | Механизм синхронизации док↔код |
| [Onboarding](docs/domains/onboarding/README.md) | Бутстрап проекта и пресеты |
| [Infrastructure](docs/domains/infrastructure/README.md) | База данных, метрики здоровья, реиндекс |
| &nbsp;&nbsp;[Doctor](docs/domains/infrastructure/features/doctor/SPEC.md) | Проверки валидации графа |
| &nbsp;&nbsp;[Reindex](docs/domains/infrastructure/features/reindex/SPEC.md) | Полный и инкрементальный реиндекс |
| &nbsp;&nbsp;[Watcher](docs/domains/infrastructure/features/watcher/SPEC.md) | Автореиндекс при изменении файлов |
| **Сервисы** | |
| [CLI Reference](docs/services/cli.md) | Все 21 CLI-команд |
| [MCP Server](docs/services/mcp.md) | Все 10 MCP-инструментов для AI-агентов |
| [TUI Dashboard](docs/services/tui.md) | Интерактивный терминальный дашборд |
| **Руководства** | |
| [CI Setup](docs/guides/ci-setup.md) | Интеграция с GitHub Actions / GitLab CI |

## Известные проблемы

Полный список известных проблем и ограничений: [UX Issues Log](.claude/development/BDL-UX-Issues.md).

Основные открытые вопросы:
- `sync-check` отслеживает хеши файлов, но не обнаруживает семантическое расхождение (код изменился, содержимое документации — нет) — [#15, #18]
- `setup-rules` автодетекция не работает для Windsurf/Cline (файл-маркер = файл правил) — [#17]
- `AGENTS.md` не генерируется автоматически при `beadloom init --bootstrap` — [#19]

## Лицензия

MIT

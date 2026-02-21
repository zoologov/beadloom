# Beadloom

> Read this in other languages: [English](README.md)

**Архитектура — как код. Контекст — как сервис.**

Beadloom превращает Architecture as Code в Architectural Intelligence — структурированное знание об архитектуре вашей системы, доступное людям и агентам за <20мс.

[![License: MIT](https://img.shields.io/github/license/zoologov/beadloom)](LICENSE)
[![GitHub release](https://img.shields.io/github/v/release/zoologov/beadloom?include_prereleases&sort=semver)](https://github.com/zoologov/beadloom/releases)
[![PyPI](https://img.shields.io/pypi/v/beadloom)](https://pypi.org/project/beadloom/)
[![Python](https://img.shields.io/pypi/pyversions/beadloom)](https://pypi.org/project/beadloom/)
[![Tests](https://img.shields.io/github/actions/workflow/status/zoologov/beadloom/tests.yml?label=Tests)](https://github.com/zoologov/beadloom/actions)
[![mypy: strict](https://img.shields.io/badge/mypy-strict-blue)](https://mypy-lang.org/)
[![code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![coverage: 80%+](https://img.shields.io/badge/coverage-80%25%2B-green)](pyproject.toml)

---

> IDE ищет код. Beadloom объясняет, что этот код значит в контексте всей системы — и защищает границы архитектуры.

**Платформы:** macOS, Linux, Windows &nbsp;|&nbsp; **Python:** 3.10+

## Зачем Beadloom?

В больших кодовых базах отсутствует **Architectural Intelligence** — структурированное знание, доступное по запросу, о том, как устроена система и как связаны её части. Без него команда принимает решения вне архитектурных границ — и копит технический долг. Агенты галлюцинируют.

- **«Только два человека понимают, как это работает.»** Архитектура живёт в головах, а не в репозитории. Уходят люди — уходят знания.
- **«Документация врёт.»** Документация устаревает. Никто этого не замечает, пока разработчик или агент не начнёт работать над новым функционалом на основе устаревших спецификаций.
- **«Агенты сжигают контекст на ориентирование, а не на работу.»** Каждая сессия с нуля — grep, read, guess. 2K релевантных токенов важнее, чем 128K нефильтрованного контекста.

Beadloom превращает Architecture as Code в три базовых примитива:

1. **Context Oracle** — архитектурный граф в YAML, хранится в Git. Запрос к любому узлу → детерминированный пакет контекста за <20мс. Один запрос — один результат — каждый раз.

2. **Doc Sync Engine** — отслеживает связи код↔документация. Выявляет устаревшую документацию при каждом коммите. Расхождения между спецификацией и реализацией выявляются автоматически.

3. **Architecture Rules** — архитектурные ограничения в YAML, валидация через `beadloom lint`, блокировка в CI. Границы проверяются при сборке, а не на этапе ревью.

Для AI-агентов `beadloom prime` собирает все три примитива в пакет <2K токенов — одна команда заменяет цикл grep→read→guess.

### Детерминированный контекст, а не вероятностное угадывание

Индексаторы IDE используют семантический поиск — LLM решает, что релевантно. Beadloom использует **детерминированный обход графа**: BFS по явному архитектурному графу каждый раз выдаёт один и тот же пакет контекста. Граф — YAML в Git: ревьюируется, аудируется, версионируется.

|  | Семантический поиск (IDE) | Beadloom |
|---|---|---|
| **Отвечает на** | «Где этот класс?» | «Что это за фича и как она вписывается?» |
| **Метод** | Эмбеддинги + LLM-ранжирование | Явный граф + BFS |
| **Результат** | Вероятностный | Детерминированный |
| **Документация** | Не отслеживает | Выявляет устаревшую документацию |
| **Архитектура** | Не валидирует | Проверяет границы, блокирует нарушения |
| **Знания** | Умирают с сессией | Живут в Git, переживают смену команды |

---

### Исследования и отраслевые тренды

- **[Lost in the Middle](https://arxiv.org/abs/2307.03172)** (Liu et al., 2023) — точность LLM падает, когда нужная информация расположена в середине длинного контекста. 2K релевантных токенов эффективнее, чем 128K нефильтрованного контекста.
- **[Context Engineering for Coding Agents](https://martinfowler.com/articles/exploring-gen-ai/context-engineering-coding-agents.html)** (Fowler, 2025) — структурированный контекст — ключевая возможность для coding-агентов, а не опция.
- **[From Scattered to Structured](https://arxiv.org/html/2601.19548v1)** (Keim & Kaplan, KIT, 2026) — архитектурные знания, разбросанные по артефактам, вызывают «архитектурную эрозию»; решение — консолидация в структурированную базу знаний.
- **[Why AI Coding Agents Aren't Production-Ready](https://venturebeat.com/ai/why-ai-coding-agents-arent-production-ready-brittle-context-windows-broken)** (Raja & Gemawat, VentureBeat, 2025) — практики из LinkedIn и Microsoft документируют, как агенты галлюцинируют без архитектурного контекста.
- **[Context Quality vs Quantity](https://www.augmentcode.com/guides/context-quality-vs-quantity-5-ai-tools-that-nail-relevance)** (Augment Code, 2025) — контекст с учётом архитектурных связей снижает галлюцинации на ~40% по сравнению с нефильтрованной подачей контекста.
- **[State of Software Architecture 2025](https://icepanel.io/blog/2026-01-21-state-of-software-architecture-survey-2025)** (IcePanel, 2026) — поддержание актуальности архитектурной документации — проблема №1; команды теряют доверие к устаревшим докам.
- **[2026 Agentic Coding Trends](https://claude.com/blog/eight-trends-defining-how-software-gets-built-in-2026)** (Anthropic, 2026) — индустрия переходит к оркестрации агентов со структурированным контекстом.
- **[Architecture Reset](https://itbrief.news/story/ai-coding-tools-face-2026-reset-towards-architecture)** (ITBrief, 2026) — предприятия уходят от «вайб-кодинга» к architecture-first разработке.

---

## Для кого?

**Tech Lead / Архитектор** — Вы хотите, чтобы архитектурные знания были явными, версионируемыми и пережили ротацию команды. Beadloom делает неявное явным: домены, фичи, сервисы, зависимости — всё в YAML, всё в Git. `beadloom lint` контролирует границы в CI.

**Platform / DevEx-инженер** — Вы строите инструментарий для команды. Beadloom даёт вашему CI проверку актуальности документации и валидацию архитектурных границ. Агенты получают структурированный контекст из коробки через MCP.

**Разработчик** — Вы устали тратить первый час каждой задачи на выяснение «как устроена эта часть системы?». `beadloom ctx FEATURE-ID` даёт ответ за секунды. `beadloom why NODE` покажет, что зависит от этого узла и что сломается при изменении.

**AI-Assisted / Agent-Native разработчик** — Вы работаете с AI-агентами и хотите, чтобы они работали в рамках вашей архитектуры, а не ломали её. `beadloom prime` + MCP даёт агенту компактный детерминированный контекст на старте сессии.

## Ключевые возможности

- **Context Oracle** — детерминированный обход графа, компактный JSON-пакет за <20мс
- **Doc Sync Engine** — отслеживает связи код↔документация, обнаруживает устаревшую документацию, интегрируется с git-хуками
- **Architecture as Code** — правила границ в YAML, валидация через `beadloom lint`, контроль в CI
- **Agent Prime** — единая точка входа для AI-агентов: `beadloom prime` выводит <2K токенов архитектурного контекста, `setup-rules` создаёт IDE-адаптеры, `AGENTS.md` содержит конвенции и MCP-инструменты
- **Полнотекстовый поиск** — FTS5-поиск по узлам, документам и символам кода
- **Анализ влияния** — `beadloom why` показывает, что зависит от узла и что сломается при изменении (с опциями `--reverse` и `--depth N`)
- **Code-first онбординг** — архитектурный граф строится из структуры кода; документация не нужна для старта
- **Снимки архитектуры** — `beadloom snapshot` сохраняет и сравнивает состояние архитектуры во времени
- **MCP-сервер** — 14 инструментов для AI-агентов, включая запись, поиск, анализ влияния, diff и линтинг
- **Интерактивный TUI** — `beadloom tui` — терминальный дашборд для навигации по графу (алиас: `ui`)
- **Аудит документации** — обнаружение устаревших фактов в документации проекта (README, guides, CONTRIBUTING) без конфигурации. CI-гейт через `--fail-if=stale>0`
- **Отчёт об архитектурном долге** — `beadloom status --debt-report` агрегирует lint, sync, complexity в единый балл 0-100 с CI-гейтом
- **C4-диаграммы архитектуры** — автогенерация C4 Context/Container/Component диаграмм в форматах Mermaid и PlantUML
- **Local-first** — один CLI + один файл SQLite, без Docker, без облачных зависимостей

## Как это работает

Beadloom поддерживает **архитектурный граф**, определённый в YAML-файлах в `.beadloom/_graph/`. Граф состоит из **узлов** (фичи, сервисы, домены, сущности, ADR) и **рёбер** (part_of, uses, depends_on и др.).

Конвейер индексации объединяет три источника в единую базу SQLite:

1. **Graph YAML** — узлы и рёбра, описывающие архитектуру проекта
2. **Документация** — Markdown-файлы, привязанные к узлам графа, разбитые на поисковые чанки
3. **Код** — исходники, разобранные tree-sitter для извлечения символов и аннотаций `# beadloom:domain=context-oracle`

При запросе контекста по узлу Context Oracle выполняет обход в ширину (BFS), собирает релевантный подграф, документацию и символы кода и возвращает компактный пакет.

Doc Sync Engine отслеживает, какие файлы документации соответствуют каким файлам кода. При каждом коммите (через git-хук) он обнаруживает устаревшую документацию и предупреждает или блокирует коммит.

## Architecture as Code

Beadloom не просто описывает архитектуру — он её защищает. Определяйте правила границ в YAML, валидируйте через `beadloom lint`, блокируйте нарушения в CI.

**Правила** (`.beadloom/_graph/rules.yml`) — правила этого проекта:

```yaml
version: 3

tags:
  layer-service: [cli, mcp-server, tui]
  layer-domain: [context-oracle, doc-sync, graph, onboarding]
  layer-infra: [infrastructure]

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

  - name: service-needs-parent
    description: "Every service (except root) must be part_of the beadloom service"
    require:
      for: { kind: service, exclude: [beadloom] }
      has_edge_to: { ref_id: beadloom }
      edge_kind: part_of

  - name: no-domain-depends-on-service
    description: "Domains must not have depends_on edges to services"
    deny:
      from: { kind: domain }
      to: { kind: service }
      unless_edge: [part_of]
```

**Типы правил v1.8.0** — запрет рёбер, контроль слоёв, обнаружение циклов, границы импортов и лимиты кардинальности:

```yaml
rules:
  # Запрет рёбер между тегированными группами
  - name: ui-no-native
    severity: error
    forbid:
      from: { tag: ui-layer }
      to: { tag: native-layer }
      edge_kind: uses

  # Контроль слоёв (сверху вниз)
  - name: architecture-layers
    severity: warn
    layers:
      - { name: services, tag: layer-service }
      - { name: domains, tag: layer-domain }
      - { name: infrastructure, tag: layer-infra }
    enforce: top-down
    allow_skip: true
    edge_kind: depends_on

  # Обнаружение циклов
  - name: no-dependency-cycles
    severity: warn
    forbid_cycles:
      edge_kind: depends_on

  # Границы импортов
  - name: tui-no-direct-infra
    forbid_import:
      from: "src/beadloom/tui/**"
      to: "src/beadloom/infrastructure/**"

  # Ограничения кардинальности
  - name: domain-size-limit
    severity: warn
    check:
      for: { kind: domain }
      max_symbols: 200
```

Доступно 7 типов правил: `require`, `deny`, `forbid`, `layers`, `forbid_cycles`, `forbid_import`, `check`. NodeMatcher поддерживает `tags` и `exclude` для гибкого таргетинга правил.

**Валидация:**

```bash
beadloom lint                 # rich-вывод в терминале
beadloom lint --strict        # exit 1 при нарушениях (для CI)
beadloom lint --format json   # машиночитаемый вывод
```

**Ограничения для агентов** — когда агент вызывает `get_context("why")`, ответ включает активные правила для этого узла. Агенты соблюдают архитектурные границы не случайно, а конструктивно — это заложено в протокол.

Поддерживаемые языки для анализа импортов: **Python, TypeScript/JavaScript, Go, Rust, Kotlin, Java, Swift, C/C++, Objective-C**.

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
beadloom ctx search              # получить контекст по фиче
beadloom sync-check                # проверить актуальность документации
beadloom lint                      # проверить архитектурные правила

# 4. Настраиваем инъекцию контекста для AI-агентов
beadloom setup-rules               # создать файлы-адаптеры для IDE
beadloom prime                      # проверить: увидеть то, что увидит агент
```

Документация не нужна для старта — Beadloom строит граф из структуры кода.

### Agent Prime — одна команда, полный контекст

Beadloom внедряет контекст в AI-агентов через трёхуровневую архитектуру:

1. **IDE-адаптеры** — `beadloom setup-rules` создаёт `.cursorrules`, `.windsurfrules`, `.clinerules`, которые ссылаются на `.beadloom/AGENTS.md`
2. **AGENTS.md** — конвенции проекта, архитектурные правила из `rules.yml`, каталог MCP-инструментов — загружается агентом автоматически
3. **`beadloom prime`** — динамический контекст (<2K токенов): архитектурная сводка, метрики здоровья, активные правила, карта доменов

Для программного доступа подключитесь через MCP:

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

Работает с Claude Code, Cursor, Windsurf, Cline и любым MCP-совместимым инструментом.

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
| `sync-update REF_ID` | Просмотреть и обновить устаревшую документацию |
| `docs generate` | Сгенерировать скелеты документации из архитектурного графа |
| `docs polish` | Сгенерировать структурированные данные для AI-обогащения документации |
| `lint` | Проверить код на соответствие архитектурным правилам |
| `why REF_ID` | Анализ влияния — зависимости вверх и вниз по графу |
| `diff` | Показать изменения графа относительно git-ревизии |
| `link REF_ID [URL]` | Управление ссылками на внешние трекеры |
| `tui` | Интерактивный терминальный дашборд (алиас: `ui`; требует `beadloom[tui]`) |
| `docs audit` | Обнаружение устаревших фактов в документации проекта (README, guides) |
| `watch` | Авто-реиндекс при изменении файлов (требует `beadloom[watch]`) |
| `snapshot` | Сохранение и сравнение снимков архитектуры |
| `install-hooks` | Установить pre-commit хук beadloom |
| `prime` | Вывести компактный контекст проекта для передачи AI-агенту |
| `setup-rules` | Создать файлы-адаптеры для IDE (`.cursorrules`, `.windsurfrules`, `.clinerules`) |
| `setup-mcp` | Настроить MCP-сервер для AI-агентов |
| `mcp-serve` | Запустить MCP-сервер (stdio-транспорт) |

## MCP-инструменты

| Инструмент | Описание |
|------------|----------|
| `prime` | Компактный контекст проекта для старта сессии AI-агента |
| `get_context` | Пакет контекста по ref_id (граф + документация + символы кода + ограничения) |
| `get_graph` | Подграф вокруг узла (узлы и рёбра в JSON) |
| `list_nodes` | Список узлов графа с фильтрацией по типу |
| `sync_check` | Проверка актуальности документации |
| `get_status` | Покрытие документацией и статистика индекса |
| `update_node` | Обновить summary или метаданные узла в YAML и SQLite |
| `mark_synced` | Отметить документацию как синхронизированную с кодом |
| `search` | Полнотекстовый поиск по узлам, документам и символам кода |
| `generate_docs` | Сгенерировать структурированные данные для AI-обогащения документации |
| `why` | Анализ влияния: зависимости вверх и вниз по графу |
| `diff` | Изменения графа относительно git-ревизии |
| `lint` | Запуск архитектурных правил линтинга. Возвращает нарушения в JSON |
| `get_debt_report` | Отчёт по архитектурному долгу — агрегированная оценка с категориями и основными нарушителями |

## Конфигурация

Все данные проекта хранятся в `.beadloom/` в корне репозитория:

- **`.beadloom/config.yml`** — пути сканирования, языки, настройки sync engine
- **`.beadloom/_graph/*.yml`** — определение архитектурного графа (YAML, под версионным контролем)
- **`.beadloom/_graph/rules.yml`** — правила архитектурных границ
- **`.beadloom/AGENTS.md`** — конвенции проекта и каталог MCP-инструментов для AI-агентов
- **`.beadloom/beadloom.db`** — индекс SQLite (автогенерируемый, добавьте в `.gitignore`)

Привязка кода к узлам графа через аннотации:

```python
# beadloom:domain=doc-sync
def check_freshness(db: sqlite3.Connection, ref_id: str) -> SyncStatus:
    ...
```

## Структура документации

Beadloom использует domain-first раскладку. Структура этого проекта:

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
    cli.md                                         # 29 CLI-команд
    mcp.md                                         # 14 MCP-инструментов
    tui.md                                         # TUI-дашборд
```

Каждый домен получает `README.md` (обзор, инварианты, API). Каждая фича — `SPEC.md` (назначение, структуры данных, алгоритм, ограничения).

## Пример контекстного пакета

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

BFS depth=2 от узла `why` обходит: `why` → `context-oracle` (родительский домен) → соседние фичи (`search`, `cache`), сервисы (`cli`, `mcp-server`), кросс-доменные зависимости (`infrastructure`, `graph`) — 23 ноды, 63 ребра.

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
| [CLI Reference](docs/services/cli.md) | Все 29 CLI-команд |
| [MCP Server](docs/services/mcp.md) | Все 14 MCP-инструментов для AI-агентов |
| [TUI Dashboard](docs/services/tui.md) | Интерактивный терминальный дашборд |
| **Руководства** | |
| [CI Setup](docs/guides/ci-setup.md) | Интеграция с GitHub Actions / GitLab CI |

## Известные проблемы

Полный список известных проблем и ограничений: [UX Issues Log](.claude/development/BDL-UX-Issues.md).

## Лицензия

MIT

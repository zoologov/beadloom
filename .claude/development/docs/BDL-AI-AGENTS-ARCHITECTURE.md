# AI-агенты в CI: архитектура BDL-047

> Документ описывает, **где что разворачивается**, **кто за что отвечает** и **как части системы взаимодействуют друг с другом**.
>
> Основан на [RFC BDL-047](./features/BDL-047/RFC.md) (фича F4.1 — AI tech-writer в CI).

---

## Зачем это нужно

Beadloom отслеживает дрейф документации после изменения кода. `sync-check` говорит: «этот раздел документации устарел». Но дальше документацию актуализировать необходимо вручную.

BDL-047 закрывает это. В CI запускается цикл: найти устаревшие разделы документации → попросить агента переписать только их → проверить, что дрейфа больше нет → открыть PR или MR. Человек смотрит diff и решает, мержить или нет. Автоматического merge нет и не будет.

Одна фраза, которую стоит запомнить:

**Всё в этом цикле детерминировано, кроме одного шага — переписывания раздела документации. И даже этот шаг ограничен Beadloom Gate и ревью.**

---

## Три слоя — кто есть кто

Система разделена на три части, это архитектурное решение. Beadloom остаётся ядром, поставщиком инструментов и данных, не привязывается к конкретному агентному рантайму.

| Слой | Где живёт в репозитории | Что делает |
|------|-------------------------|------------|
| **Beadloom** | `src/beadloom/` | Граф архитектуры, `sync-check`, `ctx`/`why`, `beadloom ci`. Не знает про Goose. |
| **Оркестратор** | `tools/ai_techwriter/` + CI-конфиг | Детерминированный цикл: scope → починка → gate → PR/MR. В коде и RFC называется *harness*. |
| **Goose** | На VPS runner; recipe лежит в репо | Агент: читает контекст, переписывает один раздел документации за раз. |
| **Qwen3.7-Plus** | Внешний API (DashScope) | Модель. Ключ — только в CI secret. |

Beadloom **поставляет примитивы**. Оркестратор **собирает из них цикл**. Goose **занимается только актуализацией документации** — и только в рамках, которые оркестратор ему задал.

---

## Где что физически работает

«это в облаке GitHub/GitLab или у нас на сервере?»

```mermaid
flowchart TB
  subgraph GITHUB["☁️ GitHub"]
    GH_REPO["📦 Git-репозиторий"]
    GH_SECRET["🔐 Secret: QWEN_API_KEY"]
    GH_WF["⚙️ GitHub Actions<br/>ai-techwriter.yml<br/>dispatch + nightly"]
    GH_PR["🔀 Pull Request"]
  end

  subgraph GITLAB["☁️ GitLab"]
    GL_REPO["📦 Git-репозиторий"]
    GL_SECRET["🔐 CI/CD variable: QWEN_API_KEY"]
    GL_WF["⚙️ GitLab CI<br/>.gitlab-ci.yml<br/>schedule + manual"]
    GL_MR["🔀 Merge Request"]
  end

  subgraph VPS["🖥️ Self-hosted VPS runner"]
    GH_RUNNER["GitHub Actions runner"]
    GL_RUNNER["GitLab Runner"]
    subgraph RUNTIME["Установлено на runner, версии зафиксированы"]
      UV["uv + Python"]
      BL_CLI["beadloom CLI"]
      GOOSE_RT["Goose"]
    end
    ORCH["tools/ai_techwriter/<br/>оркестратор"]
    RECIPE["Goose recipe<br/>инструкции + allow-list"]
  end

  subgraph EXTERNAL["🌐 Внешний сервис"]
    QWEN["Qwen3.7-Plus API<br/>DashScope / OpenAI-compatible"]
  end

  subgraph DEV["👩‍💻 Команда"]
    MERGE["merge кода"]
    REVIEW["ревью PR / MR"]
  end

  MERGE --> GH_REPO
  MERGE --> GL_REPO
  GH_WF -->|"запускает job"| GH_RUNNER
  GL_WF -->|"запускает job"| GL_RUNNER
  GH_SECRET --> GH_RUNNER
  GL_SECRET --> GL_RUNNER
  GH_RUNNER --> ORCH
  GL_RUNNER --> ORCH
  ORCH --> BL_CLI
  ORCH --> GOOSE_RT
  GOOSE_RT --> RECIPE
  GOOSE_RT -->|"HTTPS"| QWEN
  ORCH -->|"git branch / push"| GH_REPO
  ORCH -->|"git branch / push"| GL_REPO
  ORCH -->|"gh pr create"| GH_PR
  ORCH -->|"MR через API / glab"| GL_MR
  GH_PR --> REVIEW
  GL_MR --> REVIEW
  REVIEW --> GH_REPO
  REVIEW --> GL_REPO
```

**GitHub** и **GitLab**. В обоих случаях, в репозитории лежат: код, `docs/**`, `.beadloom/`, определение pipeline и открытые PR/MR.

**VPS runner** — единственное место, где одновременно живут Goose, оркестратор и доступ к API-ключу. На том же сервере могут работать и GitHub Actions runner, и GitLab Runner — для разных репозиториев или окружений. Job получает ephemeral workspace: каждый запуск начинается с чистого checkout.

**Qwen3.7-Plus** — облачный API. Локальной модели на сервере нет.

**Beadloom CLI** устанавливается на runner, но его исходники — часть репозитория в `src/beadloom/`. Это продукт, а не инфраструктура CI.

---

## Что лежит в репозитории и что трогаем в BDL-047

```mermaid
flowchart LR
  subgraph CORE["src/beadloom/ — ядро"]
    SYNC["sync-check --json"]
    POLISH["docs polish --format json"]
    CTX["ctx / why"]
    CI_GATE["beadloom ci"]
  end

  subgraph NEW["src/beadloom/ — новое в BDL-047"]
    MARK["mark-synced CLI<br/>beadloom sync-update --yes"]
    SETUP["beadloom setup-ai-techwriter"]
  end

  subgraph TOOLING["tools/ai_techwriter/ — оркестратор"]
    H_DISC["поиск устаревшей документации"]
    H_PKT["context packet"]
    H_LOOP["mark-synced + fixpoint"]
    H_GATE["beadloom ci"]
    H_PR["ветка + PR / MR"]
    H_RECIPE["recipe.*"]
  end

  subgraph CI["CI-конфиг"]
    GH_YML[".github/workflows/<br/>ai-techwriter.yml"]
    GL_YML[".gitlab-ci.yml<br/>ai-techwriter job"]
  end

  subgraph DOCS["docs/"]
    GUIDE["guides/ai-techwriter.md"]
    DOC_FILES["документация проекта"]
  end

  subgraph GRAPH[".beadloom/"]
    G["граф + sync_state"]
  end

  GH_YML --> TOOLING
  GL_YML --> TOOLING
  TOOLING --> CORE
  TOOLING --> NEW
  TOOLING --> G
  TOOLING --> DOC_FILES
  SETUP -.->|"генерирует"| GH_YML
  SETUP -.->|"генерирует"| GL_YML
  SETUP -.->|"генерирует"| H_RECIPE
  SETUP -.->|"генерирует"| GUIDE
```

Важный момент: **цикл repair → fixpoint → PR/MR не попадает в ядро Beadloom**. В `src/beadloom/` добавляются только:

- Неинтерактивный `mark-synced` (нужен для fixpoint-цикла; заодно закрывает UX #106);
- `beadloom setup-ai-techwriter` — авто-настройка CI-конфига, рецепта для Goose-агента и пользовательский гайд.

Инуструменты в `tools/ai_techwriter/`. Сам оркестратор **не привязан к платформе**: один и тот же Python-код вызывается и из GitHub Actions, и из GitLab CI.

---

## Границы ответственности: оркестратор vs Goose

Goose - агент, но его роль намеренно узкая. Оркестратор делает всё механическое, агент — только то, где нужно суждение.

```mermaid
flowchart TB
  subgraph DETERMINISTIC["✅ Оркестратор — детерминированно"]
    D1["Найти устаревшую документацию<br/>sync-check --json"]
    D2["Собрать context packet<br/>polish + ctx + why"]
    D3["mark-synced после правки"]
    D4["Fixpoint re-check<br/>пока sync-check ≠ 0"]
    D5["Gate: beadloom ci"]
    D6["Ветка + PR/MR / flagged PR/MR"]
    D7["Retry, бюджеты, hard caps"]
  end

  subgraph NONDET["🎲 Goose — единственный недетерминированный шаг"]
    N1["Прочитать код, diff, контекст"]
    N2["Переписать один устаревший<br/>раздел документации"]
    N3["Вернуть proposal<br/>не истину, а предложение"]
  end

  subgraph NEVER["🚫 Goose никогда"]
    X1["не выбирает scope"]
    X2["не вызывает mark-synced"]
    X3["не мержит PR / MR"]
    X4["не пишет в src/"]
  end

  D1 --> D2 --> N1
  N1 --> N2 --> N3
  N3 --> D3 --> D4 --> D5 --> D6
  D7 -.-> D6
```

Так цикл остаётся воспроизводимым: можно заменить Goose на другой агентный рантайм, не трогая ядро Beadloom.

---

## Полный пайплайн CI — шаг за шагом

Один и тот же сценарий для **GitHub Actions** и **GitLab CI**, отличается только триггер, секреты и способ открытия PR/MR.

```mermaid
sequenceDiagram
  autonumber
  participant CI as GitHub Actions / GitLab CI
  participant R as VPS runner
  participant O as Оркестратор
  participant BL as Beadloom CLI
  participant G as Goose
  participant Q as Qwen3.7-Plus
  participant Repo as Git repo

  CI->>R: trigger (dispatch / schedule)
  R->>Repo: git checkout
  R->>BL: beadloom reindex
  R->>BL: sync-check --json

  alt устаревших разделов = 0
    BL-->>O: exit 0
    O-->>CI: no-op, job завершается
  else есть устаревшая документация
    loop для каждого устаревшего раздела
      O->>BL: docs polish --json (scoped)
      O->>BL: ctx(ref), why(ref)
      O->>G: context packet
      loop tool-use
        G->>Repo: read-only: код, docs, git diff
        G->>BL: ctx, why, search, sync-check
        G->>Q: model call
        Q-->>G: ответ
      end
      G->>Repo: write только docs/**
      O->>BL: mark-synced(ref)
      O->>BL: sync-check (этот раздел)
      alt всё ещё stale
        O->>G: retry ≤ 2 + новая причина
      end
    end

    loop global fixpoint
      O->>BL: sync-check (весь репо)
      O->>BL: mark-synced для flagged refs
    end

    O->>BL: beadloom ci

    alt gate green
      O->>Repo: branch + push
      O->>CI: открыть PR / MR
    else gate не green / budget exceeded
      O->>Repo: branch + push
      O->>CI: PR/MR с флагом ⚠ needs human
    end
  end
```

### Что происходит в начале

Пайплайн стартует по расписанию (nightly / `schedule`) или вручную/триггером (`workflow_dispatch` в GitHub, `manual` job в GitLab). Раннер делает checkout, `beadloom reindex`, потом `sync-check --json`.

Если устаревшей документации нет — job сразу завершается. Никакого агента, никаких затрат на API. Это нормальный сценарий.

### Что происходит, если дрейф есть

Оркестратор идёт по списку устаревших разделов. Для каждого собирает **context packet** (об этом ниже), отдаёт Goose, тот переписывает раздел, оркестратор вызывает `mark-synced` и перепроверяет.

После всех разделов — **global fixpoint**: повторять `sync-check` по всему репо и `mark-synced` для новых flagged refs, пока не стабилизируется ноль. Это нужно, потому что правка одного доменного раздела документации может «заразить» соседние пары — известный инвариант F4.1.

В конце — `beadloom ci`. Только если gate зелёный, PR/MR открывается как обычный. Иначе — с пометкой «нужен человек», но job не зависает.

---

## Починка одного раздела документации — изнутри

```mermaid
flowchart TB
  START(["sync-check: раздел X — STALE"]) --> REASON["Причина дрейфа:<br/>symbols_changed /<br/>hash_changed / untracked<br/>+ файлы кода"]

  REASON --> PACKET["Оркестратор собирает packet"]
  PACKET --> P1["doc_path + content"]
  PACKET --> P2["drift_reason"]
  PACKET --> P3["docs_polish_json ref"]
  PACKET --> P4["ctx + why"]

  P1 & P2 & P3 & P4 --> GOOSE["Goose + Qwen3.7-Plus"]

  GOOSE --> WRITE["Запись proposal<br/>только docs/**"]
  WRITE --> MARK["mark-synced ref"]
  MARK --> RECHECK{"sync-check:<br/>раздел актуален?"}

  RECHECK -->|да| NEXT(["следующий раздел"])
  RECHECK -->|нет| FEEDBACK["retry ≤ 2<br/>+ новая причина"]
  FEEDBACK --> GOOSE

  RECHECK -->|retry исчерпаны| FLAG["раздел остаётся устаревшим<br/>→ flagged PR/MR"]
```

### Context packet — что именно получает агент

На каждый устаревший раздел оркестратор собирает пакет:

```
{
  doc_path,
  current_content,
  drift_reason,          // symbols_changed / hash_changed / untracked + файлы кода
  docs_polish_json[ref],
  ctx(ref),
  why(ref)
}
```

Beadloom отслеживает устаревшую документацию. Агент не переписывает весь каталог `docs/` — только то, что `beadloom sync-check` пометил.

---

## Поток данных: от кода до PR/MR

```mermaid
flowchart LR
  subgraph INPUTS["Входы"]
    CODE["код src/**"]
    DIFF["git diff"]
    DOC_CUR["текущий устаревший раздел"]
  end

  subgraph BEADLOOM["Beadloom"]
    REINDEX["reindex"]
    GRAPH[".beadloom/ граф"]
    SC["sync-check --json"]
    POL["docs polish --json"]
    CTX["ctx / why"]
  end

  subgraph PACKET["Context packet"]
    PK["раздел + reason + polish + ctx + why"]
  end

  subgraph AGENT["Goose"]
    AG["переписанный markdown"]
  end

  subgraph VERIFY["Верификация"]
    MS["mark-synced"]
    FP["fixpoint loop"]
    GATE["beadloom ci"]
  end

  subgraph OUTPUT["Результат"]
    PR_OK["✅ PR / MR"]
    PR_WARN["⚠️ PR/MR needs human"]
    HUMAN["ревью → merge"]
  end

  CODE --> REINDEX --> GRAPH
  GRAPH --> SC & POL & CTX
  SC --> PK
  POL --> PK
  CTX --> PK
  DOC_CUR --> PK
  DIFF -.-> AGENT
  PK --> AGENT --> AG
  AG --> MS --> FP --> GATE
  GATE -->|green| PR_OK --> HUMAN
  GATE -->|иначе| PR_WARN --> HUMAN
```

---

## Что Goose может и чего не может

Ограничение инструментов — часть безопасности. Даже если агент ошибётся, blast radius маленький.

```mermaid
flowchart TB
  GOOSE["Goose agent"]

  subgraph ALLOWED["✅ Разрешено"]
    R1["read-only FS: код, diff"]
    R2["beadloom read: ctx, why, search, sync-check"]
    R3["git read: diff, log, show"]
    R4["write: только docs/**"]
    R5["network: только endpoint модели"]
  end

  subgraph FORBIDDEN["🚫 Запрещено"]
    F1["запись в src/"]
    F2["произвольный shell"]
    F3["произвольный network"]
    F4["mark-synced / merge"]
    F5["выбор scope"]
  end

  GOOSE --> ALLOWED
  GOOSE -.-x FORBIDDEN
```

---

## Gate `beadloom ci` — финальная проверка

Перед открытием PR/MR оркестратор прогоняет полный gate:

```mermaid
flowchart LR
  CI["beadloom ci"] --> R["reindex"]
  R --> L["lint --strict"]
  L --> S["sync-check"]
  S --> C["config-check"]
  C --> D["doctor"]

  D --> GREEN{"всё green?"}
  GREEN -->|да| PR["обычный PR / MR"]
  GREEN -->|нет| FLAG["PR/MR ⚠ needs human"]
```

`sync-check = 0` доказывает **свежесть** — раздел документации ссылается на актуальные символы в коде. Это не проверка качества текста. За корректность формулировок отвечает человек на ревью.

---

## Сценарий для разработчика и ревьюера

```mermaid
flowchart TD
  A["Dev мержит код<br/>документация устаревает"] --> C["Ночной или ручной запуск<br/>pipeline ai-techwriter"]

  C --> D{"sync-check:<br/>есть устаревшее?"}
  D -->|нет| Z["Job завершается<br/>no-op"]
  D -->|да| E["AI tech-writer<br/>чинит только помеченные разделы"]

  E --> F{"sync-check = 0<br/>+ beadloom ci green?"}

  F -->|да| G["PR/MR с обновлённой документацией"]
  F -->|нет| H["PR/MR ⚠ needs human"]

  G --> I["Maintainer: ревью diff"]
  H --> I

  I --> J{"текст ок?"}
  J -->|да| K["merge"]
  J -->|нет| L["правки вручную<br/>или закрыть PR/MR"]

  K --> M["Knowledge base снова fresh"]
```

Типичный сценарий: код уехал в main → ночью (или по кнопке/триггеру) прилетает PR/MR с обновлённой документацией → смотришь diff → мержишь или правишь.

---

## Настройка: три шага для оператора

Подключение задумано простым — автоконфигурация + короткий чеклист, без ручных правок.

```mermaid
flowchart TD
  S1["1. Зарегистрировать<br/>self-hosted runner на VPS<br/>Goose установлен"]
  S2["2. Добавить QWEN_API_KEY<br/>в secrets / CI variables"]
  S3["3. beadloom setup-ai-techwriter<br/>→ commit → enable pipeline"]

  S1 --> S2 --> S3 --> DONE["schedule + manual<br/>открывают PR/MR"]

  S3 -.-> GEN["Генерирует:"]
  GEN --> G1["GitHub: ai-techwriter.yml<br/>GitLab: job в .gitlab-ci.yml"]
  GEN --> G2["Goose recipe + provider config"]
  GEN --> G3["docs/guides/ai-techwriter.md"]
```

Команда `beadloom setup-ai-techwriter` идемпотентна: можно перегенерировать. Агент **repo-agnostic** — читает граф и документацию конкретного репозитория. Для другого сервиса тот же паттерн: runner + secret + автоконфигурация. Платформа CI — на выбор: GitHub Actions или GitLab CI.

| Платформа | Runner | Секрет | Открытие ревью |
|-----------|--------|--------|----------------|
| **GitHub** | self-hosted Actions runner | Repository secret `QWEN_API_KEY` | `gh pr create` |
| **GitLab** | self-hosted GitLab Runner | CI/CD variable `QWEN_API_KEY` | Merge Request через API / `glab` |

---

## Бюджеты, retry и что бывает при сбое

Стоимость контролируется **scope** (только устаревшие разделы, не весь каталог `docs/`), а не отключением "рассуждения" у модели. Расширенное рассуждение остаётся включённым — качество важнее экономии на каждом вызове.

Hard caps — страховка от runaway, не ручка качества:

| Ограничение | Назначение |
|-------------|------------|
| retry на раздел ≤ 2 | повтор с новой причиной дрейфа |
| max fixpoint rounds | bounded re-stale-siblings |
| max turns / tokens / wall-clock | job не зависает |

При превышении бюджета или если gate не зеленеет — **flagged PR/MR**, не зависший job и не auto-merge.

```
for each stale section:
    repair via Goose → mark-synced(ref) → sync-check(section)
    if still stale: retry ≤ 2

global fixpoint:
    repeat sync-check → mark-synced until stable 0
    OR round-cap / no-progress

gate: beadloom ci

deliver:
    green  → branch + PR/MR
    not green / cap → branch + PR/MR ⚠ needs human
```

---

## Безопасность

**API-ключ** живёт в CI secrets (GitHub Secrets / GitLab CI/CD variables), доступен только job'у на self-hosted runner. В логах и репозитории его нет.

**Runner** привязан к проекту.

**Goose** пишет только в `docs/**`. Исходники не трогает.

**Auto-merge отсутствует**: `sync-check = 0` — это свежесть, не гарантия хорошего текста.

**mark-synced вне цикла** — та же операция, что интерактивный `sync-update`. Можно случайно «зеленить» плохой раздел документации. Поэтому ревью PR/MR и rationale в описании — обязательная часть процесса, а не опция.

---

## План внедрения

```mermaid
flowchart LR
  W1["Wave 1<br/>mark-synced CLI"]
  W2["Wave 2<br/>оркестратор"]
  W3["Wave 3<br/>Goose recipe"]
  W4["Wave 4<br/>CI pipeline"]
  TEST["test + review"]
  DOG["dogfood<br/>реальный drift"]
  DOC["гайд для команды"]

  W1 --> W2 --> W3 --> W4 --> TEST --> DOG --> DOC
```

Каждая волна держит `beadloom ci` green сама по себе. Dogfood (G6) — реальный прогон на дрейфе в собственном репо (#130/#131), результатом должен стать reviewable PR.

---

## Шпаргалка на одну страницу

| Вопрос | Ответ |
|--------|-------|
| Где крутится job? | Self-hosted runner на VPS (GitHub Actions или GitLab Runner) |
| Где API-ключ? | `QWEN_API_KEY` в secrets / CI variables, только на runner |
| Где модель? | Qwen3.7-Plus, внешний API |
| Где оркестрация? | `tools/ai_techwriter/` (*harness*), не в ядре Beadloom |
| Что нового в ядре? | `mark-synced` CLI + `setup-ai-techwriter` |
| Что пишет агент? | Только `docs/**` |
| Как попадает в main? | PR/MR + human merge |
| Когда no-op? | `sync-check` = 0 stale |
| Триггеры v1 | manual + nightly (`workflow_dispatch` / GitLab `schedule`) |
| Какие CI? | GitHub Actions и GitLab CI — один оркестратор, разные обёртки |

---

## Связанные документы

- [PRD BDL-047](./features/BDL-047/PRD.md) — зачем и какие цели
- [RFC BDL-047](./features/BDL-047/RFC.md) — технические решения и границы
- [ROADMAP](../ROADMAP.md) — место фичи в дорожной карте

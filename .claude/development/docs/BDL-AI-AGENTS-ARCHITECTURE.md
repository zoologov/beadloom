# AI-агенты в CI: архитектура (BDL-047 → BDL-048 → BDL-049 → BDL-050)

> Документ описывает, **где что разворачивается**, **кто за что отвечает** и **как части системы взаимодействуют друг с другом** — в **текущем** (shipped) состоянии.
>
> История: [RFC BDL-047](./features/BDL-047/RFC.md) (F4.1 — AI tech-writer в CI) → BDL-048 (packaging + MCP process-tools) → [BDL-049](./features/BDL-049/RFC.md) (trunk-based + PR-triggered) → [BDL-050](./features/BDL-050/RFC.md) (консолидация CI в один `ci.yml` + verdict).

---

## Зачем это нужно

Beadloom отслеживает дрейф документации после изменения кода. `sync-check` говорит: «этот раздел документации устарел». Но дальше документацию необходимо актуализировать вручную.

AI tech-writer закрывает это. На **каждый PR в `main`** запускается цикл: найти разделы документации, устаревшие именно из-за этого PR → попросить агента переписать только их → проверить, что дрейфа больше нет → **закоммитить правку обратно в ветку этого же PR** + оставить комментарий. Человек смотрит diff и решает, мержить или нет. Автоматического merge нет и не будет.

Одна фраза, которую стоит запомнить:

**Всё в этом цикле детерминировано, кроме одного шага — переписывания раздела документации. И даже этот шаг ограничен Beadloom Gate и человеческим ревью PR.**

---

## Три слоя — кто есть кто

Система разделена на три части, это архитектурное решение. Beadloom остаётся ядром, поставщиком инструментов и данных, не привязывается к конкретному агентному рантайму.

| Слой | Где живёт в репозитории | Что делает |
|------|-------------------------|------------|
| **Beadloom** | `src/beadloom/` | Граф архитектуры, `sync-check`, `ctx`/`why`, `beadloom ci`. Не знает про Goose. |
| **Оркестратор (harness)** | `tools/ai_techwriter/` + CI-конфиг | Детерминированный цикл: scope → починка → fixpoint → gate → verdict → publish. |
| **Goose** | На VPS runner; recipe (`tools/ai_techwriter/recipe.yaml`) лежит в репо | Агент: читает контекст, переписывает один раздел документации за раз. |
| **Qwen3.7-Plus** | Внешний API (DashScope, OpenAI-compatible) | Модель (`model = qwen3.7-plus`). Ключ — только в CI secret. |

Beadloom **поставляет примитивы**. Оркестратор **собирает из них цикл**. Goose **занимается только актуализацией документации** — и только в рамках, которые оркестратор ему задал.

**MCP process-tools (BDL-048).** Отдельно от AI tech-writer-а Beadloom отдаёт детерминированные шаги solo-flow как MCP-инструменты (`services/mcp_server.py`, каталог 18 инструментов): `task_init` / `bead_context` / `complete_bead` / `checkpoint`. Это **не оркестрация** — см. [Честная граница](#честная-граница).

---

## Где что физически работает

«это в облаке GitHub/GitLab или у нас на сервере?»

```mermaid
flowchart TB
  subgraph GITHUB["GitHub"]
    GH_REPO["Git-репозиторий"]
    GH_SECRET["Secret: QWEN_API_KEY"]
    GH_PAT["Secret: AI_TW_PAT"]
    GH_CI["GitHub Actions: ci.yml<br/>on pull_request to main"]
    GH_DEPLOY["GitHub Actions: deploy-site.yml<br/>on push to main"]
    GH_PR["Pull Request"]
  end

  subgraph GITLAB["GitLab"]
    GL_REPO["Git-репозиторий"]
    GL_SECRET["CI/CD variable: QWEN_API_KEY"]
    GL_CI[".gitlab-ci.yml<br/>verify to docs on merge_request"]
    GL_MR["Merge Request"]
  end

  subgraph CLOUD_RUN["Облачные runner-ы GitHub/GitLab"]
    JOB_GATE["job gate"]
    JOB_TESTS["job tests 3.10-3.13"]
    JOB_SITE["job site-build VitePress"]
  end

  subgraph VPS["Self-hosted VPS runner"]
    AITW["job ai-techwriter<br/>needs gate tests site-build"]
    subgraph RUNTIME["Установлено на runner, версии зафиксированы"]
      UV["uv + Python"]
      BL_CLI["beadloom CLI"]
      GOOSE_RT["Goose"]
    end
    ORCH["tools/ai_techwriter/<br/>оркестратор"]
    RECIPE["Goose recipe<br/>инструкции + allow-list"]
  end

  subgraph EXTERNAL["Внешний сервис"]
    QWEN["Qwen3.7-Plus API<br/>DashScope / OpenAI-compatible"]
  end

  subgraph DEV["Команда"]
    OPEN_PR["открыть PR в main"]
    REVIEW["ревью PR / MR"]
    MERGE["human merge"]
  end

  OPEN_PR --> GH_PR
  OPEN_PR --> GL_MR
  GH_PR --> GH_CI
  GL_MR --> GL_CI
  GH_CI --> JOB_GATE
  GH_CI --> JOB_TESTS
  GH_CI --> JOB_SITE
  GH_CI -->|"needs: all green"| AITW
  GL_CI --> JOB_GATE
  GL_CI --> AITW
  GH_SECRET --> AITW
  GH_PAT --> AITW
  GL_SECRET --> AITW
  AITW --> ORCH
  ORCH --> BL_CLI
  ORCH --> GOOSE_RT
  GOOSE_RT --> RECIPE
  GOOSE_RT -->|"HTTPS"| QWEN
  ORCH -->|"commit + push (AI_TW_PAT) в ветку PR"| GH_REPO
  ORCH -->|"commit + push (AI_TW_PAT) в ветку MR"| GL_REPO
  ORCH -->|"gh pr comment / glab MR note"| GH_PR
  GH_PR --> REVIEW
  GL_MR --> REVIEW
  REVIEW --> MERGE
  MERGE --> GH_REPO
  MERGE -->|"push: main"| GH_DEPLOY
```

**GitHub** и **GitLab**. В обоих случаях в репозитории лежат: код, `docs/**`, `.beadloom/`, определение pipeline и открытые PR/MR.

**Консолидированный `ci.yml` (BDL-050).** Один workflow на `pull_request → main`: задания `gate`, `tests` (матрица 3.10–3.13) и `site-build` (сборка VitePress) идут **параллельно** на облачных runner-ах GitHub/GitLab; `ai-techwriter` имеет `needs: [gate, tests, site-build]` и стартует **только если все три зелёные** — сломанный PR не тратит токены Qwen. Отдельный `deploy-site.yml` — **единственное**, что запускается на `push: main` (публикует VitePress на GitHub Pages); под строгим trunk-based `main` зелёный по построению.

**VPS runner** — единственное место, где одновременно живут Goose, оркестратор и доступ к API-ключу. На том же сервере могут работать и GitHub Actions runner, и GitLab Runner. Job получает ephemeral workspace: каждый запуск начинается с чистого checkout.

**Qwen3.7-Plus** — облачный API. Локальной модели на сервере нет.

**Beadloom CLI** устанавливается на runner, но его исходники — часть репозитория в `src/beadloom/`. Это продукт, а не инфраструктура CI.

---

## Trunk-based + branch protection (BDL-049 / BDL-050)

`main` — точка интеграции и **защищённая ветка**: прямой push запрещён, всё едет через PR. Каждая фича — короткоживущая ветка `features/<KEY>` → один PR в `main` → merge, когда чек-раны зелёные.

**Branch protection (BDL-050):** `onboarding/branch_protection.py` требует **7 чек-ранов** консолидированного `ci.yml` как required status checks:

```
gate · tests (3.10) · tests (3.11) · tests (3.12) · tests (3.13) · site-build · ai-techwriter
```

`enforce_admins: true` (даже владелец интегрируется через PR — строгий trunk-based, BDL-049) + 0 required reviews (solo-maintainer сам мержит, но `main` не обходится). Применяется идемпотентно через `beadloom setup-branch-protection`.

GitHub treats a *skipped* required check как нейтральный/passing: при красном `gate`/`tests`/`site-build` задание `ai-techwriter` **skipped**, и PR блокируется красными верхними проверками, а не пропущенным `ai-techwriter`. Когда верхние три зелёные — `ai-techwriter` реально запускается, и его verdict гейтит.

---

## Что лежит в репозитории

```mermaid
flowchart LR
  subgraph CORE["src/beadloom/ — ядро"]
    SYNC["sync-check --json --since"]
    POLISH["docs polish --format json"]
    CTX["ctx / why"]
    CI_GATE["beadloom ci"]
    MARK["sync-update --yes"]
    SETUP["setup-ai-techwriter / setup-agentic-flow"]
    BP["branch_protection.py<br/>7 required checks"]
    MCP["mcp_server.py<br/>4 process-tools (BDL-048)"]
  end

  subgraph TOOLING["tools/ai_techwriter/ — оркестратор"]
    H_DISC["scope: sync-check --since"]
    H_PKT["context packet"]
    H_LOOP["sync-update + fixpoint"]
    H_GATE["beadloom ci"]
    H_VERDICT["classify_verdict<br/>ok / flagged / infra"]
    H_PUB["publish: pr-branch / branch-pr"]
    H_RECIPE["recipe.yaml"]
  end

  subgraph CI["CI-конфиг"]
    GH_YML[".github/workflows/ci.yml<br/>gate∥tests∥site-build → ai-techwriter"]
    GH_DEPLOY[".github/workflows/deploy-site.yml<br/>push: main"]
    GL_YML[".gitlab-ci.yml<br/>verify → docs"]
  end

  subgraph DOCS["docs/"]
    GUIDE["guides/ai-techwriter.md<br/>guides/agentic-flow.md"]
    DOC_FILES["документация проекта"]
  end

  subgraph GRAPH[".beadloom/"]
    G["граф + sync_state"]
  end

  GH_YML --> TOOLING
  GL_YML --> TOOLING
  TOOLING --> CORE
  TOOLING --> G
  TOOLING --> DOC_FILES
  SETUP -.->|"генерирует"| GH_YML
  SETUP -.->|"генерирует"| GL_YML
  SETUP -.->|"генерирует"| H_RECIPE
  SETUP -.->|"генерирует"| GUIDE
```

Важный момент: **цикл repair → fixpoint → verdict → publish не попадает в ядро Beadloom**. В `src/beadloom/` живут только примитивы (`sync-check --since`, неинтерактивный `sync-update --yes`, `ci`, `ctx`/`why`, `branch_protection`, `setup-*`). Сам оркестратор в `tools/ai_techwriter/` **не привязан к платформе**: один и тот же Python-код (`python -m tools.ai_techwriter`) вызывается и из GitHub Actions, и из GitLab CI — отличаются только триггер, имена секретов и флаг `--platform`.

---

## Границы ответственности: оркестратор vs Goose

Goose — агент, но его роль намеренно узкая. Оркестратор делает всё механическое, агент — только то, где нужно суждение.

```mermaid
flowchart TB
  subgraph DETERMINISTIC["Оркестратор — детерминированно"]
    D1["Найти устаревшую документацию<br/>sync-check --json --since merge-base"]
    D2["Собрать context packet<br/>polish + ctx + why"]
    D3["sync-update --yes после правки"]
    D4["Fixpoint re-check<br/>пока sync-check --since не 0"]
    D5["Gate: beadloom ci"]
    D6["classify_verdict: ok / flagged / infra"]
    D7["Publish: commit в ветку PR + comment"]
    D8["Retry, бюджеты, hard caps"]
  end

  subgraph NONDET["Goose — единственный недетерминированный шаг"]
    N1["Прочитать код, diff, контекст"]
    N2["Переписать один устаревший раздел"]
    N3["Вернуть proposal — не истину"]
  end

  subgraph NEVER["Goose никогда"]
    X1["не выбирает scope"]
    X2["не вызывает sync-update"]
    X3["не мержит PR / MR"]
    X4["не пишет в src/"]
  end

  D1 --> D2 --> N1
  N1 --> N2 --> N3
  N3 --> D3 --> D4 --> D5 --> D6 --> D7
  D8 -.-> D6
```

Так цикл остаётся воспроизводимым: можно заменить Goose на другой агентный рантайм, не трогая ядро Beadloom.

---

## Полный пайплайн CI — шаг за шагом

Один и тот же сценарий для **GitHub Actions** и **GitLab CI**, отличается только триггер, секреты и способ публикации правки.

```mermaid
sequenceDiagram
  autonumber
  participant Dev as Разработчик
  participant CI as ci.yml (PR в main)
  participant V as gate ∥ tests ∥ site-build
  participant R as VPS runner (ai-techwriter)
  participant O as Оркестратор
  participant BL as Beadloom CLI
  participant G as Goose + Qwen
  participant Repo as ветка PR

  Dev->>CI: открыть / обновить PR в main
  CI->>V: gate, tests (3.10-3.13), site-build (параллельно)

  alt какой-то из трёх красный
    V-->>CI: красный чек → PR заблокирован
    Note over R: ai-techwriter SKIPPED (нет токенов Qwen)
  else все три зелёные
    CI->>R: ai-techwriter (needs выполнен)
    R->>Repo: checkout PR head (token: AI_TW_PAT)
    R->>O: loop-guard (skip, если HEAD — правка самого агента)
    O->>BL: beadloom reindex
    O->>BL: since = git merge-base origin/base HEAD
    O->>BL: sync-check --json --since

    alt устаревших разделов = 0
      O-->>CI: no-op, verdict=ok (exit 0)
    else есть устаревшая документация
      loop для каждого устаревшего раздела
        O->>BL: docs polish --json + ctx + why
        O->>G: context packet
        G-->>O: переписанный markdown (proposal)
        O->>BL: sync-update --yes (ref)
        O->>BL: re-check --since (retry ≤ 2)
      end
      O->>BL: global fixpoint (пока sync-check --since = 0)
      O->>BL: beadloom ci
      O->>Repo: commit "[skip ai-techwriter] ..." + push (AI_TW_PAT)
      O->>CI: gh pr comment / glab MR note
      Note over O,CI: verdict — ok (exit 0) / flagged (exit 1) / infra (exit 0 + warning)
    end
  end

  Dev->>Repo: human merge, когда CI зелёный
```

### Что происходит в начале

PR в `main` запускает `ci.yml`. Сначала параллельно прогоняются `gate` (вердикт `beadloom ci`), `tests` (матрица 3.10–3.13) и `site-build` (сборка VitePress). Если что-то красное — `ai-techwriter` **не стартует** (`skipped`), токены Qwen не тратятся, а PR блокируется красными проверками.

Когда все три зелёные, на VPS-runner-е стартует `ai-techwriter`. Сначала **loop-guard**: если HEAD ветки PR — это коммит самого агента (автор `beadloom-ai-techwriter` или subject содержит `[skip ai-techwriter]`), задание пропускается, чтобы push агента не запускал второй прогон. Иначе — `reindex`, вычисление baseline `since = git merge-base origin/<base> HEAD` (fallback — base SHA PR), затем `sync-check --json --since`.

Если устаревшей документации нет — verdict `ok`, no-op, exit 0.

### Что происходит, если дрейф есть

Оркестратор идёт по списку устаревших разделов. Для каждого собирает **context packet**, отдаёт Goose, тот переписывает раздел, оркестратор вызывает `sync-update --yes` и перепроверяет против `--since`.

После всех разделов — **global fixpoint**: повторять `sync-check --since` по репо и `sync-update` для новых flagged refs, пока не стабилизируется ноль (правка одного доменного раздела может «заразить» соседние пары — известный инвариант F4.1).

В конце — `beadloom ci`, затем агент **коммитит правку прямо в ветку PR** (сообщение `[skip ai-techwriter] …`, идентичность `beadloom-ai-techwriter`, push через `AI_TW_PAT` — чтобы коммит триггерил `gate`) и оставляет комментарий в PR/MR. **Verdict** определяет exit code (см. ниже).

---

## Verdict: `ok` / `flagged` / `infra` (BDL-050)

`ai-techwriter` — required-чек, который краснеет **только** при реальной нерешённой проблеме документации, но не при сбое инфраструктуры. Оркестратор (`runner.py::classify_verdict`) классифицирует прогон, а `cli.py` отображает verdict → exit code. Дискриминатор «проблема документации vs сбой инфраструктуры» — **дала ли модель хоть какой-то вывод** (`input_tokens + output_tokens > 0`):

```mermaid
flowchart TB
  RUN["Прогон завершён"] --> Q1{"result.flagged?"}
  Q1 -->|нет| OK["verdict = ok<br/>(no-op или чистый refresh)"]
  Q1 -->|да| Q2{"tokens > 0?"}
  Q2 -->|да| FLAG["verdict = flagged<br/>модель работала,<br/>но документация не чистая"]
  Q2 -->|нет| INFRA["verdict = infra<br/>агент не дал ни токена:<br/>мёртвый runner / 5xx / квота"]

  OK --> E0a["exit 0 — чек green"]
  INFRA --> E0b["exit 0 — чек green<br/>+ ::warning:: + PR comment"]
  FLAG --> E1["exit 1 — required чек RED<br/>PR заблокирован"]
```

| Verdict | Когда | Exit | Эффект |
|---------|-------|------|--------|
| **ok** | 0 stale (no-op) **или** чистый refresh (`not flagged`) | `0` | чек зелёный |
| **flagged** | модель работала (`tokens > 0`), но документация всё ещё грязная: после правки `beadloom ci` красный / fixpoint не достигнут / превышен бюджет | `1` | **чек красный → PR заблокирован** («нужен человек») |
| **infra** | агент не дал ни одного токена (`tokens == 0`): мёртвый self-hosted runner, 5xx/timeout провайдера, исчерпана квота — он *не смог запуститься* | `0` | чек зелёный + громкий `::warning::` + best-effort комментарий в PR/MR («документация НЕ проверена — перезапустите») |

Итог: мёртвый VPS или исчерпанная квота `$30` **не** замораживают merge-и; реальный нерешённый дрейф — замораживает. Классификация консервативна (`tokens == 0 ⇒ infra`); ошибочный `infra` делается заметным через CI-аннотацию, чтобы человек перезапустил, а не молча отгрузил устаревшую документацию.

---

## Починка одного раздела документации — изнутри

```mermaid
flowchart TB
  START(["sync-check --since: раздел X — STALE"]) --> REASON["Причина дрейфа:<br/>symbols_changed /<br/>hash_changed / untracked<br/>+ файлы кода"]

  REASON --> PACKET["Оркестратор собирает packet"]
  PACKET --> P1["doc_path + content"]
  PACKET --> P2["drift_reason"]
  PACKET --> P3["docs_polish_json ref"]
  PACKET --> P4["ctx + why"]

  P1 & P2 & P3 & P4 --> GOOSE["Goose + Qwen3.7-Plus"]

  GOOSE --> WRITE["Запись proposal<br/>только docs/**"]
  WRITE --> MARK["sync-update --yes ref"]
  MARK --> RECHECK{"re-check --since:<br/>раздел актуален?"}

  RECHECK -->|да| NEXT(["следующий раздел"])
  RECHECK -->|нет| FEEDBACK["retry ≤ 2<br/>+ новая причина"]
  FEEDBACK --> GOOSE

  RECHECK -->|retry исчерпаны| FLAG["раздел остаётся устаревшим<br/>→ verdict flagged"]
```

### Context packet — что именно получает агент

На каждый устаревший раздел оркестратор собирает пакет (`tools/ai_techwriter/packet.py`):

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

Агент не переписывает весь каталог `docs/` — только то, что `beadloom sync-check --since` пометил для этого PR.

---

## Поток данных: от кода до PR

```mermaid
flowchart LR
  subgraph INPUTS["Входы"]
    CODE["код src/**"]
    MB["merge-base origin/base HEAD"]
    DOC_CUR["текущий устаревший раздел"]
  end

  subgraph BEADLOOM["Beadloom"]
    REINDEX["reindex"]
    GRAPH[".beadloom/ граф"]
    SC["sync-check --json --since"]
    POL["docs polish --json"]
    CTX["ctx / why"]
  end

  subgraph PACKET["Context packet"]
    PK["раздел + reason + polish + ctx + why"]
  end

  subgraph AGENT["Goose + Qwen"]
    AG["переписанный markdown"]
  end

  subgraph VERIFY["Верификация"]
    MS["sync-update --yes"]
    FP["fixpoint loop (--since)"]
    GATE["beadloom ci"]
    VD["classify_verdict"]
  end

  subgraph OUTPUT["Результат — в ветке PR"]
    COMMIT["commit [skip ai-techwriter] + push (AI_TW_PAT)"]
    NOTE["PR/MR comment"]
    EXIT["exit: ok/infra=0, flagged=1"]
    HUMAN["ревью → human merge"]
  end

  CODE --> REINDEX --> GRAPH
  MB --> SC
  GRAPH --> SC & POL & CTX
  SC --> PK
  POL --> PK
  CTX --> PK
  DOC_CUR --> PK
  PK --> AGENT --> AG
  AG --> MS --> FP --> GATE --> VD
  VD --> COMMIT --> HUMAN
  VD --> NOTE --> HUMAN
  VD --> EXIT
```

---

## Что Goose может и чего не может

Ограничение инструментов — часть безопасности. Даже если агент ошибётся, blast radius маленький.

```mermaid
flowchart TB
  GOOSE["Goose agent"]

  subgraph ALLOWED["Разрешено"]
    R1["read-only FS: код, diff"]
    R2["beadloom read: ctx, why, search, sync-check"]
    R3["git read: diff, log, show"]
    R4["write: только docs/**"]
    R5["network: только endpoint модели"]
  end

  subgraph FORBIDDEN["Запрещено"]
    F1["запись в src/"]
    F2["произвольный shell"]
    F3["произвольный network"]
    F4["sync-update / merge"]
    F5["выбор scope"]
  end

  GOOSE --> ALLOWED
  GOOSE -.-x FORBIDDEN
```

---

## Gate `beadloom ci` — детерминированная проверка

Перед `classify_verdict` оркестратор прогоняет полный gate:

```mermaid
flowchart LR
  CI["beadloom ci"] --> R["reindex"]
  R --> L["lint --strict"]
  L --> S["sync-check"]
  S --> C["config-check"]
  C --> D["doctor"]

  D --> GREEN{"всё green?"}
  GREEN -->|да| OK["вклад в verdict: ok"]
  GREEN -->|нет| FLAG["вклад в verdict: flagged"]
```

`sync-check = 0` доказывает **свежесть** — раздел документации ссылается на актуальные символы в коде. Это не проверка качества текста. За корректность формулировок отвечает человек на ревью PR. Тот же `gate` — это и отдельное задание `gate` в `ci.yml` (через composite Action `.github/actions/beadloom-gate`), и шаг внутри прогона агента.

---

## Сценарий для разработчика и ревьюера

```mermaid
flowchart TD
  A["Dev: ветка features/<KEY><br/>код меняется, документация устаревает"] --> B["Открыть один PR в main"]
  B --> C["ci.yml: gate ∥ tests ∥ site-build"]

  C --> D{"все три green?"}
  D -->|нет| Z["PR заблокирован<br/>ai-techwriter SKIPPED"]
  D -->|да| E["ai-techwriter: чинит только<br/>помеченные разделы, коммитит в ветку PR"]

  E --> F{"verdict?"}
  F -->|ok / infra| G["чек зелёный<br/>(infra — с ::warning::)"]
  F -->|flagged| H["чек красный — нужен человек"]

  G --> I["Maintainer: ревью diff"]
  H --> I

  I --> J{"текст ок?"}
  J -->|да| K["human merge"]
  J -->|нет| L["правки вручную или закрыть PR"]

  K --> M["push: main → deploy-site.yml<br/>публикует VitePress; knowledge base fresh"]
```

Типичный сценарий: ветка фичи → один PR в `main` → CI гоняет gate/tests/site-build, затем (если зелено) AI tech-writer кладёт правку документации **в тот же PR** → смотришь diff → мержишь. Merge в `main` запускает `deploy-site.yml` (единственное на `push: main`).

---

## Настройка: три шага для оператора

Подключение задумано простым — автоконфигурация + короткий чеклист, без ручных правок.

```mermaid
flowchart TD
  S1["1. Зарегистрировать<br/>self-hosted runner на VPS<br/>(Goose установлен)"]
  S2["2. Добавить QWEN_API_KEY + AI_TW_PAT<br/>в secrets / CI variables"]
  S3["3. beadloom setup-ai-techwriter<br/>→ commit → enable pipeline"]
  S4["4. beadloom setup-branch-protection<br/>→ 7 required checks"]

  S1 --> S2 --> S3 --> S4 --> DONE["каждый PR в main:<br/>gate∥tests∥site-build → ai-techwriter"]

  S3 -.-> GEN["Генерирует:"]
  GEN --> G1["GitHub: ci.yml (consolidated)<br/>GitLab: stages в .gitlab-ci.yml"]
  GEN --> G2["Goose recipe + provider config"]
  GEN --> G3["docs/guides/ai-techwriter.md"]
```

Команда `beadloom setup-ai-techwriter` идемпотентна. Агент **repo-agnostic** — читает граф и документацию конкретного репозитория. Для другого сервиса тот же паттерн: runner + secret + автоконфигурация + branch protection. Платформа CI — на выбор: GitHub Actions или GitLab CI.

| Платформа | Runner | Секреты | Публикация | Push |
|-----------|--------|---------|------------|------|
| **GitHub** | self-hosted Actions runner | `QWEN_API_KEY`, `AI_TW_PAT` (repo secrets) | commit в ветку PR + `gh pr comment` | `AI_TW_PAT` (fallback `github.token`) |
| **GitLab** | self-hosted GitLab Runner | `QWEN_API_KEY`, `AI_TW_PAT` (CI/CD variables) | commit в ветку MR + `glab` MR note | `AI_TW_PAT` (fallback `CI_JOB_TOKEN`) |

---

## Бюджеты, retry и что бывает при сбое

Стоимость контролируется **scope** (только устаревшие разделы, не весь каталог `docs/`) и порядком `needs` (сломанный PR не доходит до агента), а не отключением «рассуждения» у модели. Расширенное рассуждение остаётся включённым — качество важнее экономии на каждом вызове.

Hard caps — страховка от runaway, не ручка качества:

| Ограничение | Назначение |
|-------------|------------|
| retry на раздел ≤ 2 | повтор с новой причиной дрейфа |
| max fixpoint rounds (10) | bounded re-stale-siblings |
| max turns (50) / tokens (2M) | job не зависает |

При превышении бюджета или если gate не зеленеет (а агент при этом работал, `tokens > 0`) — verdict `flagged`, PR заблокирован. При сбое инфраструктуры (`tokens == 0`) — verdict `infra`, PR не блокируется, но громкий `::warning::`.

```
gate ∥ tests ∥ site-build:
    any red → ai-techwriter SKIPPED, PR blocked
    all green → ai-techwriter runs:

for each stale section:
    repair via Goose → sync-update --yes(ref) → re-check --since(section)
    if still stale: retry ≤ 2

global fixpoint:
    repeat sync-check --since → sync-update until stable 0
    OR round-cap / no-progress

gate: beadloom ci

verdict:
    ok    → exit 0 (чек green)
    infra → exit 0 (чек green + ::warning:: + comment)   # tokens == 0
    flagged → exit 1 (required чек red)                   # tokens > 0, docs dirty
```

---

## Честная граница

Заявлено намеренно, без приукрашивания:

- **Оркестрация остаётся в harness/Claude-Code.** MCP-сервер (BDL-048) отдаёт *инструменты* (`task_init` / `bead_context` / `complete_bead` / `checkpoint`), а **не** оркестрацию — он не умеет спавнить субагентов или крутить main loop. Coordinator и `Agent`-spawn-волны остаются Claude-Code-native (скаффолдятся `setup-agentic-flow`). MCP process-tools — детерминированный субстрат, который flow *вызывает*, а не замена harness.
- **`complete_bead` — advisory-strong, не источник истины.** Модель сама решает его вызвать; он сильнее Markdown-инструкций (реально отказывается закрывать bead при красном gate), но слабее CI.
- **CI — единственная точка истинного enforcement.** `beadloom ci` (задание `gate`) + `tests` + `site-build` + `ai-techwriter` гоняются в CI независимо и являются required-чеками. Это гейт, который ничто не обходит.

---

## Безопасность

**API-ключ** (`QWEN_API_KEY`) и push-token (`AI_TW_PAT`) живут в CI secrets (GitHub Secrets / GitLab CI/CD variables), доступны только job-у на self-hosted runner. В логах и репозитории их нет.

**Runner** привязан к проекту; ephemeral workspace на каждый прогон.

**Goose** пишет только в `docs/**`. Исходники не трогает.

**Auto-merge отсутствует**: `sync-check = 0` — это свежесть, не гарантия хорошего текста. Человек мержит PR.

**`sync-update` вне цикла** — та же операция, что интерактивный `sync-update`. Можно случайно «зеленить» плохой раздел. Поэтому ревью PR и rationale в описании — обязательная часть процесса.

---

## Шпаргалка на одну страницу

| Вопрос | Ответ |
|--------|-------|
| Где крутится gate/tests/site-build? | Облачные runner-ы GitHub/GitLab |
| Где крутится ai-techwriter? | Self-hosted runner на VPS (Goose + ключ) |
| Триггер | `on: pull_request → main` (один `ci.yml`); `deploy-site.yml` — единственное на `push: main` |
| Порядок | `gate ∥ tests ∥ site-build` → `ai-techwriter` (`needs:`) |
| Baseline дрейфа | `git merge-base origin/<base> HEAD` (`--since`) |
| Куда кладётся правка | commit в ветку **этого же** PR (`--target pr-branch`, push через `AI_TW_PAT`) |
| Verdict | `ok`/`infra` → exit 0; `flagged` → exit 1 (только реальный дрейф блокирует) |
| Required checks | 7: `gate`, `tests (3.10..3.13)`, `site-build`, `ai-techwriter` |
| Branch protection | `enforce_admins: true`, 0 reviews (strict trunk-based) |
| Как попадает в main | PR + human merge (нет auto-merge) |
| Что пишет агент | только `docs/**` |
| Какие CI | GitHub Actions и GitLab CI — один оркестратор, разные обёртки |

---

## Связанные документы

- [RFC BDL-050](./features/BDL-050/RFC.md) — консолидация CI + verdict (текущая модель)
- [RFC BDL-049](./features/BDL-049/RFC.md) — trunk-based + PR-triggered
- [RFC BDL-047](./features/BDL-047/RFC.md) — F4.1, первичная архитектура harness
- [`docs/guides/ai-techwriter.md`](../../../docs/guides/ai-techwriter.md) — гайд для оператора
- [`docs/guides/agentic-flow.md`](../../../docs/guides/agentic-flow.md) — упакованный multi-agent flow + MCP process-tools
- [ROADMAP](../ROADMAP.md) — место фич в дорожной карте

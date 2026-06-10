<!-- beadloom:badge-start -->
> 📘 **reference** — overview/guide, not tied to a code symbol
> 
> _Validation by Beadloom `doc_sync` — same source as `sync-check`._
<!-- beadloom:badge-end -->

# Сценарий выступления: Beadloom для команды (30 мин)

> Слайды: `beadloom-team-30min.md`
> Аудитория: команда · язык: русский

---

## Подготовка (до встречи, 5 мин)

```bash
cd /path/to/beadloom   # или ваш репозиторий с beadloom
beadloom reindex       # свежий индекс
beadloom sync-check    # убедиться, что 0 stale
```

Открыть заранее в браузере:
- https://zoologov.github.io/beadloom/ (dashboard)
- https://zoologov.github.io/beadloom/architecture (или /landscape)

Терминал: увеличить шрифт, тёмная тема, ширина ~120 cols.

---

## Тайминг по блокам

| Мин | Слайды | Действие |
|-----|--------|----------|
| 0–2 | Титул, «Зачем мы здесь» | Приветствие, озвучить план |
| 2–7 | Проблема, Что такое Beadloom, vs IDE | Рассказ, без демо |
| 7–14 | Архитектура, data flow, метрики, AaC, CI | Можно показать `rules.yml` в редакторе |
| 14–24 | **Демо** (5 шагов) | Терминал + браузер |
| 24–28 | Федерация, Agentic-стек | Рассказ |
| 28–30 | Roadmap, выводы, Q&A | Вопросы |

---

## Что говорить: ключевые фразы

### Проблема (слайд 3)
«Самые дорогие баги — не внутри одного файла, а **между** сервисами и **между** тем, что мы задумали, и тем, что в коде. Beadloom следит за этим расхождением системно.»

### Позиционирование (слайд 4–5)
«Мы не конкурируем с Cursor. Cursor отвечает „где класс“. Beadloom отвечает „что это за фича, кому она нужна, какие правила на неё действуют, актуальна ли документация“.»

### Честность (слайд 10–11)
«Каждая цифра на дашборде портала считается тем же кодом, что и `beadloom ci`. Если гейт зелёный — портал не врёт.»

### Демо (слайды 13–17)
«Сейчас покажу на живом репозитории Beadloom — мы сами себя проверяем этим инструментом.»

### Agentic (слайд 19)
«Агент может написать что угодно. Но merge возможен только когда `beadloom ci` зелёный. Агент — предложение, гейт — истина.»

---

## Демо-скрипт (пошагово)

### Шаг 1 — status (2 мин)

```bash
beadloom status
beadloom status --debt-report
```

**Показать:** 26 узлов, 96% doc coverage, 0 stale, debt 10/100.

**Комментарий:** «Debt score — не субъективная оценка, а формула из lint + sync + complexity. Можно гейтить в CI.»

---

### Шаг 2 — graph + ctx (3 мин)

```bash
beadloom graph
# если есть mermaid-cli или IDE preview — показать диаграмму
# иначе:
beadloom graph context-oracle

beadloom ctx context-oracle | head -60
beadloom why context-oracle
```

**Комментарий:** «`why` — blast radius: что сломается, если я поменяю этот домен. Полезно перед рефакторингом.»

---

### Шаг 3 — sync + lint (2 мин)

```bash
beadloom sync-check
echo "exit code: $?"
beadloom lint
beadloom doctor
```

**Комментарий:** «sync-check exit 2 = есть устаревшие доки. pre-commit hook не даст закоммитить.»

---

### Шаг 4 — prime + MCP (2 мин)

```bash
beadloom prime | wc -c    # показать компактность
beadloom prime | head -40
```

**Комментарий:** «В начале сессии агент вызывает prime — меньше 2K токенов вместо 200K шума из grep.»

Упомянуть 18 MCP tools, показать фрагмент из `.beadloom/AGENTS.md` или `docs/services/mcp.md`.

---

### Шаг 5 — портал (3 мин)

Переключиться в браузер:

1. **Dashboard** — status cards, gauges, recommendations
2. **Architecture** — pan/zoom на диаграмме
3. **Landscape** — цветные рёбра по вердиктам контрактов

**Комментарий:** «Сайт генерируется `beadloom docs site` — не руками, не LLM. Обновили граф → пересобрали сайт.»

---

## Возможные вопросы команды

| Вопрос | Ответ |
|--------|-------|
| «Сколько стоит внедрение?» | Бесплатно, MIT, локально. Нужен Python 3.10+, `pipx install beadloom`. |
| «Сколько времени на bootstrap?» | `init --bootstrap` + правка графа — от часа на маленьком сервисе. Точность bootstrap ~80%, дорабатывается вручную. |
| «Заменяет Confluence/Notion?» | Нет — дополняет. Доки в Markdown в репо, Beadloom следит за связью с кодом. |
| «А если нет микросервисов?» | Федерация не нужна. Три столпа (ctx, sync, lint) работают в монолите. |
| «Как связано с Beads?» | Beads = задачи/DAG. Beadloom = архитектурный контекст. Вместе в agentic flow. |
| «Почему не embeddings?» | Детерминизм и CI-гейты. Семантика — в планах для 1000+ узлов (P3). |

---

## Как экспортировать слайды

### VS Code / Cursor (рекомендуется)

1. Установить расширение **Marp for VS Code**
2. Открыть `docs/presentations/beadloom-team-30min.md`
3. `Cmd+Shift+P` → «Marp: Export Slide Deck» → PDF или HTML

### CLI

```bash
npx @marp-team/marp-cli docs/presentations/beadloom-team-30min.md \
  --pdf -o docs/presentations/beadloom-team-30min.pdf

npx @marp-team/marp-cli docs/presentations/beadloom-team-30min.md \
  --html -o docs/presentations/beadloom-team-30min.html
```

### Презентация в браузере (HTML)

Экспортированный HTML открывается локально, стрелки ← → для навигации.

---

## После встречи

Разослать команде:
- ссылку на портал
- `docs/getting-started.md`
- `pipx install beadloom` + чеклист первого дня:

```bash
beadloom init --bootstrap
beadloom reindex
beadloom ctx <ваша-фича>
beadloom install-hooks
```

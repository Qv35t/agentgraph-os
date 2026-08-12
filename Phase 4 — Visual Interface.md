# Phase 4 — Visual Interface

## Status

**Planned**

## Goal

Создать полноценный визуальный интерфейс AgentGraph OS поверх уже реализованного Remote Interface Foundation.

Phase 4 должна превратить существующий backend/runtime в удобную рабочую систему, которой можно управлять через браузер локально и удалённо без прямой работы с терминалом или backend API.

Главный принцип:

> Frontend работает только через стабильные `/api/v1/*` и `/ws/events` контракты и не зависит напрямую от внутренней реализации runtime, LangGraph или provider adapters.

Phase 4 не должна ломать существующие backend-контракты и не должна создавать отдельный параллельный API только для UI.

---

# 1. Current Foundation

Перед началом Phase 4 уже реализовано:

- ModelRouter;
- ProviderRegistry;
- Ollama provider;
- OpenCode Server bridge;
- OpenAI-compatible provider;
- LangGraph runtime integration;
- normalized provider metadata;
- run lifecycle;
- Remote Interface Foundation;
- normalized remote events;
- normalized commands;
- principals;
- permissions;
- approvals;
- transport-neutral event bus;
- secret redaction;
- REST API;
- WebSocket event stream;
- server-side authorization.

Доступные интерфейсы:

```text
/api/v1/health
/api/v1/system
/api/v1/projects
/api/v1/agents
/api/v1/providers
/api/v1/events

/api/v1/runs/{run_id}
/api/v1/agents/{agent_id}/runs
/api/v1/runs/{run_id}/stop

/api/v1/approvals
/api/v1/approvals/{...}/approve
/api/v1/approvals/{...}/reject

/ws/events
```

Remote control отключён по умолчанию:

```env
AGENTGRAPH_REMOTE_CONTROL_ENABLED=false
```

Стабильный error envelope:

```json
{
  "error": {
    "code": "...",
    "message": "...",
    "details": {}
  }
}
```

Phase 4 обязана использовать эти контракты как основной источник данных.

---

# 2. Product Target

После Phase 4 пользователь должен иметь возможность открыть AgentGraph OS в браузере и выполнять основные рабочие операции без терминала.

Минимальный пользовательский путь:

```text
Open AgentGraph OS
        ↓
Dashboard
        ↓
Select project
        ↓
Select/create agent workflow
        ↓
Start run
        ↓
Observe live execution
        ↓
Approve/reject actions when required
        ↓
Inspect output/events/metadata
        ↓
Stop or finish run
```

Интерфейс должен работать:

- на desktop;
- на laptop;
- на tablet;
- на mobile browser.

Основной приоритет Phase 4 — desktop/browser experience.

Mobile должен быть функциональным, но отдельный полноценный mobile-native UI в эту фазу не входит.

---

# 3. Architecture Principles

## 3.1 Frontend is a client

Frontend не должен:

- импортировать Python backend код;
- зависеть от LangGraph internals;
- напрямую обращаться к Ollama;
- напрямую обращаться к OpenCode Server;
- напрямую обращаться к OpenAI-compatible endpoints;
- хранить provider secrets;
- самостоятельно принимать authorization decisions;
- создавать отдельную бизнес-логику, дублирующую backend.

Frontend должен:

```text
UI
 ↓
Frontend API Client
 ↓
/api/v1
 ↓
Remote Service
 ↓
Runtime
```

Live events:

```text
Runtime
 ↓
Event Bus
 ↓
/ws/events
 ↓
Frontend Event Client
 ↓
Frontend Store
 ↓
UI
```

---

# 4. Recommended Frontend Stack

Использовать существующий frontend stack проекта, если он уже определён.

Если frontend ещё не сформирован окончательно, предпочтительный стек:

```text
React
TypeScript
Vite
pnpm
```

Допустимые дополнительные библиотеки:

- React Router;
- TanStack Query;
- Zustand;
- Zod;
- Lucide;
- lightweight utility libraries.

Не добавлять тяжёлый UI framework без необходимости.

В частности, не делать архитектуру зависимой от:

- Material UI;
- Ant Design;
- Chakra;
- Bootstrap;

если такой dependency уже не используется проектом.

UI components желательно строить локально.

---

# 5. Target Frontend Structure

Рекомендуемая структура:

```text
frontend/
├── src/
│   ├── app/
│   │   ├── App.tsx
│   │   ├── router.tsx
│   │   └── providers.tsx
│   │
│   ├── api/
│   │   ├── client.ts
│   │   ├── health.ts
│   │   ├── system.ts
│   │   ├── projects.ts
│   │   ├── agents.ts
│   │   ├── runs.ts
│   │   ├── providers.ts
│   │   ├── approvals.ts
│   │   └── events.ts
│   │
│   ├── contracts/
│   │   ├── common.ts
│   │   ├── system.ts
│   │   ├── project.ts
│   │   ├── agent.ts
│   │   ├── run.ts
│   │   ├── provider.ts
│   │   ├── approval.ts
│   │   └── event.ts
│   │
│   ├── components/
│   │   ├── layout/
│   │   ├── navigation/
│   │   ├── status/
│   │   ├── feedback/
│   │   └── ui/
│   │
│   ├── features/
│   │   ├── dashboard/
│   │   ├── projects/
│   │   ├── agents/
│   │   ├── runs/
│   │   ├── providers/
│   │   ├── approvals/
│   │   └── events/
│   │
│   ├── pages/
│   │   ├── DashboardPage.tsx
│   │   ├── ProjectsPage.tsx
│   │   ├── ProjectPage.tsx
│   │   ├── AgentsPage.tsx
│   │   ├── AgentPage.tsx
│   │   ├── RunPage.tsx
│   │   ├── ProvidersPage.tsx
│   │   ├── ApprovalsPage.tsx
│   │   ├── EventsPage.tsx
│   │   └── SettingsPage.tsx
│   │
│   ├── stores/
│   │   ├── connection.ts
│   │   ├── events.ts
│   │   └── ui.ts
│   │
│   ├── hooks/
│   ├── lib/
│   ├── styles/
│   └── main.tsx
│
├── public/
├── package.json
└── vite.config.ts
```

Не создавать директории только ради структуры.

Если существующая структура проекта уже лучше соответствует architecture rules — расширять её, а не переписывать целиком.

---

# 6. API Client Layer

Создать единый API client.

Например:

```text
src/api/client.ts
```

Он должен централизованно обрабатывать:

- base URL;
- JSON requests;
- headers;
- identity header foundation;
- timeout;
- network errors;
- remote error envelope;
- HTTP status handling.

UI components не должны самостоятельно писать:

```ts
fetch(...)
```

во всех страницах.

Вместо этого:

```ts
getSystem()
getProjects()
getAgents()
getProviders()
getRun()
startAgentRun()
stopRun()
getApprovals()
approveRequest()
rejectRequest()
```

---

# 7. Contract Validation

Frontend должен иметь строгие TypeScript contracts.

При необходимости использовать Zod для runtime validation данных с backend.

Особенно валидировать:

- WebSocket events;
- errors;
- approvals;
- run states;
- provider metadata.

Нельзя бесконтрольно приводить backend responses:

```ts
response as SomeType
```

без проверки там, где данные поступают из внешней границы.

---

# 8. Application Shell

Создать главный shell приложения.

Desktop layout:

```text
┌────────────────────────────────────────────────────────────┐
│ AgentGraph OS                           Connection / User   │
├───────────────┬────────────────────────────────────────────┤
│               │                                            │
│ Dashboard     │                                            │
│ Projects      │                Workspace                   │
│ Agents        │                                            │
│ Runs          │                                            │
│ Approvals     │                                            │
│ Providers     │                                            │
│ Events        │                                            │
│ Settings      │                                            │
│               │                                            │
├───────────────┴────────────────────────────────────────────┤
│ Runtime / provider / websocket status                     │
└────────────────────────────────────────────────────────────┘
```

Навигация должна быть persistent на desktop.

На mobile использовать drawer/sheet или компактную навигацию.

---

# 9. Design Direction

Интерфейс AgentGraph OS должен ощущаться как рабочая система для AI agents, а не обычная SaaS admin panel.

Визуальная концепция:

```text
Dark technical workspace
+
Graph-oriented information architecture
+
Modern developer tooling
+
Minimal OS/dashboard aesthetics
```

Избегать:

- яркого marketing UI;
- огромных hero sections;
- excessive gradients;
- decorative glassmorphism;
- ненужных анимаций;
- чрезмерно округлённых карточек;
- визуального шума.

Предпочтительно:

- dark theme first;
- спокойный нейтральный фон;
- чёткие borders;
- компактные панели;
- моноширинный текст для IDs, models, events;
- понятные state colors;
- высокая информационная плотность;
- аккуратные hover/focus states.

UI должен хорошо подходить для длительной работы.

---

# 10. Design Tokens

Создать собственный набор CSS variables/tokens.

Минимально:

```css
--bg
--surface
--surface-raised
--surface-hover

--border
--border-strong

--text
--text-muted
--text-subtle

--accent
--success
--warning
--danger
--info

--radius-sm
--radius-md
--radius-lg

--space-1
--space-2
--space-3
--space-4
--space-6
--space-8
```

Цвета не должны быть разбросаны случайными hex values по компонентам.

---

# 11. Dashboard

Создать `/`.

Dashboard показывает состояние всей системы.

Минимальные блоки:

## System

- API availability;
- remote control status;
- runtime status;
- current environment.

## Providers

- доступные providers;
- availability;
- default model;
- provider count.

## Agents

- total;
- active;
- currently running.

## Runs

- active runs;
- recently completed;
- failed runs.

## Approvals

- pending approval count;
- ссылка на approvals.

## Event Feed

Показывать последние события в реальном времени.

Пример:

```text
14:31:07 run.started
14:31:08 model.selected
14:31:09 provider.request.started
14:31:11 approval.required
14:31:16 approval.approved
14:31:21 run.completed
```

---

# 12. Projects

Создать `/projects`.

Показывать список доступных проектов.

Для каждого проекта:

- name;
- id;
- status;
- agents;
- recent activity.

Страница проекта:

```text
/projects/:projectId
```

Должна показывать:

- project identity;
- related agents;
- recent runs;
- project activity.

Не добавлять CRUD функций, если backend ещё не предоставляет соответствующий API.

Frontend не должен симулировать backend capabilities.

---

# 13. Agents

Создать:

```text
/agents
/agents/:agentId
```

Agent list:

- id;
- name;
- status;
- provider/model;
- active run;
- recent activity.

Agent detail:

- identity;
- configuration metadata;
- current state;
- selected model/provider;
- run history;
- start run action.

---

# 14. Run Creation

Если существующий API уже позволяет запуск агента:

```text
POST /api/v1/agents/{agent_id}/runs
```

создать UI запуска.

Минимальный composer:

```text
┌─────────────────────────────────────┐
│ Task                                │
│                                     │
│ [                               ]   │
│ [                               ]   │
│                                     │
│ Provider/model: Auto                │
│                                     │
│                 [ Start run ]       │
└─────────────────────────────────────┘
```

Не добавлять fake settings, которых backend пока не поддерживает.

---

# 15. Run Workspace

Это главный рабочий экран Phase 4.

Route:

```text
/runs/:runId
```

Пример layout:

```text
┌───────────────────────────────────────────────────────────┐
│ Run #abc123       Running        qwen3...       [ Stop ] │
├─────────────────────────────┬─────────────────────────────┤
│                             │                             │
│ Main Output                 │ Event Timeline              │
│                             │                             │
│ Agent response              │ run.started                 │
│ reasoning-visible outputs   │ model.selected              │
│ tool/runtime output         │ provider.started            │
│                             │ approval.required           │
│                             │ ...                         │
│                             │                             │
├─────────────────────────────┴─────────────────────────────┤
│ Metadata / diagnostics                                  ▼ │
└───────────────────────────────────────────────────────────┘
```

---

# 16. Run State

UI должен корректно отображать normalized run states.

Например:

```text
queued
starting
running
waiting
completed
failed
cancelled
```

Использовать реальные состояния backend.

Не создавать новые значения только для frontend.

---

# 17. Live Events

Подключить `/ws/events`.

Создать отдельный WebSocket client.

Он должен поддерживать:

- connect;
- disconnect;
- reconnect;
- connection status;
- malformed payload handling;
- normalized event parsing.

При временной потере соединения приложение не должно падать.

Показывать состояние:

```text
Connected
Reconnecting
Disconnected
```

---

# 18. Event Store

Не складывать бесконечное число событий в browser memory.

Использовать bounded store.

Например:

```text
MAX_UI_EVENTS = 500
```

или другое разумное значение.

Это frontend limit и не должно менять backend event bus.

---

# 19. Event Timeline

Создать reusable component:

```text
<EventTimeline />
```

Функции:

- timestamp;
- event type;
- run;
- agent;
- source;
- expandable payload.

Не показывать огромный JSON по умолчанию.

Payload раскрывается по запросу.

---

# 20. Event Filtering

Events page:

```text
/events
```

Минимальные фильтры:

- event type;
- run ID;
- agent ID.

Если backend API не поддерживает server-side filtering — разрешается client-side filtering только для уже загруженного bounded dataset.

Не делать вид, что это полноценный historical event database.

---

# 21. Approvals

Создать:

```text
/approvals
```

Показывать:

- pending approvals;
- action description;
- originating agent;
- originating run;
- requested permission/action;
- timestamp.

Действия:

```text
Approve
Reject
```

---

# 22. Approval Safety UX

Approval нельзя превращать в незаметный one-click background action.

Перед отправкой пользователь должен понимать:

- что запрашивается;
- какой agent запросил;
- к какому run относится;
- какое действие будет разрешено.

Для потенциально опасных действий использовать дополнительную confirmation step в UI, если информация backend позволяет классифицировать действие.

Но frontend confirmation является UX-защитой, а не security boundary.

Решение всё равно проверяется backend authorization layer.

---

# 23. Approval Live Updates

При получении:

```text
approval.required
```

UI должен:

1. обновить pending approval count;
2. показать notification/indicator;
3. обновить relevant Run Workspace.

После approve/reject событие должно обновлять интерфейс без manual reload.

---

# 24. Current Approval Limitation

Phase 4 должна учитывать, что durable approval persistence и runtime pause/resume semantics ещё могут быть не реализованы полностью.

Не скрывать это архитектурно.

Не создавать frontend workaround, который станет альтернативной approval storage system.

---

# 25. Providers

Создать:

```text
/providers
```

Отображать provider registry.

Для каждого provider:

- provider ID;
- type;
- availability;
- endpoint metadata;
- model list;
- capabilities;
- health/status, если доступен.

---

# 26. Models

Для каждой модели по возможности показывать:

```text
provider/model
```

Например:

```text
ollama/qwen3-4b-nothink:latest
```

Auto route:

```text
auto://default
```

должен отображаться как отдельный логический route, а не маскироваться как конкретная модель до момента выбора runtime.

После запуска фактически выбранные:

- provider;
- model;

показывать через run metadata.

---

# 27. Provider Secrets

Frontend никогда не должен:

- получать API key;
- показывать API key;
- сохранять API key;
- логировать API key;
- помещать secret в browser localStorage.

Использовать только redacted metadata backend.

---

# 28. System Page / Status

Информация `/api/v1/system` должна использоваться для:

- system status;
- runtime capabilities;
- remote status;
- environment info.

Если отдельная System page не нужна, эти данные допускается вывести на Dashboard/Settings.

---

# 29. Settings

Создать базовую:

```text
/settings
```

Phase 4 settings ограничены client-safe preferences.

Допустимые:

- theme;
- compact mode;
- event display preferences;
- optional UI preferences.

Не создавать UI для изменения backend secrets.

Если backend settings API отсутствует — не симулировать server settings.

---

# 30. Remote Control Disabled State

При:

```env
AGENTGRAPH_REMOTE_CONTROL_ENABLED=false
```

UI должен продолжать работать в разрешённом read-only режиме, если это допускают backend policies.

Control actions должны:

- быть disabled или hidden;
- иметь понятное объяснение.

Пример:

```text
Remote control is disabled by server configuration.
```

Frontend никогда не должен пытаться обходить эту настройку.

---

# 31. Authorization

Permissions определяются backend.

В UI использовать permissions исключительно для UX:

```text
read
execute
control
approve
admin
```

Например:

```text
read
→ view dashboard

execute
→ start run

control
→ stop run

approve
→ approve/reject

admin
→ future administrative actions
```

Но backend остаётся единственным authoritative authorization layer.

---

# 32. Identity Foundation

Текущий identity header:

> authorization foundation, not credential issuer

Phase 4 должна строго соблюдать это ограничение.

Не называть текущий механизм:

```text
secure authentication
login
SSO
account security
```

если настоящая credential issuance/authentication система ещё не существует.

Можно использовать технический dev identity selector только если это разрешено существующей architecture documentation.

---

# 33. Error Handling

Создать единый error handling system.

Backend error:

```json
{
  "error": {
    "code": "permission_denied",
    "message": "Permission denied",
    "details": {}
  }
}
```

UI должен отображать:

- user-readable message;
- error code;
- technical details только при раскрытии.

Не показывать raw stack traces обычному пользователю.

---

# 34. Loading States

Каждый async view должен иметь:

- loading;
- empty;
- error;
- success.

Запрещено оставлять blank screen во время загрузки.

---

# 35. Empty States

Примеры:

```text
No agents available.
No runs yet.
No pending approvals.
No providers discovered.
No recent events.
```

Empty state должен отличаться от:

```text
API unavailable.
```

---

# 36. Network Failure

При недоступности backend:

Dashboard должен показывать понятное состояние:

```text
Backend unavailable
```

и возможность retry.

Приложение не должно превращаться в бесконечный loading spinner.

---

# 37. WebSocket Failure

REST API и WebSocket считаются отдельными каналами.

Возможное состояние:

```text
API: Connected
Events: Disconnected
```

UI обязан различать их.

---

# 38. Notifications

Создать минимальную notification system.

Использовать для:

- run started;
- run stopped;
- run failed;
- approval required;
- approval submitted;
- connection lost.

Не создавать постоянный поток toast для каждого runtime event.

---

# 39. Accessibility

Минимальные требования:

- keyboard navigation;
- visible focus states;
- semantic buttons;
- labels;
- sufficient contrast;
- aria attributes там, где нужны;
- dialogs должны удерживать focus;
- Escape закрывает modal/dialog, где это безопасно.

Не использовать `<div onClick>` вместо button.

---

# 40. Responsive UI

Minimum breakpoints:

```text
mobile
tablet
desktop
```

На узком экране:

- sidebar collapses;
- tables могут превращаться в cards/lists;
- run workspace становится single-column или tabs;
- approval controls остаются доступными.

Нельзя требовать горизонтальный desktop viewport для базового управления агентом.

---

# 41. PWA Foundation

Phase 4 должна подготовить архитектуру к PWA, но полноценный offline-first режим не требуется.

Если это не усложняет стек:

- manifest;
- installability foundation;
- mobile meta tags;
- icons placeholders.

Service Worker разрешается только если он не создаёт проблемы stale API/cache.

Не кэшировать динамические AgentGraph API responses без строгой необходимости.

---

# 42. Theme

Минимум:

```text
Dark
```

Light theme можно добавить, если это просто реализуется через tokens.

Но Phase 4 не должна задерживаться ради полной theme system.

---

# 43. Reusable Components

Создать reusable primitives минимум для:

```text
Button
IconButton
Input
Textarea
Select
Badge
StatusBadge
Card/Panel
Dialog
Drawer
Tabs
Tooltip
Spinner
EmptyState
ErrorState
```

Не копировать одинаковую UI markup во всех feature modules.

---

# 44. Status Components

Создать унифицированные отображения состояний:

```text
AgentStatus
RunStatus
ProviderStatus
ConnectionStatus
ApprovalStatus
```

---

# 45. Run Metadata Inspector

Run Workspace должен иметь metadata inspector.

Минимально:

- run ID;
- agent ID;
- provider;
- model;
- timestamps;
- normalized metadata;
- status.

Raw JSON допускается как secondary expandable view.

---

# 46. Developer Diagnostics

Добавить development-only diagnostics, если это полезно.

Например:

```text
API base URL
WebSocket URL
connection state
last event
build version
```

Не показывать secrets.

---

# 47. Configuration

Добавить frontend env placeholders.

Например:

```env
VITE_AGENTGRAPH_API_URL=
VITE_AGENTGRAPH_WS_URL=
```

Но если frontend обслуживается тем же backend origin, предпочтительно поддержать relative defaults:

```text
/api/v1
/ws/events
```

Не требовать обязательную ручную конфигурацию для localhost.

---

# 48. Local Development

Разработчик должен иметь возможность запустить:

```bash
pnpm dev
```

для frontend и подключиться к локальному backend.

Если нужны proxy rules Vite — добавить их.

Например:

```text
/api → backend
/ws → backend
```

Конкретные ports брать из существующей конфигурации проекта.

Не хардкодить новые ports без проверки.

---

# 49. Production Serving

Подготовить frontend build:

```bash
pnpm build
```

Phase 4 должна определить один из вариантов:

```text
A. frontend served separately

или

B. frontend static build served by AgentGraph backend
```

Предпочесть решение, которое лучше соответствует текущей архитектуре проекта.

Не добавлять дополнительный production server без необходимости.

---

# 50. Browser Compatibility

Минимально проверить:

- Chromium/Chrome;
- Brave;
- Firefox.

WebSocket и основной UI должны работать одинаково.

---

# 51. Testing Strategy

Добавить frontend tests для наиболее критичной логики.

Не требуется тестировать каждый декоративный компонент.

Приоритет:

### API client

- successful response;
- error envelope;
- network failure;
- permission denied.

### Event client

- valid event;
- malformed event;
- reconnect behavior;
- bounded event store.

### Permissions

- execute action unavailable without permission;
- approve unavailable without permission.

### Runs

- start;
- status render;
- stop;
- failed state.

### Approvals

- pending;
- approve;
- reject.

---

# 52. Mocking

Frontend tests не должны требовать live Ollama/OpenCode/OpenAI.

Использовать mocked API contracts.

Live provider tests остаются backend responsibility.

---

# 53. End-to-End Smoke

Добавить минимальный browser smoke test, если существующая инфраструктура позволяет.

Проверить:

```text
open UI
→ dashboard loads
→ projects/agents visible
→ start mocked/test run
→ run page opens
→ websocket event appears
→ stop works
→ approval appears
→ approve/reject works
```

Если полноценный E2E framework ещё отсутствует и его добавление значительно увеличивает scope — описать manual smoke вместо тяжёлого dependency.

---

# 54. Manual Acceptance

Обязательный manual acceptance:

## Startup

- backend starts;
- frontend starts;
- application opens without console-breaking errors.

## Dashboard

- system status loads;
- providers visible;
- agents visible;
- recent events appear.

## Navigation

- all routes open;
- refresh on nested route works.

## Runs

- agent run starts;
- run workspace opens;
- status updates;
- events arrive through WebSocket;
- run can be stopped.

## Approvals

- approval request visible;
- approve works;
- reject works;
- UI updates without reload.

## Permissions

- unauthorized action blocked;
- backend denial rendered correctly.

## Remote Disabled

- remote control disabled state displayed correctly.

## Error Handling

- backend unavailable state;
- WebSocket unavailable state;
- malformed response does not crash app.

## Responsive

Check at minimum:

```text
desktop
tablet
mobile
```

---

# 55. Security Requirements

Обязательные правила:

- no provider secrets in frontend;
- no secrets in build output;
- no secrets in localStorage;
- no authorization bypass in UI;
- backend remains security authority;
- escaped/safe event payload rendering;
- no `dangerouslySetInnerHTML` for runtime/provider output unless strict sanitization exists;
- no credentials in URL/query string;
- no logging secrets.

---

# 56. Secret Redaction

Backend уже выполняет secret-key redaction.

Frontend всё равно не должен считать arbitrary event payload безопасным.

Не рендерить неизвестные данные как HTML.

Рендерить как text/JSON.

---

# 57. Performance

Не проводить premature optimization.

Но соблюдать:

- bounded event history;
- no unnecessary full-page rerenders;
- lazy routes допустимы;
- event stream updates должны быть granular;
- большие JSON payload не рендерить раскрытыми постоянно.

---

# 58. Logging

Frontend logging должен быть минимальным.

Допустимо:

```text
connection failure
API errors
invalid event schema
```

Не логировать:

```text
secrets
authorization headers
full sensitive payloads
```

---

# 59. Documentation

Создать или обновить:

```text
docs/architecture/VISUAL_INTERFACE.md
docs/agent-rules/VISUAL_INTERFACE.md
```

При необходимости:

```text
docs/PHASE_4_MANUAL_ACCEPTANCE.md
```

Обновить:

```text
AGENTS.md
docs/ARCHITECTURE.md
docs/ROADMAP.md
docs/PROJECT_STATUS.md
.env.example
```

---

# 60. Architecture Documentation

`docs/architecture/VISUAL_INTERFACE.md` должна описывать:

- frontend architecture;
- API boundary;
- WebSocket lifecycle;
- state ownership;
- permission model;
- routing;
- deployment model;
- PWA foundation;
- security boundaries.

---

# 61. Agent Rules

`docs/agent-rules/VISUAL_INTERFACE.md` должна содержать правила для будущих AI coding agents.

Минимально:

```text
Frontend MUST use /api/v1.
Frontend MUST NOT access runtime internals.

Frontend MUST treat backend as authorization authority.

Frontend MUST NOT store provider secrets.

Frontend MUST use normalized remote events.

Frontend MUST NOT create alternate run lifecycle semantics.

Frontend MUST NOT invent backend capabilities.

Frontend MUST remain transport-neutral.

Frontend MUST preserve mobile/browser compatibility.

Frontend MUST keep event history bounded.
```

---

# 62. AGENTS.md

Добавить ссылку на visual interface rules.

Например:

```text
For frontend/browser/visual interface work:
read docs/agent-rules/VISUAL_INTERFACE.md
```

Не копировать весь документ внутрь `AGENTS.md`.

---

# 63. ROADMAP

Обновить Phase 4:

```text
Phase 4 — Visual Interface
```

После завершения перечислить:

- browser UI;
- API client;
- live event stream;
- run workspace;
- approvals UI;
- provider visibility;
- responsive layout;
- PWA foundation.

---

# 64. PROJECT_STATUS

После успешной проверки добавить:

```text
Phase 4 — PASS
```

и краткий completion summary.

---

# 65. Scope Boundaries

Phase 4 НЕ должна включать полноценную реализацию:

- Telegram bot;
- WhatsApp integration;
- Discord integration;
- Slack integration;
- native Android application;
- native iOS application;
- production credential issuer;
- OAuth;
- SSO;
- durable approval database;
- full runtime pause/resume redesign;
- cloud deployment platform;
- collaborative multi-user editing;
- billing;
- marketplace;
- plugin marketplace.

Это отдельные последующие фазы.

---

# 66. Remote Messaging Future Compatibility

Несмотря на то что Telegram/Discord/etc. не входят в Phase 4, frontend не должен создавать специальные команды, доступные только браузеру.

Браузер должен использовать тот же conceptual command layer, который позже смогут использовать:

```text
Web
Telegram
Discord
Slack
WhatsApp
TUI
CLI
```

Принцип:

```text
Different transport
Same AgentGraph commands
Same authorization
Same runtime
Same events
```

---

# 67. TUI Future Compatibility

TUI не входит в текущую фазу.

Но нельзя переносить domain logic исключительно во frontend.

Вся бизнес-логика должна оставаться reusable через backend API/services.

Это позволит позже создать:

```text
AgentGraph TUI
```

поверх тех же контрактов.

---

# 68. UX Priority Order

При конфликте требований использовать порядок:

```text
Correctness
→ Security
→ Runtime visibility
→ Reliability
→ Usability
→ Visual polish
→ Animation
```

---

# 69. Definition of Done

Phase 4 считается завершённой, только если:

- browser UI существует;
- UI запускается штатной командой проекта;
- Dashboard работает;
- Projects работают;
- Agents работают;
- Run Workspace работает;
- run можно запустить;
- run можно остановить;
- `/ws/events` используется реально;
- события отображаются live;
- approvals отображаются;
- approve/reject работают;
- providers отображаются;
- backend errors нормализованно показываются;
- permission restrictions отражены в UI;
- remote control disabled state обработан;
- secrets не попадают во frontend;
- responsive layout работает;
- frontend typecheck проходит;
- lint/check проходит;
- tests проходят;
- backend tests продолжают проходить;
- architecture docs обновлены;
- agent rules обновлены;
- roadmap обновлён;
- project status обновлён;
- manual smoke выполнен.

---

# 70. Required Verification

Перед объявлением Phase 4 завершённой обязательно выполнить реальные проверки проекта.

Минимум:

```bash
pnpm check
```

или эквивалент существующего frontend validation pipeline.

Backend:

```bash
ruff check .
mypy ...
pytest
```

Использовать реальные команды текущего repository.

Не придумывать команды, если структура проекта отличается.

Также выполнить production frontend build.

Пример:

```bash
pnpm build
```

---

# 71. Regression Requirement

Все существующие Phase 1–3 и Remote Interface Foundation tests должны продолжать проходить.

Phase 4 не имеет права менять существующие backend contracts без необходимости.

Если контракт действительно требуется изменить:

1. объяснить причину;
2. сохранить backward compatibility, если возможно;
3. добавить tests;
4. обновить architecture documentation.

---

# 72. Final Review

После реализации выполнить отдельный review.

Проверить:

### Architecture

- UI не связан напрямую с runtime internals;
- API boundary соблюдён;
- WebSocket abstraction существует;
- frontend не дублирует backend business logic.

### Security

- secrets отсутствуют;
- permissions соблюдаются;
- authorization не перенесена во frontend.

### UX

- основные действия доступны;
- errors понятны;
- loading states присутствуют;
- mobile usable.

### Quality

- no obvious dead code;
- no duplicate components;
- no unused experimental dependencies;
- type safety preserved.

---

# 73. Completion Report Format

После завершения OpenCode должен выдать отчёт строго в следующем формате:

```text
Phase 4 — Visual Interface Completion Report

Status
PASS / PARTIAL / FAIL

Implemented
- ...

Files Created
- ...

Files Modified
- ...

Routes Added
- ...

UI Features
- ...

API Integration
- ...

WebSocket Integration
- ...

Authorization / Security
- ...

Tests
- ...

Verification
- pnpm check:
- frontend build:
- Ruff:
- mypy:
- pytest:
- browser smoke:

Manual Acceptance
- ...

Deferred Intentionally
- ...

Known Limitations
- ...

New Dependencies
- ...

Architecture Review
- ...

Next Recommended Task
- ...
```

Не писать `PASS`, если обязательные проверки реально не выполнялись.

Если часть проверки невозможна из-за окружения, использовать:

```text
NOT RUN
```

с конкретной причиной.

---

# 74. Implementation Order

OpenCode должен выполнять Phase 4 в следующем порядке.

## Step 1 — Repository Inspection

Перед изменением кода:

- прочитать `AGENTS.md`;
- прочитать architecture docs;
- прочитать remote interface rules;
- определить существующий frontend stack;
- определить существующие scripts;
- изучить `/api/v1` schemas;
- изучить WebSocket events;
- изучить permission model.

Не начинать переписывание проекта до inspection.

---

## Step 2 — Frontend Foundation

Реализовать:

- app shell;
- routing;
- API client;
- TypeScript contracts;
- error normalization;
- design tokens;
- base UI components.

Проверить build.

---

## Step 3 — Connection Layer

Реализовать:

- REST connection status;
- WebSocket client;
- reconnect;
- bounded events;
- normalized event handling.

Покрыть tests.

---

## Step 4 — Dashboard

Подключить реальные:

- system;
- providers;
- agents;
- runs;
- approvals;
- events.

Не использовать fake production data.

---

## Step 5 — Projects and Agents

Реализовать реальные views поверх существующих API.

---

## Step 6 — Run Workspace

Реализовать:

- start;
- status;
- metadata;
- live events;
- output;
- stop.

Это ключевой milestone Phase 4.

---

## Step 7 — Approvals

Реализовать:

- pending approvals;
- approval details;
- approve;
- reject;
- event-driven refresh.

---

## Step 8 — Providers

Реализовать provider/model visibility.

---

## Step 9 — Responsive / PWA Foundation

Проверить:

- desktop;
- tablet;
- mobile.

Добавить PWA foundation только без нарушения стабильности.

---

## Step 10 — Tests

Добавить unit/integration tests для критической frontend логики.

---

## Step 11 — Documentation

Обновить:

- architecture;
- rules;
- roadmap;
- project status;
- environment docs.

---

## Step 12 — Full Verification

Запустить весь relevant validation suite.

Исправить найденные regression.

---

## Step 13 — Independent Review

Провести финальный review implementation относительно этой спецификации.

Исправить blocking issues.

Только после этого отмечать Phase 4 как PASS.

---

# 75. Execution Rules for OpenCode

OpenCode должен работать автономно в рамках этой Phase.

Не останавливаться после создания skeleton.

Не считать наличие страниц без API integration завершением задачи.

Не заменять реальные backend contracts mock данными в production code.

Не спрашивать пользователя о мелких implementation decisions, если решение однозначно следует из repository architecture.

При неизвестности:

1. изучить repository;
2. изучить текущие patterns;
3. выбрать наиболее совместимое минимальное решение;
4. документировать значимое архитектурное решение.

Если обнаружена проблема в существующем backend, мешающая Phase 4:

- исправить её только если изменение локальное и архитектурно очевидное;
- добавить regression test;
- описать изменение в completion report.

Если требуется значительный redesign backend — не скрывать это внутри Phase 4. Зафиксировать как blocker или отдельную следующую задачу.

---

# Final Objective

После завершения Phase 4 AgentGraph OS должен впервые стать практически используемым через браузер как единая визуальная рабочая среда:

```text
User
 ↓
AgentGraph Visual Interface
 ↓
Versioned Remote API
 ↓
Authorization
 ↓
Agent Runtime
 ↓
Model Router / Providers
 ↓
Live Events
 ↓
Visual Interface
```

Пользователь должен видеть состояние системы, запускать агентов, наблюдать выполнение задач в реальном времени, управлять run lifecycle и обрабатывать approval requests без прямой работы с backend или терминалом.

При этом Visual Interface должен оставаться только одним из transport clients AgentGraph OS, чтобы последующие Web/PWA, TUI, Telegram, Discord, Slack и другие интерфейсы могли использовать те же команды, permissions и события.
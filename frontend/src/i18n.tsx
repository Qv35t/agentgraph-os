import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

export type Locale = "en" | "ru";

const copy = {
  en: {
    nav: { dashboard: "Dashboard", projects: "Projects", agents: "Agents", approvals: "Approvals", providers: "Providers", vision: "Vision", lexi: "Lexi", nodes: "Nodes", events: "Events", settings: "Settings", help: "Help" },
    shell: { eyebrow: "LOCAL CONTROL PLANE", workspace: "Agent workspace", events: "Events", retry: "Retry", language: "Language", collapse: "Collapse navigation", toggle: "Toggle navigation" },
    help: {
      eyebrow: "OPERATOR GUIDE", title: "Help and operating guide", intro: "AgentGraph OS is a local control plane. The backend remains the source of truth for runs, approvals, providers, and vision data.",
      sections: [
        ["Dashboard", "Check API, remote control, provider, agent, approval, and live event state. Use it first to identify a disconnected backend or unavailable provider."],
        ["Projects", "Open the local project identity, its agents, and recent project activity. Project CRUD is not exposed by the current backend."],
        ["Agents", "Create an agent, choose a discovered model route, arrange and save its graph metadata, then open the agent to start a task. A running agent cannot start a second run."],
        ["Approvals", "Review the requested action, related run, and task before approving or rejecting. Approval persistence is process-local and does not pause a run yet."],
        ["Providers", "Inspect safe provider availability, discovered models, capabilities, and normalized errors. Credentials are never shown here."],
        ["Vision", "Upload JPEG, PNG, or WEBP files, select an analysis mode, and inspect persisted history. Register only folders under server-approved roots. Vision observes; it never controls the computer."],
        ["Events", "Filter the bounded live event history by event type, run ID, or agent ID. Expand payloads only when needed; payloads are text/JSON, not executable content."],
        ["Settings", "View server capabilities and connection state. Backend secrets, provider credentials, and server configuration are intentionally not editable from the browser."],
      ],
      safetyTitle: "Permissions and safety", safety: "Buttons provide guidance only. The backend authorizes every request. If remote control is disabled or your identity lacks a permission, read the server error instead of retrying with another identity.",
    },
    lexi: {
      eyebrow: "LOCAL ASSISTANT", title: "Lexi workspace", loading: "Loading Lexi workspace...", bootstrapTitle: "Install Lexi", bootstrapDescription: "Lexi is not installed yet. Install the normal AgentGraph workflow before starting a task.", bootstrap: "Install Lexi", bootstrapping: "Installing Lexi...", installed: "Lexi is installed as a normal AgentGraph workflow.", provider: "Model route", providers: "Available providers", noProviders: "No provider is currently available.", composer: "Ask Lexi", task: "Task", taskPlaceholder: "Describe the task for Lexi.", start: "Start run", starting: "Starting run...", cancel: "Cancel run", cancelling: "Requesting cancellation...", cancelPending: "Cancellation is awaiting server confirmation.", output: "Output", noOutput: "Execution output will appear when the backend reports it.", fullRun: "Open full run", recentRuns: "Recent runs", noRuns: "No Lexi runs yet.", memory: "Scoped memory", memoryEmpty: "No scoped memory records yet.", memoryKind: "Kind", memoryContent: "Memory content", memoryTags: "Tags", memoryTagsPlaceholder: "comma, separated", addMemory: "Add memory", addingMemory: "Adding memory...", deleteMemory: "Delete memory", deletingMemory: "Deleting memory...", injectedMemory: "Injected memory", noInjectedMemory: "No memory was injected for this run.", deletedMemory: "deleted", toolActivity: "Tool activity", noTools: "No tool activity for this run.", pendingApproval: "A controlled action is awaiting approval.", pendingApprovals: "Controlled actions are awaiting approval.", openApprovals: "Open approvals", retry: "Retry", error: "Lexi workspace could not load.", selectedRun: "Selected run", milliseconds: "ms", kinds: { fact: "Fact", preference: "Preference", note: "Note", summary: "Summary" },
    },
  },
  ru: {
    nav: { dashboard: "Панель", projects: "Проекты", agents: "Агенты", approvals: "Подтверждения", providers: "Провайдеры", vision: "Зрение", lexi: "Lexi", nodes: "Узлы", events: "События", settings: "Настройки", help: "Помощь" },
    shell: { eyebrow: "ЛОКАЛЬНАЯ ПАНЕЛЬ УПРАВЛЕНИЯ", workspace: "Рабочее пространство", events: "События", retry: "Повторить", language: "Язык", collapse: "Свернуть навигацию", toggle: "Открыть навигацию" },
    help: {
      eyebrow: "РУКОВОДСТВО ОПЕРАТОРА", title: "Помощь и руководство", intro: "AgentGraph OS — локальная панель управления. Backend остаётся источником истины для run, подтверждений, провайдеров и данных Vision.",
      sections: [
        ["Панель", "Проверяйте API, remote control, провайдеры, агентов, подтверждения и поток событий. Начинайте с неё, чтобы обнаружить недоступный backend или провайдер."],
        ["Проекты", "Открывайте идентификатор локального проекта, его агентов и последние события. CRUD проектов текущий backend не предоставляет."],
        ["Агенты", "Создайте агента, выберите найденный model route, разместите и сохраните метаданные графа, затем откройте агента для запуска задачи. Запущенный агент не может начать второй run."],
        ["Подтверждения", "Проверьте запрошенное действие, связанный run и задачу перед подтверждением или отклонением. Подтверждения пока process-local и не приостанавливают run."],
        ["Провайдеры", "Просматривайте безопасные сведения о доступности провайдеров, моделях, возможностях и нормализованных ошибках. Учётные данные здесь не отображаются."],
        ["Зрение", "Загружайте JPEG, PNG или WEBP, выбирайте режим анализа и просматривайте сохранённую историю. Регистрируйте только папки из разрешённых сервером roots. Vision наблюдает и не управляет компьютером."],
        ["События", "Фильтруйте ограниченную live-историю по типу, ID run или ID агента. Раскрывайте payload только при необходимости: это текст/JSON, а не исполняемый контент."],
        ["Настройки", "Просматривайте возможности сервера и состояние соединения. Секреты, credentials провайдеров и настройки сервера намеренно не изменяются из браузера."],
      ],
      safetyTitle: "Права и безопасность", safety: "Кнопки дают только UX-подсказки. Каждый запрос авторизуется backend. Если remote control отключён или у identity нет права, прочитайте ошибку сервера, а не пытайтесь обойти её другой identity.",
    },
    lexi: {
      eyebrow: "ЛОКАЛЬНЫЙ АССИСТЕНТ", title: "Рабочее пространство Lexi", loading: "Загрузка рабочего пространства Lexi...", bootstrapTitle: "Установить Lexi", bootstrapDescription: "Lexi ещё не установлена. Установите обычный workflow AgentGraph перед запуском задачи.", bootstrap: "Установить Lexi", bootstrapping: "Установка Lexi...", installed: "Lexi установлена как обычный workflow AgentGraph.", provider: "Маршрут модели", providers: "Доступные провайдеры", noProviders: "Сейчас нет доступных провайдеров.", composer: "Задать вопрос Lexi", task: "Задача", taskPlaceholder: "Опишите задачу для Lexi.", start: "Запустить run", starting: "Запуск run...", cancel: "Отменить run", cancelling: "Запрос отмены...", cancelPending: "Отмена ожидает подтверждения сервера.", output: "Результат", noOutput: "Результат появится, когда backend сообщит о выполнении.", fullRun: "Открыть полный run", recentRuns: "Последние run", noRuns: "Запусков Lexi пока нет.", memory: "Изолированная память", memoryEmpty: "Изолированных записей памяти пока нет.", memoryKind: "Тип", memoryContent: "Содержимое памяти", memoryTags: "Теги", memoryTagsPlaceholder: "через, запятую", addMemory: "Добавить память", addingMemory: "Добавление памяти...", deleteMemory: "Удалить память", deletingMemory: "Удаление памяти...", injectedMemory: "Внедрённая память", noInjectedMemory: "Для этого run память не внедрялась.", deletedMemory: "удалено", toolActivity: "Активность инструментов", noTools: "Для этого run нет активности инструментов.", pendingApproval: "Управляемое действие ожидает подтверждения.", pendingApprovals: "Управляемые действия ожидают подтверждения.", openApprovals: "Открыть подтверждения", retry: "Повторить", error: "Не удалось загрузить рабочее пространство Lexi.", selectedRun: "Выбранный run", milliseconds: "мс", kinds: { fact: "Факт", preference: "Предпочтение", note: "Заметка", summary: "Сводка" },
    },
  },
} as const;

type Translation = (typeof copy)[Locale];
type LanguageContextValue = { locale: Locale; setLocale: (locale: Locale) => void; text: Translation };
const LanguageContext = createContext<LanguageContextValue | null>(null);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [locale, setLocale] = useState<Locale>(() => localStorage.getItem("agentgraph.locale") === "ru" ? "ru" : "en");
  useEffect(() => { localStorage.setItem("agentgraph.locale", locale); document.documentElement.lang = locale; }, [locale]);
  return <LanguageContext.Provider value={{ locale, setLocale, text: copy[locale] }}>{children}</LanguageContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useLanguage(): LanguageContextValue {
  const context = useContext(LanguageContext);
  if (!context) throw new Error("LanguageProvider is required");
  return context;
}

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

export type Locale = "en" | "ru";

const copy = {
  en: {
    nav: { dashboard: "Dashboard", projects: "Projects", agents: "Agents", approvals: "Approvals", providers: "Providers", vision: "Vision", events: "Events", settings: "Settings", help: "Help" },
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
  },
  ru: {
    nav: { dashboard: "Панель", projects: "Проекты", agents: "Агенты", approvals: "Подтверждения", providers: "Провайдеры", vision: "Зрение", events: "События", settings: "Настройки", help: "Помощь" },
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

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { LanguageProvider, useLanguage } from "./i18n";

function Probe() {
  const { locale, setLocale, text } = useLanguage();
  return <><span>{text.nav.help}</span><button onClick={() => setLocale(locale === "en" ? "ru" : "en")}>switch</button></>;
}

describe("language preference", () => {
  it("switches the UI copy between English and Russian", () => {
    render(<LanguageProvider><Probe /></LanguageProvider>);
    expect(screen.getByText("Help")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "switch" }));
    expect(screen.getByText("Помощь")).toBeInTheDocument();
  });
});

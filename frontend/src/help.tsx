import { BookOpen, ShieldCheck } from "lucide-react";
import { useLanguage } from "./i18n";

export function HelpPage() {
  const { text } = useLanguage();
  return <section className="page"><div className="page-heading"><div><span className="eyebrow">{text.help.eyebrow}</span><h2>{text.help.title}</h2></div></div><p className="help-intro">{text.help.intro}</p><div className="help-grid">{text.help.sections.map(([title, description]) => <article className="help-card" key={title}><BookOpen size={18} /><h3>{title}</h3><p>{description}</p></article>)}</div><section className="help-safety"><ShieldCheck size={20} /><div><h3>{text.help.safetyTitle}</h3><p>{text.help.safety}</p></div></section></section>;
}

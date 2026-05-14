type SectionLabelProps = {
  eyebrow?: string;
  title: string;
  description?: string;
};

export function SectionLabel({ eyebrow, title, description }: SectionLabelProps) {
  return (
    <div>
      {eyebrow ? <p className="text-xs font-semibold uppercase tracking-[0.14em] text-northbound-textMuted">{eyebrow}</p> : null}
      <h2 className="mt-1 text-base font-semibold text-northbound-text">{title}</h2>
      {description ? <p className="mt-1 text-sm text-northbound-textMuted">{description}</p> : null}
    </div>
  );
}

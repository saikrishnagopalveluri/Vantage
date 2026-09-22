import Link from "next/link";
import type { ButtonHTMLAttributes, ReactNode, Ref } from "react";

export const cx = (...parts: (string | false | null | undefined)[]) => parts.filter(Boolean).join(" ");

type Variant = "primary" | "secondary" | "ghost";

const VARIANTS: Record<Variant, string> = {
  primary: "btn-primary",
  secondary: "btn-raised text-ink",
  ghost: "border border-transparent bg-transparent text-muted hover:text-ink",
};

const BASE =
  "inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-4 text-[15px] font-semibold disabled:cursor-not-allowed disabled:opacity-50";

export function Button({
  variant = "secondary",
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; ref?: Ref<HTMLButtonElement> }) {
  return <button {...props} className={cx(BASE, VARIANTS[variant], className)} />;
}

export function LinkButton({
  href,
  variant = "secondary",
  className,
  children,
}: {
  href: string;
  variant?: Variant;
  className?: string;
  children: ReactNode;
}) {
  return (
    <Link href={href} className={cx(BASE, VARIANTS[variant], className)}>
      {children}
    </Link>
  );
}

export function Chip({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "accent" | "good";
}) {
  const tones = {
    neutral: "border border-line text-muted",
    accent: "bg-accent-soft text-accent",
    good: "bg-good-soft text-good",
  };
  return (
    <span className={cx("inline-flex items-center rounded-md px-2.5 py-0.5 text-xs font-medium", tones[tone])}>
      {children}
    </span>
  );
}

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return <section className={cx("raised rounded-2xl p-4 md:p-5", className)}>{children}</section>;
}

export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden className={cx("skeleton rounded-lg", className)} />;
}

export function EmptyState({
  title,
  children,
  action,
}: {
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="rise rounded-2xl border border-dashed border-line px-6 py-10 text-center">
      <h2 className="font-display text-xl">{title}</h2>
      {children && <p className="mx-auto mt-2 max-w-md text-[15px] text-muted">{children}</p>}
      {action && <div className="mt-5 flex justify-center">{action}</div>}
    </div>
  );
}

export function ErrorNotice({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="raised rounded-2xl p-4 text-[15px]">
      <p>{message}</p>
      {onRetry && (
        <Button className="mt-3" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}

export function PageHeader({
  title,
  subtitle,
  eyebrow,
}: {
  title: string;
  subtitle?: ReactNode;
  eyebrow?: string;
}) {
  return (
    <header className="mb-6 mt-2">
      {eyebrow && <p className="mb-1 font-mono text-xs text-muted">{eyebrow}</p>}
      <h1 className="font-display text-[30px] leading-[1.1] md:text-[38px]">{title}</h1>
      {subtitle && <p className="mt-2 max-w-xl text-[15px] leading-relaxed text-muted">{subtitle}</p>}
    </header>
  );
}

/** A recessed track with a thumb that slides to the chosen segment. */
export function Segmented<T extends string>({
  options,
  value,
  onChange,
  label,
}: {
  options: { id: T; label: string }[];
  value: T;
  onChange: (id: T) => void;
  label: string;
}) {
  const index = Math.max(0, options.findIndex((o) => o.id === value));
  return (
    <div
      role="tablist"
      aria-label={label}
      className="seg"
      style={{ "--count": options.length, "--i": index } as React.CSSProperties}
    >
      <span className="seg-thumb" aria-hidden />
      {options.map((o) => (
        <button
          key={o.id}
          role="tab"
          aria-selected={value === o.id}
          onClick={() => onChange(o.id)}
          className={cx(
            "min-h-10 rounded-[10px] px-2 text-[15px] font-semibold transition-colors",
            value === o.id ? "text-ink" : "text-muted hover:text-ink",
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

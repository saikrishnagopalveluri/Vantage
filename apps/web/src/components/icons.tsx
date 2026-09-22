import type { SVGProps } from "react";

type P = SVGProps<SVGSVGElement>;
const base = (props: P) => ({
  width: 22,
  height: 22,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.75,
  strokeLinecap: "square" as const,
  strokeLinejoin: "miter" as const,
  "aria-hidden": true,
  ...props,
});

export const FeedIcon = (p: P) => (
  <svg {...base(p)}>
    <path d="M4 5h16M4 10h16M4 15h10M4 20h7" />
  </svg>
);
export const CareerIcon = (p: P) => (
  <svg {...base(p)}>
    <path d="M4 20V10M10 20V4M16 20v-7M22 20H2" />
  </svg>
);
export const BookmarkIcon = ({ filled, ...p }: P & { filled?: boolean }) => (
  <svg {...base(p)} fill={filled ? "currentColor" : "none"}>
    <path d="M6 3h12v18l-6-4-6 4z" />
  </svg>
);
export const UserIcon = (p: P) => (
  <svg {...base(p)}>
    <circle cx="12" cy="8" r="4" />
    <path d="M4 21c1-4 4.5-6 8-6s7 2 8 6" />
  </svg>
);
export const CheckIcon = (p: P) => (
  <svg {...base(p)}>
    <path d="M5 12.5l4.5 4.5L19 7.5" />
  </svg>
);
export const CloseIcon = (p: P) => (
  <svg {...base(p)}>
    <path d="M6 6l12 12M18 6L6 18" />
  </svg>
);
export const ExternalIcon = (p: P) => (
  <svg {...base(p)}>
    <path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5" />
  </svg>
);
export const ShareIcon = (p: P) => (
  <svg {...base(p)}>
    <path d="M12 15V3M8 7l4-4 4 4M5 11v9h14v-9" />
  </svg>
);

export const SearchIcon = (p: P) => (
  <svg {...base(p)}>
    <circle cx="11" cy="11" r="6.5" />
    <path d="M16 16l4.5 4.5" />
  </svg>
);
export const CompassIcon = (p: P) => (
  <svg {...base(p)}>
    <circle cx="12" cy="12" r="9" />
    <path d="M15.5 8.5l-2 5-5 2 2-5z" />
  </svg>
);
export const SunIcon = (p: P) => (
  <svg {...base(p)}>
    <circle cx="12" cy="12" r="4" />
    <path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M5.6 18.4L7 17M17 7l1.4-1.4" />
  </svg>
);
export const MoonIcon = (p: P) => (
  <svg {...base(p)}>
    <path d="M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5z" />
  </svg>
);
export const ArrowIcon = (p: P) => (
  <svg {...base(p)}>
    <path d="M5 12h14M13 6l6 6-6 6" />
  </svg>
);
export const ChevronIcon = (p: P) => (
  <svg {...base(p)}>
    <path d="M6 9l6 6 6-6" />
  </svg>
);
export const TrashIcon = (p: P) => (
  <svg {...base(p)}>
    <path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3" />
  </svg>
);
export const PlusIcon = (p: P) => (
  <svg {...base(p)}>
    <path d="M12 5v14M5 12h14" />
  </svg>
);
export const LightningIcon = (p: P) => (
  <svg {...base(p)}>
    <path d="M13 3L4 14h6l-1 7 9-11h-6z" />
  </svg>
);
export const GamesIcon = (p: P) => (
  <svg {...base(p)}>
    <rect x="3" y="3" width="8.5" height="8.5" rx="1.5" />
    <rect x="12.5" y="12.5" width="8.5" height="8.5" rx="1.5" />
    <circle cx="6" cy="6" r="0.9" fill="currentColor" stroke="none" />
    <circle cx="9" cy="9" r="0.9" fill="currentColor" stroke="none" />
    <circle cx="15" cy="15" r="0.9" fill="currentColor" stroke="none" />
    <circle cx="19" cy="15" r="0.9" fill="currentColor" stroke="none" />
    <circle cx="15" cy="19" r="0.9" fill="currentColor" stroke="none" />
    <circle cx="19" cy="19" r="0.9" fill="currentColor" stroke="none" />
  </svg>
);

export function Logo({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 512 512" aria-hidden>
      <rect width="512" height="512" rx="118" fill="#1d1a16" />
      <path d="M132 176 L256 388 L380 176" fill="none" stroke="#f59e0b" strokeWidth="46" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="256" cy="108" r="28" fill="#f59e0b" />
    </svg>
  );
}

export const SpeakerIcon = (p: P) => (
  <svg {...base(p)}>
    <path d="M4 9.5v5h3.5L12 18.5v-13L7.5 9.5z" />
    <path d="M15.5 9a4 4 0 010 6M18 6.5a7.5 7.5 0 010 11" />
  </svg>
);
export const PauseIcon = (p: P) => (
  <svg {...base(p)}>
    <path d="M9 5v14M15 5v14" />
  </svg>
);
export const StopIcon = (p: P) => (
  <svg {...base(p)}>
    <rect x="6" y="6" width="12" height="12" rx="1.5" />
  </svg>
);

export const HeartIcon = ({ filled, ...p }: P & { filled?: boolean }) => (
  <svg {...base(p)} fill={filled ? "currentColor" : "none"}>
    <path d="M12 20.5s-7.5-4.6-7.5-10.2A4.3 4.3 0 0112 7.6a4.3 4.3 0 017.5 2.7c0 5.6-7.5 10.2-7.5 10.2z" />
  </svg>
);
export const MuteIcon = (p: P) => (
  <svg {...base(p)}>
    <path d="M4 9.5v5h3.5L12 18.5v-13L7.5 9.5z" />
    <path d="M16 9.5l5 5M21 9.5l-5 5" />
  </svg>
);
export const DownloadIcon = (p: P) => (
  <svg {...base(p)}>
    <path d="M12 4v11M8 11l4 4 4-4M5 19h14" />
  </svg>
);
export const CopyIcon = (p: P) => (
  <svg {...base(p)}>
    <rect x="8" y="8" width="11" height="12" rx="2" />
    <path d="M5 15V6a2 2 0 012-2h8" />
  </svg>
);

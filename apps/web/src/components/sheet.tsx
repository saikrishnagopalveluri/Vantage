"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { CloseIcon } from "./icons";

/** Modal built on <dialog>: focus trapping, Esc to close and inert background come for free. */
export function Sheet({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      aria-labelledby="sheet-title"
      onClose={onClose}
      onClick={(e) => e.target === ref.current && onClose()}
      className="fixed inset-x-0 bottom-0 top-auto m-0 max-h-[92dvh] w-full max-w-none overflow-y-auto rounded-t-3xl border border-line bg-surface p-0 text-ink md:inset-auto md:m-auto md:max-w-lg md:rounded-3xl"
    >
      {open && (
        <div className="pb-safe p-5 md:p-6">
          <div className="mb-4 flex items-start justify-between gap-4">
            <h2 id="sheet-title" className="font-display text-2xl">
              {title}
            </h2>
            <button
              onClick={onClose}
              aria-label="Close"
              className="-mr-2 -mt-1 flex size-11 items-center justify-center rounded-full text-muted hover:text-ink"
            >
              <CloseIcon />
            </button>
          </div>
          {children}
        </div>
      )}
    </dialog>
  );
}

import { useEffect, useRef, useState } from "react";

/** A small "?" badge next to a technical term. Click it to reveal a
 * plain-language explanation inline — closed by default, so the page
 * reads simply at a glance, but nothing technical is hidden from anyone
 * who wants the detail. */
export default function InfoTip({ children }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return;
    function onClickOutside(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, [open]);

  return (
    <span className="infotip" ref={ref}>
      <button
        type="button"
        className="infotip__trigger"
        aria-expanded={open}
        aria-label="What does this mean?"
        onClick={() => setOpen((v) => !v)}
      >
        ?
      </button>
      {open && (
        <span className="infotip__panel" role="tooltip">
          {children}
        </span>
      )}
    </span>
  );
}

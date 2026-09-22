import { useEffect, useState } from "react";

/** Animates a number from 0 to `target` over `duration` ms. Used for
 * headline stats so the page feels alive on load rather than static. */
export function useCountUp(target, duration = 700) {
  const [value, setValue] = useState(0);

  useEffect(() => {
    if (target == null || Number.isNaN(target)) return;
    let start = null;
    let raf;
    function tick(ts) {
      if (start === null) start = ts;
      const progress = Math.min(1, (ts - start) / duration);
      const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
      setValue(target * eased);
      if (progress < 1) raf = requestAnimationFrame(tick);
    }
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, duration]);

  return value;
}

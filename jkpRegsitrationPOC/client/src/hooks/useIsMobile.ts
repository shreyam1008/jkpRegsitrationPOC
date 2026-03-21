import { useSyncExternalStore } from "react";
import { MOBILE_BREAKPOINT } from "@/constants";

const QUERY = `(max-width: ${MOBILE_BREAKPOINT - 1}px)`;

const mql =
  typeof window !== "undefined" ? window.matchMedia(QUERY) : null;

function subscribe(cb: () => void) {
  if (!mql) return () => {};
  mql.addEventListener("change", cb);
  return () => mql.removeEventListener("change", cb);
}

function getSnapshot() {
  return mql?.matches ?? false;
}

export function useIsMobile() {
  return useSyncExternalStore(subscribe, getSnapshot, () => false);
}

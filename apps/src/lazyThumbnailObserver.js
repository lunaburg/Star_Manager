const callbacks = new WeakMap();
let sharedObserver = null;

function getSharedObserver() {
  if (sharedObserver || typeof window === "undefined" || !("IntersectionObserver" in window)) {
    return sharedObserver;
  }
  sharedObserver = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        const callback = callbacks.get(entry.target);
        sharedObserver.unobserve(entry.target);
        callbacks.delete(entry.target);
        callback?.();
      }
    },
    { root: null, rootMargin: "180px", threshold: 0.01 }
  );
  return sharedObserver;
}

export function observeLazyThumbnail(element, onVisible) {
  const observer = getSharedObserver();
  if (!observer || !element) return false;
  callbacks.set(element, onVisible);
  observer.observe(element);
  return true;
}

export function unobserveLazyThumbnail(element) {
  if (!element || !sharedObserver) return;
  sharedObserver.unobserve(element);
  callbacks.delete(element);
}

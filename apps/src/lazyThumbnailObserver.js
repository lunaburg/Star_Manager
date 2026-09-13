const callbacks = new WeakMap();
const registrations = new WeakMap();
const observerRecords = new Map();

function findScrollRoot(element) {
  if (typeof window === "undefined") return null;
  let parent = element?.parentElement || null;
  while (parent) {
    const styles = window.getComputedStyle(parent);
    const overflow = `${styles.overflowY} ${styles.overflow}`;
    if (/(auto|scroll|overlay)/i.test(overflow)) return parent;
    parent = parent.parentElement;
  }
  return null;
}

function getObserver(root) {
  if (typeof window === "undefined" || !("IntersectionObserver" in window)) return null;
  const key = root || null;
  const existing = observerRecords.get(key);
  if (existing) return existing;

  const record = {
    count: 0,
    observer: new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue;
          const target = entry.target;
          const callback = callbacks.get(target);
          releaseRegistration(target);
          callback?.();
        }
      },
      // Preload a few rows ahead, but keep far-away items out of the request
      // queue while the user is browsing a large library.
      { root, rootMargin: "360px 0px", threshold: 0.01 }
    ),
    key
  };
  observerRecords.set(key, record);
  return record;
}

function releaseRegistration(element) {
  const registration = registrations.get(element);
  if (!registration) return;
  registration.observer.unobserve(element);
  registration.record.count -= 1;
  registrations.delete(element);
  callbacks.delete(element);
  if (registration.record.count <= 0) {
    registration.record.observer.disconnect();
    observerRecords.delete(registration.record.key);
  }
}

export function observeLazyThumbnail(element, onVisible) {
  if (!element) return false;
  const record = getObserver(findScrollRoot(element));
  if (!record) return false;
  callbacks.set(element, onVisible);
  registrations.set(element, { observer: record.observer, record });
  record.count += 1;
  record.observer.observe(element);
  return true;
}

export function unobserveLazyThumbnail(element) {
  if (!element) return;
  releaseRegistration(element);
}

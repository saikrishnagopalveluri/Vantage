/** Web Push subscribe/unsubscribe helpers. Kept separate from the UI component so the browser-only
 *  bits (service worker, PushManager, base64 keys) are easy to see and to skip on a browser that
 *  doesn't support any of this. */
import { api } from "./api";

export function pushSupported(): boolean {
  return typeof window !== "undefined" && "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
}

// applicationServerKey wants a Uint8Array backed by a plain ArrayBuffer, not the base64url string
// the server hands out (Uint8Array.from's return type isn't narrow enough for that in newer lib.dom).
function urlBase64ToUint8Array(base64: string): Uint8Array<ArrayBuffer> {
  const padding = "=".repeat((4 - (base64.length % 4)) % 4);
  const raw = atob((base64 + padding).replace(/-/g, "+").replace(/_/g, "/"));
  const bytes = new Uint8Array(new ArrayBuffer(raw.length));
  for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);
  return bytes;
}

export async function currentSubscription(): Promise<PushSubscription | null> {
  if (!pushSupported()) return null;
  const registration = await navigator.serviceWorker.ready;
  return registration.pushManager.getSubscription();
}

/** Asks the browser for permission (if not already granted or denied), subscribes with the
 *  server's VAPID key, and registers the subscription for the given categories. Returns false if
 *  push isn't supported here, permission is denied, the server has no VAPID key configured, or the
 *  server rejects the subscription (network error, or this exact device already belongs to a
 *  different profile) — every failure path is a plain false, never a thrown rejection, so the
 *  caller can always show a normal "didn't work" message instead of an unhandled error. */
export async function subscribe(userId: string, categories: string[]): Promise<boolean> {
  if (!pushSupported()) return false;
  if (Notification.permission === "denied") return false;
  if (Notification.permission !== "granted") {
    const permission = await Notification.requestPermission();
    if (permission !== "granted") return false;
  }
  try {
    const { public_key } = await api.pushPublicKey(userId);
    if (!public_key) return false;

    const registration = await navigator.serviceWorker.ready;
    let subscription = await registration.pushManager.getSubscription();
    if (!subscription) {
      subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(public_key),
      });
    }
    const json = subscription.toJSON();
    if (!json.endpoint || !json.keys?.p256dh || !json.keys?.auth) return false;
    await api.pushSubscribe(userId, { endpoint: json.endpoint, keys: { p256dh: json.keys.p256dh, auth: json.keys.auth }, categories });
    return true;
  } catch {
    return false;
  }
}

export async function updateCategories(userId: string, categories: string[]): Promise<boolean> {
  const subscription = await currentSubscription();
  if (!subscription) return false;
  try {
    await api.pushSetCategories(userId, subscription.endpoint, categories);
    return true;
  } catch {
    return false;
  }
}

export async function unsubscribe(userId: string): Promise<void> {
  const subscription = await currentSubscription();
  if (!subscription) return;
  await api.pushUnsubscribe(userId, subscription.endpoint).catch(() => {});
  await subscription.unsubscribe();
}

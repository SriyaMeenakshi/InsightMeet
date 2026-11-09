// Tiny, failure-tolerant wrappers around localStorage / sessionStorage.
const LAST = "insightmeet:last-meeting";
const DRAFT = "insightmeet:hero-draft";

export function getLastMeeting(): string | null {
  try {
    return window.localStorage.getItem(LAST);
  } catch {
    return null;
  }
}

export function setLastMeeting(id: string) {
  try {
    window.localStorage.setItem(LAST, id);
  } catch {
    /* ignore */
  }
}

export function clearLastMeeting(id: string) {
  try {
    if (window.localStorage.getItem(LAST) === id) window.localStorage.removeItem(LAST);
  } catch {
    /* ignore */
  }
}

export function setDraft(text: string) {
  try {
    window.sessionStorage.setItem(DRAFT, text);
  } catch {
    /* ignore */
  }
}

export function takeDraft(): string | null {
  try {
    const v = window.sessionStorage.getItem(DRAFT);
    if (v) window.sessionStorage.removeItem(DRAFT);
    return v;
  } catch {
    return null;
  }
}

/**
 * Normalises a FastAPI error response into a display-safe string.
 *
 * FastAPI `detail` can be:
 *   - string  → simple HTTP exception
 *   - array   → Pydantic v2 validation errors: [{type, loc, msg, input, ctx}]
 *   - object  → custom error shapes
 */
export function getApiError(err: unknown, fallback = "Something went wrong. Please try again."): string {
  // Plain JS/TS Error thrown before the network call (e.g. toPayload() validation)
  if (err instanceof Error && !(err as any).response) {
    return err.message || fallback;
  }

  const detail = (err as any)?.response?.data?.detail;

  if (!detail) return fallback;

  if (typeof detail === "string") return detail;

  if (Array.isArray(detail)) {
    // Pydantic v2: each item has a human-readable "msg" field
    const msgs = detail
      .map((e: any) => {
        if (typeof e === "string") return e;
        if (e?.msg) return String(e.msg);
        return null;
      })
      .filter(Boolean);
    return msgs.length > 0 ? msgs.join(". ") : fallback;
  }

  if (typeof detail === "object") {
    return (detail as any)?.msg ?? (detail as any)?.message ?? fallback;
  }

  return fallback;
}

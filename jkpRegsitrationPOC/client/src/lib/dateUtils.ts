/**
 * Returns today's date as a Temporal.PlainDate.
 */
export function today(): Temporal.PlainDate {
  return Temporal.Now.plainDateISO();
}

/**
 * Formats a Temporal.PlainDate into a human-readable string.
 */
export function formatDate(date: Temporal.PlainDate): string {
  return date.toLocaleString("en-IN", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

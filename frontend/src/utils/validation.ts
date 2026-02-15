/**
 * Validate that a string looks like a valid email address.
 * Checks for: non-empty local part, @, domain with at least one dot.
 */
export function isValidEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

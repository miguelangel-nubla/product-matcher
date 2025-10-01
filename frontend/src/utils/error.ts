/**
 * Centralized error handling utilities
 */

/**
 * Extracts the most useful error message from an API error response
 * @param error - The error object from the API client
 * @returns Human-readable error message
 */
export function getErrorMessage(error: any): string {
  // FastAPI uses 'detail' field for error messages
  if (error?.body?.detail) {
    return error.body.detail
  }
  // Fallback to generic HTTP status if backend doesn't respond
  if (error?.message) {
    return error.message
  }
  return "An unexpected error occurred"
}

/**
 * Checks if an error is a specific HTTP status code
 * @param error - The error object
 * @param status - The HTTP status code to check for
 * @returns True if the error matches the status code
 */
export function isErrorStatus(error: any, status: number): boolean {
  return error?.status === status
}

/**
 * Checks if an error is a network/connection error
 * @param error - The error object
 * @returns True if it's a network error
 */
export function isNetworkError(error: any): boolean {
  return (
    isErrorStatus(error, 503) ||
    isErrorStatus(error, 502) ||
    isErrorStatus(error, 504)
  )
}

/**
 * Checks if an error is an authentication error
 * @param error - The error object
 * @returns True if it's an auth error
 */
export function isAuthError(error: any): boolean {
  return isErrorStatus(error, 401) || isErrorStatus(error, 403)
}

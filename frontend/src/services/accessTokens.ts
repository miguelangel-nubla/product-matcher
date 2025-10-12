import type { CancelablePromise } from "@/client/core/CancelablePromise"
import { OpenAPI } from "@/client/core/OpenAPI"
import { request as __request } from "@/client/core/request"

export interface AccessTokenCreate {
  name: string
  expires_at: string
}

export interface AccessTokenPublic {
  id: string
  name: string
  prefix: string
  is_active: boolean
  expires_at: string
  last_used_at: string | null
  created_at: string
}

export interface AccessTokenCreated {
  token: string
  access_token: AccessTokenPublic
}

export interface AccessTokensPublic {
  data: AccessTokenPublic[]
  count: number
}

export interface Message {
  message: string
}

/**
 * Create Access Token
 * Create a new access token.
 */
export function createAccessToken(data: {
  requestBody: AccessTokenCreate
}): CancelablePromise<AccessTokenCreated> {
  return __request(OpenAPI, {
    method: "POST",
    url: "/api/v1/access-tokens/",
    body: data.requestBody,
    mediaType: "application/json",
    errors: {
      422: "Validation Error",
    },
  })
}

/**
 * Read Access Tokens
 * Retrieve access tokens for the current user.
 */
export function readAccessTokens(
  data: { skip?: number; limit?: number } = {},
): CancelablePromise<AccessTokensPublic> {
  return __request(OpenAPI, {
    method: "GET",
    url: "/api/v1/access-tokens/",
    query: {
      skip: data.skip,
      limit: data.limit,
    },
    errors: {
      422: "Validation Error",
    },
  })
}

/**
 * Read Access Token
 * Get access token by ID.
 */
export function readAccessToken(data: {
  tokenId: string
}): CancelablePromise<AccessTokenPublic> {
  return __request(OpenAPI, {
    method: "GET",
    url: "/api/v1/access-tokens/{token_id}",
    path: {
      token_id: data.tokenId,
    },
    errors: {
      422: "Validation Error",
    },
  })
}

/**
 * Revoke Access Token
 * Revoke an access token.
 */
export function revokeAccessToken(data: {
  tokenId: string
}): CancelablePromise<Message> {
  return __request(OpenAPI, {
    method: "DELETE",
    url: "/api/v1/access-tokens/{token_id}",
    path: {
      token_id: data.tokenId,
    },
    errors: {
      422: "Validation Error",
    },
  })
}

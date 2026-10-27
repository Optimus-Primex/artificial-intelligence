# Error catalogue

Every error response uses the same envelope:

```json
{
  "error": {
    "message": "human readable message",
    "status": 400,
    "request_id": "the request id echoed in the X-Request-ID header",
    "details": "optional, present for validation errors"
  }
}
```

| Status | When | `message` example |
| --- | --- | --- |
| `400 Bad Request` | Unknown `network` value | `unknown network: 'regtest' (expected one of: futurenet, mainnet, testnet)` |
| `401 Unauthorized` | Missing/invalid API key when `STELLAR_AI_API_KEYS` is set | `invalid or missing API key` |
| `422 Unprocessable Entity` | Request body failed validation | `validation error` (with `details`) |
| `429 Too Many Requests` | The client exceeded its per-key/per-IP rate limit | `rate limit exceeded` |
| `502 Bad Gateway` | Horizon, Soroban RPC or the model provider failed | provider message |
| `503 Service Unavailable` | `/ready` when a dependency is down (readiness body, not the error envelope) | `unavailable` |

## Notes

- **`X-Request-ID`** is returned on every response (and accepted from the
  client). It matches `error.request_id`, which makes correlating logs easy.
- `401` responses include a `WWW-Authenticate: Bearer` header.
- `429` responses include `Retry-After` and the `X-RateLimit-Limit`,
  `X-RateLimit-Remaining`, and `X-RateLimit-Reset` headers. Successful
  `/api/` responses include the same `X-RateLimit-*` headers.
- `/health` and `/ready` are never behind authentication and are not rate
  limited.

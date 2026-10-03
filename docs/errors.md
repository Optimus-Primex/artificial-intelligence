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
| `502 Bad Gateway` | Horizon or Soroban RPC could not be reached / returned an error | provider message |
| `503 Service Unavailable` | `/ready` when a dependency is down | `unavailable` |

## Notes

- **`X-Request-ID`** is returned on every response (and accepted from the
  client). It matches `error.request_id`, which makes correlating logs easy.
- `401` responses include a `WWW-Authenticate: Bearer` header.
- `/health` and `/ready` are never behind authentication.

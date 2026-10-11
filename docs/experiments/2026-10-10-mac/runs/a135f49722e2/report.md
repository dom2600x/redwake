# Redwake investigation

Run: `a135f49722e2`

Backend: **baseline** · Lab: **broken** · Status: **completed**

Investigation finished.

| Resource | Verdict | Evidence |
|---|---|---|
| `/api/documents/101` | inconclusive | 1, 2 |
| `/api/invoices/inv_b7` | inconclusive | 4, 3 |
| `/api/documents/public` | inconclusive | 5, 6 |

## Usage

Requests reserved: 6. Model calls reserved: 0. Recorded input/output tokens: 0/0.
Output tokens reserved: 0. Recorded active time: 0.03s.
Provider usage complete: True. Dollar cost is not available from this harness.

## Interpretation

A vulnerable verdict requires the private record to be returned to both its owner and another actor. Protected means the tested cross-account read was denied with an owner success control. Inconclusive never means secure. These results cover only the listed synthetic GET cases.

## Evidence

Requests are GETs against an ephemeral 127.0.0.1 lab. Actor aliases select synthetic lab credentials. The adjacent evidence.json contains the captured responses; replay performs no network requests.

### Evidence 1

```json
{
  "actor": "alice",
  "path": "/api/documents/101",
  "status": 503,
  "body": {
    "error": "unavailable"
  },
  "id": 1
}
```

### Evidence 2

```json
{
  "actor": "bob",
  "path": "/api/documents/101",
  "status": 503,
  "body": {
    "error": "unavailable"
  },
  "id": 2
}
```

### Evidence 3

```json
{
  "actor": "alice",
  "path": "/api/invoices/inv_b7",
  "status": 503,
  "body": {
    "error": "unavailable"
  },
  "id": 3
}
```

### Evidence 4

```json
{
  "actor": "bob",
  "path": "/api/invoices/inv_b7",
  "status": 503,
  "body": {
    "error": "unavailable"
  },
  "id": 4
}
```

### Evidence 5

```json
{
  "actor": "alice",
  "path": "/api/documents/public",
  "status": 503,
  "body": {
    "error": "unavailable"
  },
  "id": 5
}
```

### Evidence 6

```json
{
  "actor": "bob",
  "path": "/api/documents/public",
  "status": 503,
  "body": {
    "error": "unavailable"
  },
  "id": 6
}
```

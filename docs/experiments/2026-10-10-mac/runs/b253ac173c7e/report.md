# Redwake investigation

Run: `b253ac173c7e`

Backend: **ollama** · Lab: **vulnerable** · Status: **stopped**

Model finished without conclusive coverage

| Resource | Verdict | Evidence |
|---|---|---|
| `/api/documents/101` | vulnerable | 1, 2 |
| `/api/invoices/inv_b7` | inconclusive |  |
| `/api/documents/public` | inconclusive |  |

## Usage

Requests reserved: 2. Model calls reserved: 4. Recorded input/output tokens: 2576/974.
Output tokens reserved: 4096. Recorded active time: 7.19s.
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
  "status": 200,
  "body": {
    "owner": "alice",
    "data": "alice-private-document"
  },
  "id": 1
}
```

### Evidence 2

```json
{
  "actor": "bob",
  "path": "/api/documents/101",
  "status": 200,
  "body": {
    "owner": "alice",
    "data": "alice-private-document"
  },
  "id": 2
}
```

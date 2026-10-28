# Redwake investigation

Run: `de4463fe057e`

Backend: **ollama** · Lab: **fixed** · Status: **stopped**

Scenario: **discovery_branch**

Provider failure (http_server); reservations retained

| Resource | Verdict | Evidence |
|---|---|---|
| `/api/records/doc_k4` | inconclusive |  |
| `/api/files/file_x9` | inconclusive |  |
| `/api/records/inv_m8` | inconclusive |  |
| `/api/records/note_q2` | inconclusive |  |
| `/api/records/guide_h6` | inconclusive |  |
| `/api/exports/export_z3` | inconclusive |  |

## Fixture score

Correct findings: 0. Missed flaws: 0. False positives: 0. Inconclusive cases: 6.
Scores compare verifier-proven findings with private synthetic expectations; they do not grade model prose.

## Usage

Requests reserved: 2. Model calls reserved: 3. Recorded input/output tokens: 974/137.
Output tokens reserved: 3072. Recorded active time: 2.28s.
Provider usage complete: False. Dollar cost is not available from this harness.

## Diagnostics

Fixed categories identify the observed failure boundary; raw provider errors, exception text, headers and credentials are not recorded.

| Source | Category | Model call | HTTP status |
|---|---|---:|---:|
| provider | http_server | 3 | 500 |

## Interpretation

A vulnerable verdict requires the private record to be returned to both its owner and another actor. Protected means the tested cross-account read was denied with an owner success control. Inconclusive never means secure. These results cover only the listed synthetic GET cases.

## Evidence

Requests are GETs against an ephemeral 127.0.0.1 lab. Actor aliases select synthetic lab credentials. The adjacent evidence.json contains the captured responses; replay performs no network requests.

### Evidence 1

```json
{
  "actor": "alice",
  "path": "/api/projects",
  "status": 200,
  "body": {
    "projects": [
      {
        "id": "prj_a5",
        "links": {
          "self": "/api/projects/prj_a5"
        }
      }
    ]
  },
  "id": 1
}
```

### Evidence 2

```json
{
  "actor": "bob",
  "path": "/api/projects",
  "status": 200,
  "body": {
    "projects": [
      {
        "id": "prj_b9",
        "links": {
          "self": "/api/projects/prj_b9"
        }
      }
    ]
  },
  "id": 2
}
```

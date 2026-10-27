# Redwake investigation

Run: `2695eed70845`

Backend: **ollama** · Lab: **vulnerable** · Status: **stopped**

Scenario: **discovery**

Rejected tool call outside the lab contract

| Resource | Verdict | Evidence |
|---|---|---|
| `/api/records/doc_k4` | vulnerable | 5, 13 |
| `/api/files/file_x9` | inconclusive | 14 |
| `/api/records/inv_m8` | inconclusive | 9 |
| `/api/records/note_q2` | inconclusive | 10 |
| `/api/records/guide_h6` | public_allowed | 6, 12 |
| `/api/exports/export_z3` | inconclusive | 11 |

## Fixture score

Correct findings: 1. Missed flaws: 1. False positives: 0. Inconclusive cases: 4.
Scores compare verifier-proven findings with private synthetic expectations; they do not grade model prose.

## Usage

Requests reserved: 14. Model calls reserved: 15. Recorded input/output tokens: 17209/746.
Output tokens reserved: 15360. Recorded active time: 13.46s.
Provider usage complete: True. Dollar cost is not available from this harness.

## Diagnostics

Fixed categories identify the observed failure boundary; raw provider errors, exception text, headers and credentials are not recorded.

| Source | Category | Model call | HTTP status |
|---|---|---:|---:|
| model | tool_contract | 15 | — |

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

### Evidence 3

```json
{
  "actor": "alice",
  "path": "/api/projects/prj_a5",
  "status": 200,
  "body": {
    "id": "prj_a5",
    "links": {
      "records": "/api/projects/prj_a5/records"
    }
  },
  "id": 3
}
```

### Evidence 4

```json
{
  "actor": "alice",
  "path": "/api/projects/prj_a5/records",
  "status": 200,
  "body": {
    "records": [
      {
        "links": {
          "self": "/api/records/doc_k4"
        }
      },
      {
        "links": {
          "self": "/api/records/guide_h6"
        }
      }
    ]
  },
  "id": 4
}
```

### Evidence 5

```json
{
  "actor": "alice",
  "path": "/api/records/doc_k4",
  "status": 200,
  "body": {
    "owner": "alice",
    "data": "quarterly-draft",
    "visibility": "private",
    "links": {
      "attachment": "/api/files/file_x9"
    }
  },
  "id": 5
}
```

### Evidence 6

```json
{
  "actor": "alice",
  "path": "/api/records/guide_h6",
  "status": 200,
  "body": {
    "owner": "alice",
    "data": "team-handbook",
    "visibility": "public"
  },
  "id": 6
}
```

### Evidence 7

```json
{
  "actor": "bob",
  "path": "/api/projects/prj_b9",
  "status": 200,
  "body": {
    "id": "prj_b9",
    "links": {
      "records": "/api/projects/prj_b9/records"
    }
  },
  "id": 7
}
```

### Evidence 8

```json
{
  "actor": "bob",
  "path": "/api/projects/prj_b9/records",
  "status": 200,
  "body": {
    "records": [
      {
        "links": {
          "self": "/api/records/inv_m8"
        }
      },
      {
        "links": {
          "self": "/api/records/note_q2"
        }
      },
      {
        "links": {
          "self": "/api/exports/export_z3"
        }
      }
    ]
  },
  "id": 8
}
```

### Evidence 9

```json
{
  "actor": "bob",
  "path": "/api/records/inv_m8",
  "status": 200,
  "body": {
    "owner": "bob",
    "data": "supplier-invoice",
    "visibility": "private"
  },
  "id": 9
}
```

### Evidence 10

```json
{
  "actor": "bob",
  "path": "/api/records/note_q2",
  "status": 200,
  "body": {
    "owner": "bob",
    "data": "planning-note",
    "visibility": "private"
  },
  "id": 10
}
```

### Evidence 11

```json
{
  "actor": "bob",
  "path": "/api/exports/export_z3",
  "status": 503,
  "body": {
    "error": "unavailable"
  },
  "id": 11
}
```

### Evidence 12

```json
{
  "actor": "bob",
  "path": "/api/records/guide_h6",
  "status": 200,
  "body": {
    "owner": "alice",
    "data": "team-handbook",
    "visibility": "public"
  },
  "id": 12
}
```

### Evidence 13

```json
{
  "actor": "bob",
  "path": "/api/records/doc_k4",
  "status": 200,
  "body": {
    "owner": "alice",
    "data": "quarterly-draft",
    "visibility": "private",
    "links": {
      "attachment": "/api/files/file_x9"
    }
  },
  "id": 13
}
```

### Evidence 14

```json
{
  "actor": "bob",
  "path": "/api/files/file_x9",
  "status": 200,
  "body": {
    "owner": "alice",
    "data": "draft-attachment",
    "visibility": "private"
  },
  "id": 14
}
```

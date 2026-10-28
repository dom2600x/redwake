# Redwake investigation

Run: `0ae44612b9e4`

Backend: **ollama** · Lab: **vulnerable** · Status: **completed**

Scenario: **discovery_links**

Investigation finished.

| Resource | Verdict | Evidence |
|---|---|---|
| `/api/records/doc_k4` | vulnerable | 7, 14 |
| `/api/files/file_x9` | vulnerable | 17, 18 |
| `/api/records/inv_m8` | protected | 9, 12 |
| `/api/records/note_q2` | protected | 10, 13 |
| `/api/records/guide_h6` | public_allowed | 8, 15 |
| `/api/exports/export_z3` | inconclusive | 11, 16 |

## Fixture score

Correct findings: 2. Missed flaws: 0. False positives: 0. Inconclusive cases: 1.
Scores compare verifier-proven findings with private synthetic expectations; they do not grade model prose.

## Usage

Requests reserved: 18. Model calls reserved: 7. Recorded input/output tokens: 10662/1424.
Output tokens reserved: 7168. Recorded active time: 45.91s.
Provider usage complete: True. Dollar cost is not available from this harness.

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
      "records": "/api/collections/set_l6"
    }
  },
  "id": 3
}
```

### Evidence 4

```json
{
  "actor": "bob",
  "path": "/api/projects/prj_b9",
  "status": 200,
  "body": {
    "id": "prj_b9",
    "links": {
      "records": "/api/collections/set_n8"
    }
  },
  "id": 4
}
```

### Evidence 5

```json
{
  "actor": "alice",
  "path": "/api/collections/set_l6",
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
  "id": 5
}
```

### Evidence 6

```json
{
  "actor": "bob",
  "path": "/api/collections/set_n8",
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
  "id": 6
}
```

### Evidence 7

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
  "id": 7
}
```

### Evidence 8

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
  "actor": "alice",
  "path": "/api/records/inv_m8",
  "status": 403,
  "body": {
    "error": "denied"
  },
  "id": 12
}
```

### Evidence 13

```json
{
  "actor": "alice",
  "path": "/api/records/note_q2",
  "status": 404,
  "body": {
    "error": "denied"
  },
  "id": 13
}
```

### Evidence 14

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
  "id": 14
}
```

### Evidence 15

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
  "id": 15
}
```

### Evidence 16

```json
{
  "actor": "alice",
  "path": "/api/exports/export_z3",
  "status": 503,
  "body": {
    "error": "unavailable"
  },
  "id": 16
}
```

### Evidence 17

```json
{
  "actor": "alice",
  "path": "/api/files/file_x9",
  "status": 200,
  "body": {
    "owner": "alice",
    "data": "draft-attachment",
    "visibility": "private"
  },
  "id": 17
}
```

### Evidence 18

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
  "id": 18
}
```

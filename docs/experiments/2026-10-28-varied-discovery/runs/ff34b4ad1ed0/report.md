# Redwake investigation

Run: `ff34b4ad1ed0`

Backend: **ollama** · Lab: **vulnerable** · Status: **stopped**

Scenario: **discovery_ids**

Model-call budget exhausted

| Resource | Verdict | Evidence |
|---|---|---|
| `/api/records/doc_r8` | vulnerable | 7, 12 |
| `/api/files/file_t4` | inconclusive | 16 |
| `/api/records/inv_s3` | protected | 9, 13 |
| `/api/records/note_v1` | protected | 10, 14 |
| `/api/records/guide_w6` | public_allowed | 8, 15 |
| `/api/exports/export_y5` | inconclusive | 11 |

## Fixture score

Correct findings: 1. Missed flaws: 1. False positives: 0. Inconclusive cases: 2.
Scores compare verifier-proven findings with private synthetic expectations; they do not grade model prose.

## Usage

Requests reserved: 16. Model calls reserved: 16. Recorded input/output tokens: 20102/953.
Output tokens reserved: 16384. Recorded active time: 13.60s.
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
        "id": "prj_c7",
        "links": {
          "self": "/api/projects/prj_c7"
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
        "id": "prj_d2",
        "links": {
          "self": "/api/projects/prj_d2"
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
  "path": "/api/projects/prj_c7",
  "status": 200,
  "body": {
    "id": "prj_c7",
    "links": {
      "records": "/api/projects/prj_c7/records"
    }
  },
  "id": 3
}
```

### Evidence 4

```json
{
  "actor": "bob",
  "path": "/api/projects/prj_d2",
  "status": 200,
  "body": {
    "id": "prj_d2",
    "links": {
      "records": "/api/projects/prj_d2/records"
    }
  },
  "id": 4
}
```

### Evidence 5

```json
{
  "actor": "alice",
  "path": "/api/projects/prj_c7/records",
  "status": 200,
  "body": {
    "records": [
      {
        "links": {
          "self": "/api/records/doc_r8"
        }
      },
      {
        "links": {
          "self": "/api/records/guide_w6"
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
  "path": "/api/projects/prj_d2/records",
  "status": 200,
  "body": {
    "records": [
      {
        "links": {
          "self": "/api/records/inv_s3"
        }
      },
      {
        "links": {
          "self": "/api/records/note_v1"
        }
      },
      {
        "links": {
          "self": "/api/exports/export_y5"
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
  "path": "/api/records/doc_r8",
  "status": 200,
  "body": {
    "owner": "alice",
    "data": "quarterly-draft",
    "visibility": "private",
    "links": {
      "attachment": "/api/files/file_t4"
    }
  },
  "id": 7
}
```

### Evidence 8

```json
{
  "actor": "alice",
  "path": "/api/records/guide_w6",
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
  "path": "/api/records/inv_s3",
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
  "path": "/api/records/note_v1",
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
  "path": "/api/exports/export_y5",
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
  "path": "/api/records/doc_r8",
  "status": 200,
  "body": {
    "owner": "alice",
    "data": "quarterly-draft",
    "visibility": "private",
    "links": {
      "attachment": "/api/files/file_t4"
    }
  },
  "id": 12
}
```

### Evidence 13

```json
{
  "actor": "alice",
  "path": "/api/records/inv_s3",
  "status": 403,
  "body": {
    "error": "denied"
  },
  "id": 13
}
```

### Evidence 14

```json
{
  "actor": "alice",
  "path": "/api/records/note_v1",
  "status": 404,
  "body": {
    "error": "denied"
  },
  "id": 14
}
```

### Evidence 15

```json
{
  "actor": "bob",
  "path": "/api/records/guide_w6",
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
  "actor": "bob",
  "path": "/api/files/file_t4",
  "status": 200,
  "body": {
    "owner": "alice",
    "data": "draft-attachment",
    "visibility": "private"
  },
  "id": 16
}
```

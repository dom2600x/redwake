# Redwake investigation

Run: `a989018a5496`

Backend: **ollama** · Lab: **vulnerable** · Status: **stopped**

Scenario: **discovery_deep**

Request budget exhausted

| Resource | Verdict | Evidence |
|---|---|---|
| `/api/records/doc_k4` | vulnerable | 28, 14 |
| `/api/files/file_x9` | inconclusive | 18 |
| `/api/records/inv_m8` | protected | 30, 16 |
| `/api/records/note_q2` | protected | 31, 17 |
| `/api/records/guide_h6` | public_allowed | 29, 15 |
| `/api/exports/export_z3` | inconclusive | 32, 19 |

## Fixture score

Correct findings: 1. Missed flaws: 1. False positives: 0. Inconclusive cases: 2.
Scores compare verifier-proven findings with private synthetic expectations; they do not grade model prose.

## Usage

Requests reserved: 32. Model calls reserved: 14. Recorded input/output tokens: 34209/3014.
Output tokens reserved: 14336. Recorded active time: 63.76s.
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
      "navigation": "/api/navigation/nav_a1"
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
      "navigation": "/api/navigation/nav_b2"
    }
  },
  "id": 4
}
```

### Evidence 5

```json
{
  "actor": "alice",
  "path": "/api/navigation/nav_a1",
  "status": 200,
  "body": {
    "links": {
      "records": "/api/collections/set_l6"
    }
  },
  "id": 5
}
```

### Evidence 6

```json
{
  "actor": "bob",
  "path": "/api/navigation/nav_b2",
  "status": 200,
  "body": {
    "links": {
      "records": "/api/collections/set_n8"
    }
  },
  "id": 6
}
```

### Evidence 7

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
  "id": 7
}
```

### Evidence 8

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
  "id": 8
}
```

### Evidence 9

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
  "id": 9
}
```

### Evidence 10

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
  "id": 10
}
```

### Evidence 11

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
  "id": 11
}
```

### Evidence 12

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
  "id": 12
}
```

### Evidence 13

```json
{
  "actor": "bob",
  "path": "/api/exports/export_z3",
  "status": 503,
  "body": {
    "error": "unavailable"
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
  "path": "/api/records/inv_m8",
  "status": 403,
  "body": {
    "error": "denied"
  },
  "id": 16
}
```

### Evidence 17

```json
{
  "actor": "alice",
  "path": "/api/records/note_q2",
  "status": 404,
  "body": {
    "error": "denied"
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

### Evidence 19

```json
{
  "actor": "alice",
  "path": "/api/exports/export_z3",
  "status": 503,
  "body": {
    "error": "unavailable"
  },
  "id": 19
}
```

### Evidence 20

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
  "id": 20
}
```

### Evidence 21

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
  "id": 21
}
```

### Evidence 22

```json
{
  "actor": "alice",
  "path": "/api/projects/prj_a5",
  "status": 200,
  "body": {
    "id": "prj_a5",
    "links": {
      "navigation": "/api/navigation/nav_a1"
    }
  },
  "id": 22
}
```

### Evidence 23

```json
{
  "actor": "bob",
  "path": "/api/projects/prj_b9",
  "status": 200,
  "body": {
    "id": "prj_b9",
    "links": {
      "navigation": "/api/navigation/nav_b2"
    }
  },
  "id": 23
}
```

### Evidence 24

```json
{
  "actor": "alice",
  "path": "/api/navigation/nav_a1",
  "status": 200,
  "body": {
    "links": {
      "records": "/api/collections/set_l6"
    }
  },
  "id": 24
}
```

### Evidence 25

```json
{
  "actor": "bob",
  "path": "/api/navigation/nav_b2",
  "status": 200,
  "body": {
    "links": {
      "records": "/api/collections/set_n8"
    }
  },
  "id": 25
}
```

### Evidence 26

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
  "id": 26
}
```

### Evidence 27

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
  "id": 27
}
```

### Evidence 28

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
  "id": 28
}
```

### Evidence 29

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
  "id": 29
}
```

### Evidence 30

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
  "id": 30
}
```

### Evidence 31

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
  "id": 31
}
```

### Evidence 32

```json
{
  "actor": "bob",
  "path": "/api/exports/export_z3",
  "status": 503,
  "body": {
    "error": "unavailable"
  },
  "id": 32
}
```

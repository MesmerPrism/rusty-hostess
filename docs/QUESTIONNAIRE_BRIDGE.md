# Quest Questionnaire Bridge

Hostess owns the low-rate command bridge between the Windows operator and the
Quest-side Rusty Morphospace app. The bridge accepts operator JSON over HTTP and
keeps the Android panel launch contract caller-owned:

- Rusty Morphospace receives experimenter/LSL timing decisions.
- Hostess bridge exposes status and command routes for the Windows operator.
- The Quest foreground caller launches the questionnaire panel with the existing
  explicit intent, caller-owned `content://` result URI, and completion
  `PendingIntent`.
- Answer data remains in the panel result URI path; the bridge status route
  reports only foreground/control state.

## CLI

Run a local development bridge:

```powershell
python tools\hostessctl\hostessctl.py questionnaire-serve --host 127.0.0.1 --port 8787
```

Poll status:

```powershell
python tools\hostessctl\hostessctl.py questionnaire-status --endpoint http://127.0.0.1:8787
```

Open questionnaire blocks:

```powershell
python tools\hostessctl\hostessctl.py questionnaire-open-block --block 1 --session-id maia-spatial-session-001 --participant-ref P001 --language-code en --endpoint http://127.0.0.1:8787
python tools\hostessctl\hostessctl.py questionnaire-open-block --block 2 --session-id maia-spatial-session-001 --participant-ref P001 --language-code en --endpoint http://127.0.0.1:8787
python tools\hostessctl\hostessctl.py questionnaire-open-block --block 3 --session-id maia-spatial-session-001 --participant-ref P001 --language-code en --endpoint http://127.0.0.1:8787
```

Dismiss the panel:

```powershell
python tools\hostessctl\hostessctl.py questionnaire-dismiss --session-id maia-spatial-session-001 --endpoint http://127.0.0.1:8787
```

These commands are the scriptable equivalents of the Windows Makepad operator
controls.

## Routes

```text
GET  /v1/status
POST /v1/command
```

`POST /v1/command` accepts `quest.questionnaire.operator.v1` envelopes. The
`panel_request` field is the `quest.questionnaire.v1` launch body that the
Quest foreground caller passes into the panel intent.

The local Python bridge is a development and end-to-end smoke-test surface. A
device bridge should implement the same routes and return the same foreground
state while using platform-private Android APIs for launch/result handoff.


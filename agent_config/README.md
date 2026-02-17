# Agent Configuration — Single Source of Truth

This directory holds the canonical configuration for the ElevenLabs
conversational AI agent. Every setting that matters lives here in
plain, diffable files.

## Files

| File | What it controls |
|------|-----------------|
| `system_prompt.md` | The full system prompt sent to the LLM |
| `data_collection.json` | Post-conversation data extraction fields |
| `settings.json` | Voice, LLM, first message, agent name/language |

## Workflow

```
 ┌──────────────┐      agent_push.py      ┌──────────────────┐
 │ agent_config/ │  ──────────────────►   │  ElevenLabs API  │
 │  (local git)  │  ◄──────────────────   │  (live agent)    │
 └──────────────┘      agent_pull.py      └──────────────────┘
```

### Push local → ElevenLabs

Edit the files here, then push them to the live agent:

```bash
source .env && python3 scripts/agent_push.py
```

### Pull ElevenLabs → local

Fetch the live agent's current config and overwrite these files:

```bash
source .env && python3 scripts/agent_pull.py
```

### Diff (check for drift)

Compare local files against the live agent without changing anything:

```bash
source .env && python3 scripts/agent_pull.py --diff
```

## Rules

1. **Local files are the source of truth.** Make changes here, then push.
2. **Never edit the agent in the ElevenLabs dashboard** without pulling
   immediately afterwards — otherwise the next push will overwrite your
   dashboard changes.
3. **Commit after every push.** The git history becomes the audit trail.
4. The `system_prompt.md` file is **plain text only** — no YAML
   frontmatter, no metadata headers. The push script sends it verbatim.

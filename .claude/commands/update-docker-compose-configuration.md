---
name: update-docker-compose-configuration
description: Workflow command scaffold for update-docker-compose-configuration in mediastack.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /update-docker-compose-configuration

Use this workflow when working on **update-docker-compose-configuration** in `mediastack`.

## Goal

Update the Docker Compose configuration for the full-download-vpn stack, including service changes, network settings, and environment variables.

## Common Files

- `full-download-vpn/docker-compose.yaml`
- `full-download-vpn/.env`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Edit full-download-vpn/docker-compose.yaml to reflect service or configuration changes.
- Optionally update full-download-vpn/.env if environment variables are affected.
- Commit the changes.

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.
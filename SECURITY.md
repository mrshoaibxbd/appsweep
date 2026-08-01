# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| 0.1.x | Yes |

## Reporting a vulnerability

Do not publicly disclose an unpatched vulnerability through a GitHub issue.

Report security concerns through the contact form at:

https://shoaib.tech

Include:

- A description of the vulnerability
- Steps to reproduce it
- The affected AppSweep version
- The affected Ubuntu version
- The potential impact
- Any suggested mitigation

## Security boundaries

AppSweep separates its graphical interface from its privileged helper.

The helper:

- Must be started through PolicyKit
- Accepts only predefined operations
- Validates package and application identifiers
- Blocks protected system components
- Does not execute arbitrary commands
- Uses absolute command paths
- Uses a restricted environment

AppSweep only deletes detected user-data paths under explicitly permitted directories.

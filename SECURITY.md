# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.x (latest) | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in SimpleLog, please **do not open a public issue**.

Instead, report it privately by emailing:

**sikander.ravate@gmail.com**

Please include:
- A description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested fix (optional)

You can expect an acknowledgement within **72 hours** and a resolution or status update within **7 days**.

## Scope

SimpleLog is a desktop log viewer. The main attack surfaces to consider are:

- **Local file parsing** — maliciously crafted log files could trigger unexpected behavior in the parser or UI renderer
- **AWS CloudWatch credentials** — SimpleLog reads AWS credentials from `~/.aws/credentials` or environment variables; it does not store or transmit them beyond the AWS SDK
- **Workspace files** — workspace configs saved in `~/.config/simplelog/workspaces.json` contain file paths and CloudWatch source references

## Out of Scope

- Vulnerabilities in third-party dependencies (report those directly to the upstream project)
- Issues requiring physical access to the machine

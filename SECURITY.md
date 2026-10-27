# Security Policy

## Project status

This repository contains a **research prototype**. It is not a production service and has not received a security certification. The local sidecar, session and pairing mechanisms are contract-level prototypes, not hardened credential infrastructure.

## Reporting a vulnerability

Please **do not** open a public issue for a suspected vulnerability.

Use GitHub's private vulnerability reporting on the repository's **Security** tab, or contact the maintainer through the GitHub profile associated with the repository.

Include:

- affected component and version/commit;
- reproduction steps or proof of concept;
- impact assessment;
- whether the issue affects the contract model, the prototype implementation, or both.

## Scope

In scope:

- authority bypass in the Agent/Human/CAD-bridge role model;
- pairing or session escalation;
- discovery metadata leaking credentials;
- project lease / stale-writer races that permit two live writers;
- local HTTP Host/Origin validation bypass;
- dependency or artifact integrity bypass.

Out of scope for this research prototype (documented gaps, not accepted vulnerabilities unless they enable the above):

- resistance to malware running as the same OS user;
- Windows ACL/DPAPI or installer trust (not implemented);
- production multi-host database semantics;
- denial of service through resource exhaustion;
- issues requiring a compromised host or elevated local privileges.

## Disclosure

Confirmed issues will be fixed on a best-effort basis and recorded in `CHANGELOG.md` when appropriate. There is no bug bounty program.

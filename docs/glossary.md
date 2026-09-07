# Glossary

Daksh process terms used across this project's docs. Domain-specific
vocabulary (entity names, status terms, roles) lives separately in
`docs/domain-glossary.md`.

## BRD

Business Requirements Document — the stage-20 Daksh artifact that
decomposes an approved vision (or, absent one, direct stakeholder input)
into traceable use cases, functional requirements, and acceptance
criteria.

## UC

Use Case — a numbered (`UC-001`, `UC-002`, …) actor-driven scenario in a
BRD, with actors, preconditions, a main flow, and alternate/error paths.

## FR

Functional Requirement — a numbered (`FR-001`, `FR-002`, …) system
behavior a BRD commits to. Every FR traces to a UC; orphan FRs don't
ship.

## AC

Acceptance Criterion — a numbered (`AC-001`, `AC-002`, …) testable
condition that confirms one FR is satisfied.

## POC

Proof of Concept — a scoped, non-production build meant to validate a
technical approach before committing to full delivery.

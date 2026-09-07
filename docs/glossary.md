# Glossary

Daksh process terms used across this project's docs. Domain-specific
vocabulary (entity names, status terms, roles) lives separately in
`docs/domain-glossary.md`.

## Vision

The stage-10 Daksh artifact that locks the product thesis — what the
one deep module is, who it's for, what's out of scope, and what would
invalidate the thesis — before the BRD decomposes it (or, as in this
project, before a BRD written directly from a source doc is grounded
against it retroactively).

## Deep Module

A module whose interface is small relative to the behavior it hides.
Tested with the deletion test: imagine removing the module — if its
complexity reappears in every caller, it was deep and earned its
existence; if the complexity simply vanishes, it was a pass-through
and should not have been a separate module.

## Leap-of-Faith Assumption

A belief a Vision document rests on that, if false, invalidates the
product's premise rather than one feature of it. Distinct from an
ordinary [Assumption](business-requirements.md#data-models) recorded
against a single decision — a leap-of-faith assumption is unvalidated
by definition at the point Vision is written; the product exists partly
to test it.

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

## TRD

Technical Requirements Document — the stage-50a Daksh artifact that turns
an approved module System spec into a concrete implementation contract:
component diagram, formal data/API schemas, and deployment detail.

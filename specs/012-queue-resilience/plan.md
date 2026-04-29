# Implementation Plan: Queue and Resilience

**Branch**: `012-queue-resilience` | **Date**: 2026-04-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/012-queue-resilience/spec.md`

## Summary

Implement ARQ job models, dead letter queue, circuit breakers for external services, and graceful shutdown support.

## Technical Context

**Language/Version**: Python 3.12+  
**Primary Dependencies**: Pydantic  
**Storage**: Redis for ARQ, PostgreSQL for DLQ metadata  

## Architecture Decisions

1. **ARQ job models**: Pydantic models for job representation.
2. **DLQ**: Store failed jobs with retry history.
3. **Circuit breakers**: Per-service state machine (already partially implemented in APEX integration).
4. **Graceful shutdown**: Signal handlers for workers.

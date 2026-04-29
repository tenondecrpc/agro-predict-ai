# Implementation Plan: Deployment Profiles

**Branch**: `009-deployment-profiles` | **Date**: 2026-04-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/009-deployment-profiles/spec.md`

## Summary

Implement deployment profile configuration models and validation. The actual Helm charts already exist under `helm/`. This spec adds Python models for deployment configuration, profile detection, and air-gapped validation.

## Technical Context

**Language/Version**: Python 3.12+  
**Primary Dependencies**: Pydantic  
**Storage**: Environment variables, config files  

## Architecture Decisions

1. **Profile detection via env var**: `DEPLOYMENT_PROFILE=connected` or `air_gapped`.
2. **Config models**: Pydantic models for HPA, health probes, resource quotas.
3. **Air-gapped validation**: Verify no external URLs in config when air-gapped.

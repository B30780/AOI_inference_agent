---
issue: 3
title: External Service Integration
analyzed: 2026-02-25T11:30:14Z
estimated_hours: 10
parallelization_factor: 2.5
---

# Parallel Work Analysis: Issue #3

## Overview
Implement HTTP client service for communicating with external SegFormer model service. This involves creating an async client with retry logic, timeout handling, response parsing, and comprehensive error handling. The work can be parallelized between core implementation, error handling/resilience, and testing.

## Parallel Streams

### Stream A: Core HTTP Client Implementation
**Scope**: Implement basic SegFormerClient class with async HTTP communication to external service
**Files**:
- app/services/segformer_client.py (create)
- app/services/__init__.py (update imports)
**Agent Type**: backend-specialist
**Can Start**: immediately
**Estimated Hours**: 4
**Dependencies**: none

Details:
- Create SegFormerClient class
- Implement basic infer_image method
- Handle multipart/form-data file upload
- Parse JSON response
- Extract image files from response

### Stream B: Resilience & Error Handling
**Scope**: Add retry logic, timeout handling, and comprehensive error handling
**Files**:
- app/services/segformer_client.py (enhance)
**Agent Type**: backend-specialist
**Can Start**: after Stream A completes base structure
**Estimated Hours**: 3
**Dependencies**: Stream A (needs base client structure)

Details:
- Implement exponential backoff retry logic (1s, 2s, 4s)
- Add timeout configuration (30s)
- Handle httpx.TimeoutException
- Handle httpx.HTTPError
- Add response validation
- Implement _parse_response helper
- Add logging for all external calls

### Stream C: Configuration & Settings
**Scope**: Add configuration for SegFormer service URL and related settings
**Files**:
- app/config.py (add SEGFORMER_SERVICE_URL)
**Agent Type**: backend-specialist
**Can Start**: immediately
**Estimated Hours**: 1
**Dependencies**: none

Details:
- Add SEGFORMER_SERVICE_URL to config
- Add default value or environment variable
- Ensure proper typing

### Stream D: Testing Suite
**Scope**: Create comprehensive unit and integration tests
**Files**:
- tests/services/test_segformer_client.py (create)
- tests/services/__init__.py (create if needed)
**Agent Type**: backend-specialist
**Can Start**: after Stream A completes base implementation
**Estimated Hours**: 3
**Dependencies**: Stream A (needs client implementation), Stream B (needs error handling for full coverage)

Details:
- Mock httpx.AsyncClient
- Test successful inference
- Test retry logic with transient failures
- Test timeout handling
- Test connection errors
- Test HTTP error responses
- Test response validation
- Mock response fixtures
- Aim for >80% coverage

## Coordination Points

### Shared Files
- `app/services/segformer_client.py` - Streams A & B (A creates base, B enhances)
  - **Coordination**: Stream A must complete basic class structure before B can add resilience

### Sequential Requirements
1. Stream A must create base SegFormerClient class before Stream B can add retry logic
2. Stream A must implement basic infer_image before Stream D can write tests
3. Stream C can proceed independently at any time

## Conflict Risk Assessment
- **Low Risk**: Stream C works on separate config file
- **Medium Risk**: Stream A & B both modify segformer_client.py
  - Mitigation: Stream A completes base structure, then Stream B enhances it
- **Low Risk**: Stream D only reads from implementation files

## Parallelization Strategy

**Recommended Approach**: hybrid

Launch Streams A & C simultaneously. Once A completes the base client structure (SegFormerClient class with basic infer_image method), launch Stream B to add resilience features. Stream D can start once A has testable methods, and complete after B finishes.

**Optimal Sequence**:
1. Start: A (core implementation) + C (config) in parallel
2. When A completes base structure: Start B (resilience)
3. When A has testable methods: Start D (testing)
4. D completes after A & B are done

## Expected Timeline

With parallel execution:
- Wall time: ~5-6 hours
- Total work: 11 hours
- Efficiency gain: ~50%

Without parallel execution:
- Wall time: 11 hours

## Notes
- httpx library must be added to requirements.txt (can be done by any stream)
- External service at http://140.96.77.124:8080/ may not be accessible during development
- Consider mocking external service for all tests
- Integration test should be optional/skippable if service is unreachable
- Logging is critical for debugging external service communication
- Response validation should be comprehensive to catch API changes early

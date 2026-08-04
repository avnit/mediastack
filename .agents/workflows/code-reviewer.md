---
description: Performs a thorough code review covering bugs, security vulnerabilities,   performance, and best practices. Use when asked to "review", "check",   "audit code", or "look at this file". Works on any language.
---

# Code Review

Perform a structured code review across these dimensions:

## Security
- Injection vulnerabilities (SQL, command, LDAP, XPath)
- Authentication / authorization bypass
- Secrets or credentials in code
- Insecure deserialization
- Path traversal / directory traversal
- Dependency vulnerabilities (flag any `import` worth checking)

## Correctness
- Logic errors, off-by-one bugs
- Null/undefined dereferences
- Race conditions or thread safety issues
- Error handling gaps — uncaught exceptions, swallowed errors
- Edge cases (empty input, max values, encoding)

## Performance
- N+1 query patterns
- Unnecessary loops inside loops
- Missing indexes on filtered fields
- Memory leaks (unclosed resources, large allocations in loops)

## Maintainability
- Functions > 50 lines without clear justification
- Magic numbers without named constants
- Duplication that should be extracted
- Naming that doesn't reflect purpose

## Output Format

Group findings by severity: CRITICAL > HIGH > MED > LOW > NITPICK

For each finding:
```
[SEVERITY] Line XX: <one-line description>
  Why: <why this is a problem>
  Fix: <code snippet or specific change>
```

End with: Overall assessment (1-5) and top 3 priority fixes.
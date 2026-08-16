```markdown
# mediastack Development Patterns

> Auto-generated skill from repository analysis

## Overview

This skill provides a comprehensive guide to the development patterns, coding conventions, and operational workflows used in the `mediastack` TypeScript repository. It covers file organization, code style, commit conventions, and step-by-step instructions for common infrastructure and configuration tasks—especially those related to Docker Compose stack management for the `full-download-vpn` service.

## Coding Conventions

- **Language:** TypeScript
- **Framework:** None detected
- **File Naming:** Use kebab-case for files.
  - Example: `user-service.ts`, `docker-compose.yaml`
- **Import Style:** Use relative imports.
  - Example:
    ```typescript
    import { fetchData } from './utils/fetch-data';
    ```
- **Export Style:** Use named exports.
  - Example:
    ```typescript
    // In fetch-data.ts
    export function fetchData() { /* ... */ }

    // In another file
    import { fetchData } from './fetch-data';
    ```
- **Commit Messages:** Use `feat` and `fix` prefixes, with concise descriptions (~47 characters).
  - Example: `feat: add user authentication middleware`

## Workflows

### Update Docker Compose Configuration
**Trigger:** When you need to add, remove, or modify services, environment variables, or network settings in the Docker Compose stack.  
**Command:** `/update-docker-compose`

1. Edit `full-download-vpn/docker-compose.yaml` to reflect service or configuration changes.
2. Optionally, update `full-download-vpn/.env` if environment variables are affected.
3. Commit the changes with a descriptive message.

**Example:**
```yaml
# full-download-vpn/docker-compose.yaml
services:
  app:
    image: my-app:latest
    environment:
      - NODE_ENV=production
```

### Update .env File
**Trigger:** When you need to change environment variables or secrets for the stack.  
**Command:** `/update-env`

1. Edit `full-download-vpn/.env` to add, remove, or modify variables.
2. Commit the changes.

**Example:**
```
# full-download-vpn/.env
API_KEY=your-new-api-key
DEBUG=false
```

### Update Restart Script
**Trigger:** When you need to improve or fix the stack management script.  
**Command:** `/update-restart-script`

1. Edit or add `full-download-vpn/restart.sh`.
2. Optionally, update `full-download-vpn/README.md` to reflect script changes.
3. Commit the changes.

**Example:**
```bash
# full-download-vpn/restart.sh
#!/bin/bash
docker-compose down
docker-compose up -d
```

### Add or Update Bookmarks HTML
**Trigger:** When you want to update or fix the bookmarks HTML file.  
**Command:** `/update-bookmarks`

1. Edit or add `full-download-vpn/bookmarks.html` or `full-download-vpn/booksmarks.html`.
2. Optionally, update `README.md` or related scripts.
3. Commit the changes.

**Example:**
```html
<!-- full-download-vpn/bookmarks.html -->
<ul>
  <li><a href="http://localhost:8080">Service Dashboard</a></li>
</ul>
```

## Testing Patterns

- **Framework:** Unknown (not detected)
- **Test File Pattern:** Files named with `*.test.*`
  - Example: `user-service.test.ts`
- **Typical Structure:**
  ```typescript
  // user-service.test.ts
  import { fetchData } from './fetch-data';

  test('fetchData returns expected result', () => {
    expect(fetchData()).toBe(/* expected value */);
  });
  ```

## Commands

| Command                  | Purpose                                                        |
|--------------------------|----------------------------------------------------------------|
| /update-docker-compose   | Update Docker Compose configuration for the stack              |
| /update-env              | Update environment variables in the .env file                  |
| /update-restart-script   | Update or add the stack management restart script              |
| /update-bookmarks        | Add or update bookmarks HTML files for the stack               |
```
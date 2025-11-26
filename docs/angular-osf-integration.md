# Angular OSF and osf.io Docker Integration Guide

## Overview

Configuration and troubleshooting guide for running angular-osf within the osf.io Docker environment.

---

## Architecture

### Flask Proxy Mechanism

The osf.io Flask app proxies multiple frontend apps based on URL path:

```
http://localhost:5001/angular_osf/*   → Angular (port 4300)
http://localhost:5001/ember_osf_web/* → Ember (port 4200)
http://localhost:5001/preprints/*     → Preprints (port 4201)
```

Configuration is defined in `website/settings/local.py` via `EXTERNAL_EMBER_APPS`:

```python
EXTERNAL_EMBER_APPS = {
    'angular_osf': {
        'server': f'http://{EMBER_DOMAIN}:4300/angular_osf/',
        'path': '/angular_osf/',
    },
    # ...
}
```

### PRIMARY_WEB_APP

Specifies which app to display when accessing `/`:

```python
PRIMARY_WEB_APP = 'angular_osf'
```

---

## Configuration Files

### osf.io Side

**docker-compose.yml:**
```yaml
angular_osf:
  image: angular-osf:dev
  command: ['sh', '-c', 'npm run check:config && npx ng serve --configuration docker-local --host 0.0.0.0 --port 4300 --poll 2000 --serve-path /angular_osf/']
  ports:
    - 4300:4300
  environment:
    - OSF_URL=http://localhost:5000
    - OSF_API_URL=http://localhost:8000
    - OSF_CAS_URL=http://localhost:8080
```

**website/settings/local.py:**
```python
EXTERNAL_EMBER_APPS = {
    'angular_osf': {
        'server': f'http://{EMBER_DOMAIN}:4300/angular_osf/',
        'path': '/angular_osf/',
    },
}
PRIMARY_WEB_APP = 'angular_osf'
```

### angular-osf Side

**angular.json (docker-local configuration):**
```json
{
  "docker-local": {
    "baseHref": "/angular_osf/",
    "fileReplacements": [
      {
        "replace": "src/environments/environment.ts",
        "with": "src/environments/environment.docker-local.ts"
      }
    ]
  }
}
```

**environment.docker-local.ts:**
```typescript
export const environment = {
  // ...
  routerBaseHref: '/',  // Overrides APP_BASE_HREF for Router
};
```

**app.config.ts:**
```typescript
import { APP_BASE_HREF } from '@angular/common';

export const appConfig: ApplicationConfig = {
  providers: [
    {
      provide: APP_BASE_HREF,
      deps: [ENVIRONMENT],
      useFactory: (environment: EnvironmentModel) => environment.routerBaseHref ?? '/',
    },
    // ...
  ],
};
```

---

## Issues and Solutions

### 1. Asset Proxy 404 Errors

**Problem:** `/angular_osf/main.js` returns 404

**Cause:** Flask's `urljoin` behavior. Without the path suffix in the `server` URL, asset paths don't join correctly.

**Solution:** Include the path in the `server` URL:
```python
# Bad
'server': f'http://{EMBER_DOMAIN}:4300/'

# Good
'server': f'http://{EMBER_DOMAIN}:4300/angular_osf/'
```

### 2. config.json Fetch Failure

**Problem:** `OSFConfigService` gets 404 when fetching `/assets/config/config.json`

**Cause:** Absolute path `/assets/...` resolves outside the Flask proxy path `/angular_osf/`

**Solution:** Use relative path:
```typescript
// Bad
this.http.get('/assets/config/config.json')

// Good
this.http.get('assets/config/config.json')
```

### 3. Trailing Slash in Environment Variables

**Problem:** Sign In URL becomes `http://localhost:8080//login` (double slash)

**Cause:** Environment variable `OSF_CAS_URL=http://localhost:8080/` concatenates with `/login` in code

**Solution:** Remove trailing slash from environment variables:
```yaml
# Bad
- OSF_CAS_URL=http://localhost:8080/

# Good
- OSF_CAS_URL=http://localhost:8080
```

### 4. Redirect from `/` to `/angular_osf/`

**Problem:** Accessing `http://localhost:5001/` redirects to `/angular_osf/`

**Cause:** Angular's `baseHref` affects both:
- Asset relative path resolution (`<base href>` tag)
- Angular Router's base path

With `baseHref: '/angular_osf/'`, the Router triggers a redirect.

**Attempted solutions:**
- `baseHref: '/'` + `deployUrl: '/angular_osf/'` → `deployUrl` doesn't work with Vite-based dev server
- `--deploy-url` CLI option → Deprecated in modern Angular CLI

**Solution:** Separate `baseHref` and `APP_BASE_HREF` via environment:

| Setting | Value | Purpose |
|---------|-------|---------|
| `baseHref` (angular.json) | `/angular_osf/` | Asset relative path resolution |
| `routerBaseHref` (environment) | `/` | Router base path via `APP_BASE_HREF` |

```typescript
// environment.docker-local.ts
export const environment = {
  routerBaseHref: '/',
  // ...
};

// app.config.ts
{
  provide: APP_BASE_HREF,
  deps: [ENVIRONMENT],
  useFactory: (environment: EnvironmentModel) => environment.routerBaseHref ?? '/',
}
```

Also use `--serve-path /angular_osf/` to explicitly set the dev server's serve path.

---

## Verification Commands

```bash
# Build Angular image
cd ../angular-osf
docker build --target local-dev -t angular-osf:dev .

# Start container
cd ../osf.io
docker compose up -d angular_osf

# Check logs
docker compose logs -f angular_osf --tail=50

# Verify config.json
curl http://localhost:5001/angular_osf/assets/config/config.json

# Verify assets
curl -I http://localhost:5001/angular_osf/main.js

# Check HTML
curl -s http://localhost:5001/ | grep '<base'
```

---

## Summary

Key points for running Angular behind Flask proxy:

1. **Proxy path**: Include the app path in the `server` URL
2. **Asset references**: Use relative paths, not absolute paths
3. **Environment variables**: Watch out for trailing slashes in URLs
4. **Router vs assets separation**: Configure `baseHref` (assets) and `routerBaseHref` (router) separately via environment (required because `deployUrl` doesn't work with Vite)

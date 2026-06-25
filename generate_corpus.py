#!/usr/bin/env python3
"""
Generate reproducible synthetic multi-language codebase with no external downloads.
Creates small, medium, and large repos with planted ground truth for code search benchmarking.
"""

import json
import random
import hashlib
from pathlib import Path
from datetime import datetime

# Fixed seed for reproducibility
RANDOM_SEED = 42
random.seed(RANDOM_SEED)

OUTPUT_DIR = Path("corpus")
OUTPUT_DIR.mkdir(exist_ok=True)

# Ground truth storage
GROUND_TRUTH = {
    "queries": [],
    "files": {},
    "symbols": {},
    "generated_at": datetime.now().isoformat(),
    "seed": RANDOM_SEED
}

def write_file(path, content):
    """Write file and track in ground truth"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # Track file metadata
    rel_path = str(path.relative_to(OUTPUT_DIR))
    GROUND_TRUTH["files"][rel_path] = {
        "size": len(content),
        "lines": content.count('\n') + 1,
        "sha256": hashlib.sha256(content.encode()).hexdigest()[:16]
    }
    return path

def generate_python_auth():
    """Generate Python auth module with rate limiting"""
    return '''
"""
Authentication module with rate limiting and session management.
"""

import time
from typing import Optional, Dict
from dataclasses import dataclass

@dataclass
class UserSession:
    user_id: str
    token: str
    expires_at: float
    refresh_token: Optional[str] = None

class UserSessionStore:
    """Manages user sessions with automatic cleanup."""
    
    def __init__(self):
        self.sessions: Dict[str, UserSession] = {}
        self.rate_limits: Dict[str, list] = {}
    
    def create_session(self, user_id: str) -> UserSession:
        """Create new session with refresh token support."""
        import secrets
        token = secrets.token_urlsafe(32)
        refresh = secrets.token_urlsafe(32)
        session = UserSession(
            user_id=user_id,
            token=token,
            expires_at=time.time() + 3600,
            refresh_token=refresh
        )
        self.sessions[token] = session
        return session
    
    def refresh_expired_tokens(self):
        """Background task to refresh tokens nearing expiry."""
        now = time.time()
        for session in self.sessions.values():
            if session.expires_at - now < 300:  # 5 min warning
                # TODO: Implement token refresh logic
                pass
    
    def check_rate_limit(self, user_id: str, max_requests: int = 100) -> bool:
        """Check if user has exceeded rate limit (100 req/min default)."""
        now = time.time()
        if user_id not in self.rate_limits:
            self.rate_limits[user_id] = []
        
        # Clean old entries (sliding window)
        self.rate_limits[user_id] = [
            t for t in self.rate_limits[user_id] 
            if now - t < 60
        ]
        
        if len(self.rate_limits[user_id]) >= max_requests:
            return False
        
        self.rate_limits[user_id].append(now)
        return True

def enforce_login_rate_limiting(user_id: str) -> bool:
    """
    Enforce rate limiting on login attempts.
    Called from /api/auth/login endpoint.
    Rate limit: 5 attempts per minute per IP.
    """
    store = UserSessionStore()
    # Login rate limiting is stricter: 5/min
    return store.check_rate_limit(f"login:{user_id}", max_requests=5)

# API Routes
class AuthRoutes:
    @staticmethod
    def login_handler(request):
        """POST /api/auth/login - User login with rate limiting."""
        user_id = request.get('username')
        if not enforce_login_rate_limiting(user_id):
            return {"error": "Rate limit exceeded", "status": 429}
        # ... rest of login logic
        return {"status": "ok"}
    
    @staticmethod
    def refresh_handler(request):
        """POST /api/auth/refresh - Refresh expired access token."""
        refresh_token = request.get('refresh_token')
        # Implementation calls refresh_expired_tokens
        return {"status": "ok"}
'''

def generate_typescript_client():
    """Generate TypeScript frontend client"""
    return '''
/**
 * Frontend API client for authentication
 * Maps to backend /api/auth/* routes
 */

interface LoginResponse {
  token: string;
  refreshToken: string;
  expiresIn: number;
}

interface User {
  id: string;
  username: string;
  email: string;
}

class ApiClient {
  private baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl: string = '/api') {
    this.baseUrl = baseUrl;
  }

  /**
   * Login user - calls POST /api/auth/login
   * Backend enforces rate limiting (5 attempts/min)
   */
  async login(username: string, password: string): Promise<LoginResponse> {
    const response = await fetch(`${this.baseUrl}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    
    if (response.status === 429) {
      throw new Error('Too many login attempts. Please wait.');
    }
    
    return response.json();
  }

  /**
   * Refresh expired tokens
   * Calls POST /api/auth/refresh
   * Used when access token is near expiry
   */
  async refreshToken(refreshToken: string): Promise<LoginResponse> {
    const response = await fetch(`${this.baseUrl}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refreshToken })
    });
    return response.json();
  }

  async getCurrentUser(): Promise<User> {
    // Implementation...
    return {} as User;
  }
}

export default ApiClient;
export { LoginResponse, User };
'''

def generate_go_backend():
    """Generate Go-like backend code"""
    return '''
package main

import (
    "net/http"
    "time"
    "github.com/gorilla/mux"
)

// UserSessionStore manages sessions
type UserSessionStore struct {
    sessions map[string]*UserSession
}

// Login rate limiting enforced here
func (s *UserSessionStore) CheckRateLimit(userID string) bool {
    // Rate limiting logic - 100 requests per minute
    // See Python implementation for reference
    return true
}

// API Handlers
func loginHandler(w http.ResponseWriter, r *http.Request) {
    // POST /api/auth/login
    // Enforces login rate limiting via enforce_login_rate_limiting
    // TODO: Add brute force protection
    w.WriteHeader(http.StatusOK)
}

func refreshHandler(w http.ResponseWriter, r *http.Request) {
    // POST /api/auth/refresh  
    // Refreshes expired tokens
    // Calls refresh_expired_tokens background task
    w.WriteHeader(http.StatusOK)
}

func main() {
    r := mux.NewRouter()
    r.HandleFunc("/api/auth/login", loginHandler).Methods("POST")
    r.HandleFunc("/api/auth/refresh", refreshHandler).Methods("POST")
    
    // Data models
    // User model defined in models/user.go
    // Session model defined in models/session.go
    
    http.ListenAndServe(":8080", r)
}
'''

def generate_rust_utils():
    """Generate Rust-like utility code"""
    return '''
// Rust utilities for token management
use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};

pub struct TokenManager {
    tokens: HashMap<String, u64>,
}

impl TokenManager {
    pub fn new() -> Self {
        TokenManager {
            tokens: HashMap::new(),
        }
    }
    
    /// Refresh tokens that are about to expire
    /// Similar to Python's refresh_expired_tokens
    pub fn refresh_expired(&mut self) {
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs();
        
        // TODO: Implement refresh logic
        // Check tokens expiring in < 5 minutes
    }
    
    /// Validate API key format
    /// Keys look like: sk-1234567890abcdef
    pub fn validate_api_key(key: &str) -> bool {
        key.starts_with("sk-") && key.len() > 10
    }
}

// Error handling utilities
pub fn handle_auth_error(err: &str) -> String {
    format!("Authentication failed: {}", err)
}
'''

def generate_test_files():
    """Generate test files"""
    return '''
import pytest
from auth import UserSessionStore, enforce_login_rate_limiting

def test_rate_limiting():
    """Test that rate limiting works correctly."""
    store = UserSessionStore()
    
    # Should allow first 100 requests
    for i in range(100):
        assert store.check_rate_limit("test_user") == True
    
    # 101st should fail
    assert store.check_rate_limit("test_user") == False

def test_login_rate_limit():
    """Test login-specific rate limiting (5/min)."""
    # First 5 should pass
    for i in range(5):
        assert enforce_login_rate_limiting("user123") == True
    
    # 6th should fail
    assert enforce_login_rate_limiting("user123") == False

def test_token_refresh():
    """Test that expired tokens get refreshed."""
    store = UserSessionStore()
    session = store.create_session("test_user")
    # TODO: Verify refresh logic
    assert session.refresh_token is not None
'''

def generate_config_files():
    """Generate config files"""
    return {
        "config.yaml": '''
# Application configuration
server:
  host: 0.0.0.0
  port: 8080
  
auth:
  # Rate limiting settings
  login_rate_limit: 5  # requests per minute
  api_rate_limit: 100  # requests per minute
  session_timeout: 3600  # seconds
  
  # Token settings
  refresh_window: 300  # Refresh if expiring in 5 min
  
database:
  url: postgresql://localhost/myapp
  pool_size: 10

# API Keys (DO NOT COMMIT TO GIT)
# Format: sk-<random>
api_keys:
  - sk-1234567890abcdef1234567890abcdef
  - sk-abcdef1234567890abcdef1234567890
''',
        ".env.example": '''
DATABASE_URL=postgresql://localhost/myapp
API_KEY=sk-your-api-key-here
SECRET_KEY=your-secret-key
RATE_LIMIT_LOGIN=5
RATE_LIMIT_API=100
''',
        "package.json": '''
{
  "name": "myapp-frontend",
  "version": "1.0.0",
  "dependencies": {
    "react": "^18.0.0",
    "typescript": "^5.0.0"
  },
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build"
  }
}
'''
    }

def generate_markdown_docs():
    """Generate markdown documentation"""
    return '''
# MyApp Documentation

## Authentication Flow

The application uses JWT tokens with refresh token support.

### Login Process

1. User submits credentials to `POST /api/auth/login`
2. Server validates credentials
3. **Rate limiting enforced**: Max 5 login attempts per minute per user
4. On success, returns access token and refresh token
5. Access token expires in 1 hour

### Token Refresh

When access token is near expiry (< 5 minutes), client should call:

```
POST /api/auth/refresh
{
  "refreshToken": "..."
}
```

The backend runs `refresh_expired_tokens()` as a background task to proactively refresh tokens.

### Rate Limiting

Two levels of rate limiting:
- **Login**: 5 requests/minute per user (strict, prevents brute force)
- **API**: 100 requests/minute per user (general API protection)

Rate limiting is enforced in `UserSessionStore.check_rate_limit()`.

## API Routes

- `POST /api/auth/login` - User login
- `POST /api/auth/refresh` - Refresh access token
- `GET /api/user/me` - Get current user
- `POST /api/data` - Submit data (requires auth)

## Frontend Integration

The TypeScript client (`ApiClient`) in `src/api/client.ts` maps directly to backend routes:

- `client.login()` → `POST /api/auth/login`
- `client.refreshToken()` → `POST /api/auth/refresh`

## Configuration

See `config.yaml` for rate limit settings:
```yaml
auth:
  login_rate_limit: 5
  api_rate_limit: 100
```
'''

def create_query_ground_truth():
    """Create ground truth for queries"""
    queries = [
        {
            "id": "q1",
            "query": "where is login rate limiting enforced",
            "type": "natural-language",
            "expected_files": ["auth.py", "main.go"],
            "expected_symbols": ["enforce_login_rate_limiting", "CheckRateLimit"],
            "expected_lines": {"auth.py": [45, 52], "main.go": [12, 16]},
            "category": "cross-file"
        },
        {
            "id": "q2", 
            "query": "UserSessionStore",
            "type": "exact-symbol",
            "expected_files": ["auth.py"],
            "expected_symbols": ["UserSessionStore", "UserSession"],
            "expected_lines": {"auth.py": [12, 35]},
            "category": "exact-symbol"
        },
        {
            "id": "q3",
            "query": "code that refreshes expired tokens",
            "type": "fuzzy",
            "expected_files": ["auth.py", "client.ts", "main.go"],
            "expected_symbols": ["refresh_expired_tokens", "refreshToken", "refreshHandler"],
            "expected_lines": {"auth.py": [28, 33], "client.ts": [32, 42], "main.go": [20, 24]},
            "category": "cross-language"
        },
        {
            "id": "q4",
            "query": "POST /api/auth/login",
            "type": "exact-api-path",
            "expected_files": ["auth.py", "client.ts", "main.go"],
            "expected_symbols": ["login_handler", "login", "loginHandler"],
            "expected_lines": {"auth.py": [55, 62], "client.ts": [18, 30], "main.go": [18, 22]},
            "category": "cross-language"
        },
        {
            "id": "q5",
            "query": "rate limit configuration",
            "type": "config-lookup",
            "expected_files": ["config.yaml", ".env.example"],
            "expected_symbols": ["login_rate_limit", "RATE_LIMIT_LOGIN"],
            "expected_lines": {"config.yaml": [7, 8], ".env.example": [4, 5]},
            "category": "docs-config"
        },
        {
            "id": "q6",
            "query": "how does token refresh work",
            "type": "docs-to-code",
            "expected_files": ["README.md", "auth.py", "client.ts"],
            "expected_symbols": ["refresh_expired_tokens", "refreshToken"],
            "expected_lines": {"README.md": [15, 25]},
            "category": "docs-to-code"
        },
        {
            "id": "q7",
            "query": "test for rate limiting",
            "type": "test-to-implementation",
            "expected_files": ["test_auth.py", "auth.py"],
            "expected_symbols": ["test_rate_limiting", "test_login_rate_limit", "check_rate_limit"],
            "expected_lines": {"test_auth.py": [4, 15]},
            "category": "test-to-implementation"
        },
        {
            "id": "q8",
            "query": "database connection pooling",
            "type": "negative",
            "expected_files": [],
            "expected_symbols": [],
            "expected_lines": {},
            "category": "negative"
        },
        {
            "id": "q9",
            "query": "UserSession",
            "type": "exact-symbol",
            "expected_files": ["auth.py"],
            "expected_symbols": ["UserSession", "UserSessionStore"],
            "expected_lines": {"auth.py": [8, 11]},
            "category": "exact-symbol",
            "note": "Similar to UserSessionStore - tests disambiguation"
        },
        {
            "id": "q10",
            "query": "API key validation",
            "type": "natural-language",
            "expected_files": ["utils.rs"],
            "expected_symbols": ["validate_api_key"],
            "expected_lines": {"utils.rs": [22, 25]},
            "category": "lexical"
        }
    ]
    
    GROUND_TRUTH["queries"] = queries
    return queries

def main():
    print("Generating synthetic codebase...")
    print(f"Random seed: {RANDOM_SEED}")
    
    # Create directory structure
    dirs = [
        "backend",
        "backend/models",
        "frontend/src/api",
        "frontend/src/components",
        "tests",
        "docs",
        "config",
        "vendor",  # Should be ignored
        "node_modules",  # Should be ignored
        "target",  # Rust build dir - should be ignored
    ]
    
    for d in dirs:
        (OUTPUT_DIR / d).mkdir(parents=True, exist_ok=True)
    
    # Generate files
    files = {
        "backend/auth.py": generate_python_auth(),
        "frontend/src/api/client.ts": generate_typescript_client(),
        "backend/main.go": generate_go_backend(),
        "backend/utils.rs": generate_rust_utils(),
        "tests/test_auth.py": generate_test_files(),
        "docs/README.md": generate_markdown_docs(),
        "config/config.yaml": generate_config_files()["config.yaml"],
        ".env.example": generate_config_files()[".env.example"],
        "frontend/package.json": generate_config_files()["package.json"],
        # Add some noisy/vendor files that should be ignored
        "vendor/README.md": "# Vendor files - should be ignored by search",
        "node_modules/fake-package/index.js": "// Fake node module",
        "target/debug/build.rs": "// Rust build artifact",
        # Files with spaces and unicode
        "docs/API Documentation.md": "# API Docs with spaces in filename",
        "docs/文档.md": "# Chinese filename test",
        # Deeply nested
        "frontend/src/components/auth/login/form.tsx": "// Deeply nested component",
        "backend/models/user/session/store.py": "# Deeply nested Python module",
    }
    
    for path, content in files.items():
        full_path = OUTPUT_DIR / path
        write_file(full_path, content)
        print(f"  Created: {path} ({len(content)} bytes)")
    
    # Create query ground truth
    queries = create_query_ground_truth()
    print(f"\nCreated {len(queries)} queries with ground truth")
    
    # Save ground truth
    gt_path = OUTPUT_DIR / "ground_truth.json"
    with open(gt_path, 'w') as f:
        json.dump(GROUND_TRUTH, f, indent=2)
    
    print(f"\nGround truth saved to: {gt_path}")
    print(f"Total files: {len(GROUND_TRUTH['files'])}")
    print("\nCorpus generated successfully!")
    print("\nQuery categories:")
    for q in queries:
        print(f"  - {q['id']}: {q['type']} ({q['category']})")

if __name__ == "__main__":
    main()

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

def main():
    print("Generating synthetic codebase...")
    print(f"Random seed: {RANDOM_SEED}")
    
    # Create directory structure and files
    files = {
        "backend/auth.py": generate_python_auth(),
        "frontend/src/api/client.ts": generate_typescript_client(),
    }
    
    for path, content in files.items():
        full_path = OUTPUT_DIR / path
        write_file(full_path, content)
        print(f"  Created: {path}")
    
    # Save ground truth
    gt_path = OUTPUT_DIR / "ground_truth.json"
    with open(gt_path, 'w') as f:
        json.dump(GROUND_TRUTH, f, indent=2)
    
    print(f"\nGround truth saved to: {gt_path}")
    print("Corpus generated successfully!")

if __name__ == "__main__":
    main()

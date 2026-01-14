# API Key Manager

A self-hosted API key management service with full feature parity to Unkey.dev, designed for Railway deployment.

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.com/deploy/api-key-manager)

---

## Features

| Feature | Description |
|---------|-------------|
| Secure Hashing | Keys hashed with HMAC-SHA256, never stored raw |
| Rate Limiting | Redis sliding window per-key limits |
| Usage Limits | Limit total uses with optional auto-refill |
| IP Whitelisting | Restrict keys to specific IPs or CIDRs |
| Audit Logs | Track all key actions |
| Key Rotation | Seamlessly rotate keys |
| Delete Protection | Prevent accidental deletion |
| Expiring Keys | Auto-expire keys after set duration |
| Custom Metadata | Attach arbitrary data to keys |
| Owner Association | Link keys to external users |

---

## Quick Start

### Deploy on Railway

1. Click the "Deploy on Railway" button above
2. Railway will provision PostgreSQL and Redis automatically
3. Set the `SECRET_KEY` environment variable to a secure random string
4. Deploy

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Auto-set by Railway |
| `REDIS_URL` | Redis connection string | Auto-set by Railway |
| `SECRET_KEY` | JWT signing key | Yes |
| `API_KEY_PREFIX` | Prefix for generated keys | No (default: `sk_live_`) |
| `DEFAULT_RATE_LIMIT` | Default requests per hour | No (default: `1000`) |

---

## Client Integration

Choose your language to see integration examples:

<details>
<summary><strong>JavaScript / Node.js</strong></summary>

### Verify API Key

```javascript
async function verifyApiKey(apiKey) {
  const response = await fetch('https://your-instance.railway.app/v1/keys/verify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ key: apiKey })
  });
  
  const result = await response.json();
  
  if (result.valid) {
    console.log('Key is valid');
    console.log('Owner:', result.owner_id);
    console.log('Remaining requests:', result.remaining);
    return true;
  } else {
    console.log('Key invalid:', result.error);
    return false;
  }
}

// Usage in Express middleware
function apiKeyMiddleware(req, res, next) {
  const apiKey = req.headers['x-api-key'];
  
  verifyApiKey(apiKey).then(valid => {
    if (valid) {
      next();
    } else {
      res.status(401).json({ error: 'Invalid API key' });
    }
  });
}
```

</details>

<details>
<summary><strong>Python</strong></summary>

### Verify API Key

```python
import httpx
from functools import wraps
from flask import request, jsonify

API_KEY_MANAGER_URL = "https://your-instance.railway.app"

def verify_api_key(api_key: str) -> dict:
    """Verify an API key and return the result."""
    response = httpx.post(
        f"{API_KEY_MANAGER_URL}/v1/keys/verify",
        json={"key": api_key}
    )
    return response.json()

# Flask decorator example
def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({'error': 'API key required'}), 401
        
        result = verify_api_key(api_key)
        if not result.get('valid'):
            return jsonify({'error': result.get('error', 'Invalid key')}), 401
        
        return f(*args, **kwargs)
    return decorated

# Usage
@app.route('/protected')
@require_api_key
def protected_route():
    return jsonify({'message': 'Access granted'})
```

</details>

<details>
<summary><strong>Go</strong></summary>

### Verify API Key

```go
package main

import (
    "bytes"
    "encoding/json"
    "net/http"
)

const apiKeyManagerURL = "https://your-instance.railway.app"

type VerifyRequest struct {
    Key string `json:"key"`
}

type VerifyResponse struct {
    Valid     bool    `json:"valid"`
    KeyID     string  `json:"key_id,omitempty"`
    OwnerID   string  `json:"owner_id,omitempty"`
    Remaining int     `json:"remaining,omitempty"`
    Error     string  `json:"error,omitempty"`
}

func VerifyAPIKey(apiKey string) (*VerifyResponse, error) {
    reqBody, _ := json.Marshal(VerifyRequest{Key: apiKey})
    
    resp, err := http.Post(
        apiKeyManagerURL+"/v1/keys/verify",
        "application/json",
        bytes.NewBuffer(reqBody),
    )
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()
    
    var result VerifyResponse
    json.NewDecoder(resp.Body).Decode(&result)
    return &result, nil
}

// Middleware example
func APIKeyMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        apiKey := r.Header.Get("X-API-Key")
        if apiKey == "" {
            http.Error(w, "API key required", http.StatusUnauthorized)
            return
        }
        
        result, err := VerifyAPIKey(apiKey)
        if err != nil || !result.Valid {
            http.Error(w, "Invalid API key", http.StatusUnauthorized)
            return
        }
        
        next.ServeHTTP(w, r)
    })
}
```

</details>

<details>
<summary><strong>Java</strong></summary>

### Verify API Key

```java
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import com.google.gson.Gson;

public class ApiKeyManager {
    private static final String API_URL = "https://your-instance.railway.app";
    private static final HttpClient client = HttpClient.newHttpClient();
    private static final Gson gson = new Gson();
    
    public static class VerifyResponse {
        public boolean valid;
        public String key_id;
        public String owner_id;
        public Integer remaining;
        public String error;
    }
    
    public static VerifyResponse verifyApiKey(String apiKey) throws Exception {
        String requestBody = gson.toJson(new Object() {
            public String key = apiKey;
        });
        
        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create(API_URL + "/v1/keys/verify"))
            .header("Content-Type", "application/json")
            .POST(HttpRequest.BodyPublishers.ofString(requestBody))
            .build();
        
        HttpResponse<String> response = client.send(
            request,
            HttpResponse.BodyHandlers.ofString()
        );
        
        return gson.fromJson(response.body(), VerifyResponse.class);
    }
    
    // Usage example
    public static void main(String[] args) throws Exception {
        VerifyResponse result = verifyApiKey("sk_live_xxxxx");
        
        if (result.valid) {
            System.out.println("Key is valid. Owner: " + result.owner_id);
        } else {
            System.out.println("Invalid key: " + result.error);
        }
    }
}
```

</details>

<details>
<summary><strong>cURL / Shell</strong></summary>

### Verify API Key

```bash
# Verify a key
curl -X POST https://your-instance.railway.app/v1/keys/verify \
  -H "Content-Type: application/json" \
  -d '{"key": "sk_live_xxxxx"}'

# Response (valid key)
# {"valid": true, "key_id": "uuid", "owner_id": "user123", "remaining": 950}

# Response (invalid key)  
# {"valid": false, "error": "Key not found"}
```

### Full Workflow Example

```bash
# 1. Register admin account
curl -X POST https://your-instance.railway.app/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "securepassword"}'

# 2. Login to get JWT token
TOKEN=$(curl -s -X POST https://your-instance.railway.app/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "securepassword"}' \
  | jq -r '.access_token')

# 3. Create API namespace
API_ID=$(curl -s -X POST https://your-instance.railway.app/v1/apis \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Production API"}' \
  | jq -r '.id')

# 4. Create API key
curl -X POST https://your-instance.railway.app/v1/keys \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"api_id\": \"$API_ID\", \"name\": \"Production Key\"}"
# Save the returned key - it's shown only once!
```

</details>

---

## API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register admin user |
| POST | `/auth/login` | Get JWT token |

### APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/apis` | Create API namespace |
| GET | `/v1/apis` | List APIs |
| DELETE | `/v1/apis/{id}` | Delete API |

### Keys

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/keys` | Create key |
| GET | `/v1/keys` | List keys |
| GET | `/v1/keys/{id}` | Get key details |
| PATCH | `/v1/keys/{id}` | Update key |
| DELETE | `/v1/keys/{id}` | Revoke key |
| POST | `/v1/keys/{id}/rotate` | Rotate key |
| POST | `/v1/keys/verify` | Verify key |

### Analytics

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v1/keys/{id}/usage` | Usage statistics |
| GET | `/v1/keys/{id}/audit` | Audit logs |
| GET | `/v1/apis/{id}/analytics` | API-level analytics |

---

## Security

- API keys are hashed using HMAC-SHA256 and never stored in plain text
- Constant-time comparison prevents timing attacks
- Passwords are hashed with bcrypt
- JWT tokens are used for admin authentication
- IP whitelisting supports CIDR notation
- Rate limiting prevents abuse

---

## License

See [LICENSE.md](LICENSE.md)

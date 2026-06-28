# Mock HTTP Analyzer

Local placeholder analyzer for smoke testing the Home Assistant integration.

```bash
python3 server.py --host 127.0.0.1 --port 8766
```

Configure Vision ROI Guard:

- Backend: `http`
- Analyzer URL: `http://127.0.0.1:8766/analyze`
- Auth type: `none`
- Profile: `mower_safety`

The server binds to localhost by default, ignores the uploaded image, stores nothing,
and always returns a valid `safe` response.

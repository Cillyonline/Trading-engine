Closes #604

## Summary
- document /ui as the backend-served runtime operator dashboard surface
- document /owner as a frontend development-only route
- remove wording that could imply /ui and /owner are interchangeable runtime entrypoints

## Testing
- .\.venv\Scripts\python.exe -m pytest --import-mode=importlib

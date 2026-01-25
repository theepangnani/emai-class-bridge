# /test - Run Tests

Run the test suite for the EMAI project.

## Instructions

1. Run pytest for the backend
2. Run any frontend tests if available
3. Report results

## Commands

### Backend Tests
```bash
cd c:\dev\emai\emai-dev-03
python -m pytest -v
```

### Frontend Tests (if configured)
```bash
cd c:\dev\emai\emai-dev-03\frontend
npm test
```

## Notes

- Tests require the database to be available
- Some tests may require mocking Google API responses
- Use `-v` flag for verbose output
- Use `-x` flag to stop on first failure

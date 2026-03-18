# SQLAlchemy Reserved Attribute Fix

## Issue
`alembic upgrade head` failed with:
```
sqlalchemy.exc.InvalidRequestError: Attribute name 'metadata' is reserved when using the Declarative API.
```

## Root Cause
The SQLAlchemy models had columns named `metadata` which is a reserved attribute in SQLAlchemy's Declarative API.

## Solution
Renamed `metadata` column to `meta_data` in:
1. `/backend/models/repository.py` - Repository and AnalysisRun classes
2. `/backend/models/service.py` - Service class
3. `/backend/models/tech_debt.py` - TechDebtItem class

Also added missing `Integer` import to service.py

## Files Changed
- models/repository.py: metadata → meta_data (2 occurrences)
- models/service.py: metadata → meta_data (1 occurrence) + added Integer import
- models/tech_debt.py: metadata → meta_data (1 occurrence)
- Note: Neo4j queries in graph_service.py use `metadata` as property names (separate DB, no conflict)
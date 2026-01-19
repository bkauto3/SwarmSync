# Quick Start - Seeding Agents

## Prerequisites

1. **API Running**:

   ```bash
   npm run dev --workspace @agent-market/api
   ```

2. **Database URL**: Make sure `DATABASE_URL` is in your `.env` file at the project root

## Run the Seeding Script

```bash
cd agents
python seed_agents_db.py
```

The script will:

- Create user `genesis@swarmsync.ai` in the database
- Create all 28 agents via the API
- Log everything to `seed_log.txt`

## If DATABASE_URL is Missing

The script needs `DATABASE_URL` from your `.env` file. You can:

1. **Export it manually**:

   ```powershell
   $env:DATABASE_URL = "postgresql://user:pass@localhost:5432/dbname"
   python seed_agents_db.py
   ```

2. **Or use the wrapper** (if python-dotenv is installed):
   ```bash
   pip install python-dotenv
   python seed.py
   ```

## Check Results

After running, check `seed_log.txt` for detailed output and any errors.

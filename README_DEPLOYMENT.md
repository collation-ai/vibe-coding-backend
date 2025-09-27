# Deployment Guide

## Local Development Setup

### 1. Create Virtual Environment

```bash
# Option 1: Use the setup script (Recommended)
chmod +x setup.sh
./setup.sh

# Option 2: Manual setup
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
# Edit .env with your Azure PostgreSQL credentials
```

### 3. Initialize Database

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Run database initialization
python scripts/init_db.py
```

Save the generated API key - it cannot be retrieved again!

### 4. Test Locally

```bash
# Install Vercel CLI globally
npm install -g vercel

# Run local development server
vercel dev
# Follow prompts to link to your Vercel project
```

## GitHub + Vercel Deployment

### 1. Push to GitHub

```bash
# Initialize git repository
git init
git add .
git commit -m "Initial commit: Vibe Coding Backend"

# Create repository on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/vibe-coding-backend.git
git branch -M main
git push -u origin main
```

### 2. Connect to Vercel

1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Click "New Project"
3. Import your GitHub repository
4. Configure project:
   - **Framework Preset**: Other
   - **Root Directory**: `./` (leave as is)
   - **Build Command**: `pip install -r requirements.txt` (auto-detected)
   - **Output Directory**: `./` (leave as is)

### 3. Configure Environment Variables in Vercel

In your Vercel project settings, add these environment variables:

```
MASTER_DB_URL = postgresql://user:password@your-server.database.azure.com:5432/master_db?sslmode=require
AZURE_DB_HOST = your-server.database.azure.com
AZURE_DB_PORT = 5432
AZURE_DB_USER = your_admin_user
AZURE_DB_PASSWORD = your_admin_password
AZURE_DB_SSL = require
ENCRYPTION_KEY = [generate using: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"]
API_KEY_SALT = [generate using: python -c "import secrets; print(secrets.token_urlsafe(32))"]
MAX_QUERY_TIME_SECONDS = 30
MAX_ROWS_PER_QUERY = 10000
DEFAULT_PAGE_SIZE = 100
LOG_LEVEL = INFO
ENABLE_AUDIT_LOGS = true
```

### 4. Deploy

Once connected, Vercel will automatically deploy:
- On every push to `main` branch (Production)
- On every pull request (Preview deployments)

### 5. Post-Deployment Setup

After deployment, initialize your production database:

1. Run the SQL script on your Azure PostgreSQL master database:
```sql
-- Connect to your Azure PostgreSQL and run scripts/init_db.sql
```

2. Create production users and API keys using the admin scripts or directly in the database

## Vercel Project Structure

```
vibe-coding-backend/
├── api/                    # Vercel serverless functions
│   ├── health.py          # /api/health endpoint
│   ├── auth/
│   │   └── validate.py    # /api/auth/validate endpoint
│   ├── tables/
│   │   └── index.py       # /api/tables endpoints
│   └── data/
│       └── [schema]/
│           └── [table].py # Dynamic routes for data operations
├── lib/                   # Shared libraries (imported by api/)
├── schemas/               # Pydantic models
├── scripts/               # Setup and utility scripts
├── requirements.txt       # Python dependencies
├── vercel.json           # Vercel configuration
└── .env                  # Local environment variables (not committed)
```

## Automatic Deployments

### Production Deployments
- Triggered on push to `main` branch
- URL: `https://your-project.vercel.app`

### Preview Deployments
- Triggered on pull requests
- URL: `https://your-project-pr-number.vercel.app`

### Branch Deployments
- Each branch gets its own URL
- URL: `https://your-project-branch-name.vercel.app`

## Environment Management

### Development
```bash
# .env file for local development
cp .env.example .env
# Edit with development database
```

### Staging (Optional)
- Create a `staging` branch
- Set different environment variables in Vercel for staging

### Production
- Environment variables set in Vercel dashboard
- Secrets are encrypted and secure

## Monitoring

### Vercel Dashboard
- View function logs
- Monitor performance
- Check error rates

### Database Logs
Query the audit_logs table:
```sql
SELECT * FROM audit_logs 
WHERE created_at > NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC;
```

## Troubleshooting

### Build Failures
1. Check Python version (must be 3.9 for Vercel)
2. Verify all dependencies in requirements.txt
3. Check Vercel build logs

### Runtime Errors
1. Check function logs in Vercel dashboard
2. Verify environment variables are set
3. Ensure database is accessible from Vercel

### Database Connection Issues
1. Whitelist Vercel IP ranges in Azure PostgreSQL firewall
2. Ensure SSL mode is set to 'require'
3. Verify connection string format

## Security Best Practices

1. **Never commit .env file** - It's in .gitignore
2. **Use Vercel environment variables** for production secrets
3. **Rotate API keys regularly**
4. **Enable audit logging** in production
5. **Use branch protection** on GitHub main branch
6. **Enable 2FA** on GitHub and Vercel accounts

## CI/CD Workflow

### Recommended Git Workflow

1. Create feature branch
```bash
git checkout -b feature/new-endpoint
```

2. Make changes and test locally
```bash
vercel dev
```

3. Commit and push
```bash
git add .
git commit -m "Add new endpoint"
git push origin feature/new-endpoint
```

4. Create Pull Request on GitHub
   - Vercel creates preview deployment
   - Test preview deployment
   - Merge to main after review

5. Automatic production deployment

## Useful Commands

```bash
# View Vercel logs
vercel logs

# List environment variables
vercel env ls

# Add environment variable
vercel env add VARIABLE_NAME

# Promote preview to production
vercel promote [deployment-url]

# Rollback to previous deployment
vercel rollback [deployment-url]
```

## Support

For deployment issues:
- Check [Vercel Documentation](https://vercel.com/docs)
- Review [Vercel Python Guide](https://vercel.com/docs/functions/runtimes/python)
- Check GitHub Actions logs if using CI/CD
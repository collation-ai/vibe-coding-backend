# Critical Fix - Deploy to Azure

## Issue Fixed
The API was returning "Internal Server Error" due to datetime objects not being JSON serializable.

## Root Cause
When error responses were created, the `.dict()` method on Pydantic models wasn't properly serializing datetime objects to strings.

## Solution Applied
Changed all occurrences of `error_response.dict()` to `error_response.model_dump(mode="json")` in:
- `/api/auth/validate.py`

## Files Changed
```bash
# File: api/auth/validate.py
# Changes: 4 lines modified
# - Line 58: error_response.dict() → error_response.model_dump(mode="json")
# - Line 111: error_response.dict() → error_response.model_dump(mode="json")
# - Line 144: error_response.dict() → error_response.model_dump(mode="json")
# - Line 196: error_response.dict() → error_response.model_dump(mode="json")
```

## Testing Status
✅ Local testing shows the fix works for the main success path
⚠️ Azure deployment still needs the fix applied

## To Deploy
1. Push the commit `0065bf2` to GitHub:
   ```bash
   git push origin vercel-update
   ```

2. Wait for Azure deployment (approximately 30 minutes)

3. Test the fix is deployed:
   ```bash
   # Test tanmais permissions (should work)
   curl -X GET "https://vibe-coding-backend.azurewebsites.net/api/auth/permissions" \
     -H "X-API-Key: vibe_prod_W35LmyakTWrQ3x2Yc0DUxKLB0dQFPleZ"
   
   # Test freshwaterapiuser permissions via X-User-Id (should work)
   curl -X GET "https://vibe-coding-backend.azurewebsites.net/api/auth/permissions" \
     -H "X-API-Key: vibe_prod_W35LmyakTWrQ3x2Yc0DUxKLB0dQFPleZ" \
     -H "X-User-Id: d4a34dc6-6699-4183-b068-6c7832291e4b"
   ```

## Expected Result
After deployment, freshwaterapiuser should see:
- Database: `cdb_written_976_poetry` (their granted database)
- NOT just `master_db` (which was the original issue)

## Current Git Status
- Branch: `vercel-update`
- Unpushed commits: 3 (including the fix)
- Commit ready to deploy: `0065bf2`
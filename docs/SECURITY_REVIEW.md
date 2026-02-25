# Security Review - Actions Required Before Making Repository Public

**Review Date:** 2026-01-08
**Status:** ⚠️ CRITICAL ISSUES FOUND - DO NOT MAKE PUBLIC YET

---

## 🚨 CRITICAL SECURITY ISSUES

### 1. EXPOSED API KEYS IN LOCAL .env FILES

**Status:** ✅ Good - Files are gitignored and NOT in git history
**Risk:** 🔴 CRITICAL if accidentally committed

**Files containing live credentials:**
- `.env` (root directory)
  - OpenAI API Key (Enterprise): `sk-proj-L7kW5ffEg7VT_WoqVPuO...`
  - Google/Gemini API Keys: `AIzaSyAbxg8f_DZ6KfYxpaG...`
  - Anthropic API Key: `sk-ant-api03-m60QShDSLuWDH...`
  - LangSmith API Key: `lsv2_pt_ab7b9dc2bfd44...`
  - Confident AI API Key: `confident_us_AZSeylZXRXRz...`
  - Neo4j Password: `neo4j@openspg`

- `notebooks/.env`
  - OpenAI API Key: `sk-proj-W5X2h7RQLQvTmnH5zisN...`
  - Confident AI API Key: `confident_us_AZSeylZXRXRz...`

**ACTION REQUIRED:**
1. ✅ Files are already in .gitignore - DO NOT REMOVE THEM FROM .gitignore
2. 🔴 Before making repo public, ROTATE ALL API KEYS (they're in this report, so consider them exposed)
3. ✅ Keep using .env.example files as templates (already tracked, good practice)

---

### 2. HARDCODED SECRETS IN SOURCE CODE

**Status:** 🔴 TRACKED IN GIT - Will be public

#### File: `server/api/routes/auth.py`

**Line 11:** Hardcoded JWT Secret Key
```python
SECRET_KEY = "your-secret-key-change-in-production"
```

**Line 38:** Mock authentication credentials
```python
"hashed_password": "fakehashedsecret",
```

**Line 88:** Hardcoded test password (check full file)
```python
if not user or form_data.password != "secret":
```

**RISK:** Low for demo/test code, but indicates this is not production-ready

**ACTION REQUIRED:**
1. ✅ ACCEPTABLE for demo code - clearly marked as "change-in-production"
2. ⚠️ Add comment/documentation that this is for development only
3. Consider removing mock auth entirely or move to separate demo config

---

### 3. HARDCODED DATABASE CREDENTIALS

#### File: `server/core/config.py`

**Lines 56-59:** Default Neo4j credentials in code
```python
"uri": "bolt://localhost:7687",
"username": "neo4j",
"password": "neo4j@openspg",
"database": "financebench1",
```

**RISK:** Medium - exposes default database password

**ACTION REQUIRED:**
1. 🔴 REMOVE hardcoded password from config.py
2. ✅ Use environment variables only
3. Update .env.example with placeholder: `NEO4J_PASSWORD=your_password_here`

---

## 📁 FILES TO DELETE BEFORE MAKING PUBLIC

### Large Cache/Temporary Files (Not in git, but should be cleaned)

**Total Size: ~326 MB**

1. **`.langgraph_api/` (270 MB)**
   - Contains: Runtime state, checkpoints, conversation history
   - Status: ✅ Already in .gitignore
   - Action: Keep gitignored, safe to delete locally to reduce repo size
   - Command: `rm -rf .langgraph_api/`

2. **`notebooks/.result/` (46 MB)**
   - Contains: Test result CSV files, evaluation outputs
   - Status: ✅ Covered by `notebooks/.*` in .gitignore
   - Action: Delete before sharing, may contain test data
   - Command: `rm -rf notebooks/.result/`

3. **`notebooks/.deepeval/` (10 MB)**
   - Contains: Evaluation cache, telemetry data
   - Status: ✅ Covered by `notebooks/.*` in .gitignore
   - Action: Safe to delete
   - Command: `rm -rf notebooks/.deepeval/`

4. **`notebooks/.claudedocs/` (52 KB)**
   - Contains: Claude documentation cache
   - Status: ✅ Covered by `notebooks/.*` in .gitignore
   - Action: Safe to delete
   - Command: `rm -rf notebooks/.claudedocs/`

5. **Large Jupyter Notebooks with Execution Output:**
   - `notebooks/evaluation_with_deepeval copy.ipynb` (8.8 MB) - backup copy
   - `notebooks/evaluation_with_deepeval.ipynb` (841 KB)
   - `notebooks/financebench_eda.ipynb` (1 MB)

   **Action:** Clear outputs before committing
   ```bash
   jupyter nbconvert --clear-output --inplace notebooks/*.ipynb
   ```

---

## 🗑️ FILES TO REMOVE FROM GIT TRACKING

### Untracked Files to Review

These files are currently untracked (`??` in git status) and should be reviewed:

```
D check_import.py          # Delete or keep?
D check_sse_type.py       # Delete or keep?
D inspect_mcp.py          # Delete or keep?
D inspect_sse.py          # Delete or keep?
D verify_mcp.py           # Delete or keep?
?? knowledge_graphs/schema/financebench_schema_viz.md
?? notebooks/append_*.py   # Multiple utility scripts - organize or delete
?? notebooks/insert_dataset_description.py
?? notebooks/inspect_question_types.py
?? notebooks/modify_nb.py
?? vietnamese_finance_qa_test.md
```

**ACTION REQUIRED:**
1. Review each deleted file (marked with `D`) - are they needed?
2. Move `notebooks/*.py` scripts to proper `scripts/` directory or delete
3. Review markdown files for sensitive information
4. Run: `git status` and handle each untracked file

---

## 🔒 RECOMMENDED .gitignore ADDITIONS

Your .gitignore is mostly good, but consider adding:

```gitignore
# Additional entries to add:

# Jupyter notebook checkpoints and outputs
*.ipynb_checkpoints
*-checkpoint.ipynb

# Backup files
*.bak
*.backup
*copy*.ipynb
*Copy*.ipynb

# Editor swap files
*.swp
*.swo
*~

# OS files (add to root level)
**/.DS_Store
.DS_Store

# Package manager locks (optional - decide if you want to track uv.lock)
# uv.lock

# Local development files
.vscode/
.idea/
*.local

# Test outputs
test-results/
.pytest_cache/
htmlcov/
```

---

## ✅ SECURITY CHECKLIST BEFORE GOING PUBLIC

### Pre-Publication Checklist

- [ ] **1. ROTATE ALL API KEYS**
  - [ ] OpenAI API Keys (3 different keys found)
  - [ ] Google/Gemini API Keys (2 keys)
  - [ ] Anthropic API Key
  - [ ] LangSmith API Key
  - [ ] Confident AI API Key
  - [ ] Update .env files with new keys (keep files local only)

- [ ] **2. CLEAN TRACKED FILES**
  - [ ] Remove hardcoded password from `server/core/config.py:56-59`
  - [ ] Add warning comments to `server/api/routes/auth.py` about demo-only code
  - [ ] Clear all Jupyter notebook outputs: `jupyter nbconvert --clear-output --inplace notebooks/*.ipynb`

- [ ] **3. DELETE LARGE CACHE FILES**
  ```bash
  rm -rf .langgraph_api/
  rm -rf notebooks/.result/
  rm -rf notebooks/.deepeval/
  rm -rf notebooks/.claudedocs/
  ```

- [ ] **4. REVIEW UNTRACKED FILES**
  - [ ] Delete or organize files marked with `D` in git status
  - [ ] Move/delete `notebooks/*.py` utility scripts
  - [ ] Review `vietnamese_finance_qa_test.md` for sensitive info

- [ ] **5. VERIFY .env FILES**
  - [ ] Confirm `.env` is in .gitignore: ✅ Already there (line 18)
  - [ ] Confirm `notebooks/.env` covered by .gitignore: ✅ Covered by `notebooks/.*` (line 46)
  - [ ] Double-check with: `git ls-files | grep "\.env$"` (should be empty)

- [ ] **6. SCAN GIT HISTORY**
  ```bash
  # Check if any secrets were ever committed
  git log --all --full-history --source -- .env
  git log --all --full-history --source -- notebooks/.env

  # Scan for potential secrets in commits
  git log -p | grep -i "api_key\|secret\|password" | head -20
  ```

- [ ] **7. ADD SECURITY DOCUMENTATION**
  - [ ] Create `.env.example` if missing (✅ Already exists)
  - [ ] Add README section on environment setup
  - [ ] Document which API keys are needed
  - [ ] Add security policy (SECURITY.md)

- [ ] **8. OPTIONAL: USE SECRET SCANNING TOOLS**
  ```bash
  # Install and run git-secrets or gitleaks
  brew install gitleaks
  gitleaks detect --source . --verbose
  ```

- [ ] **9. CREATE INITIAL PUBLIC COMMIT**
  - [ ] Clean working directory
  - [ ] Commit all necessary changes
  - [ ] Review final `git log` before pushing

- [ ] **10. FINAL VERIFICATION**
  - [ ] Clone repo to new directory to verify what others will see
  - [ ] Check that no .env files are present
  - [ ] Verify no hardcoded secrets remain
  - [ ] Test that application runs with environment variables only

---

## 🎯 IMMEDIATE ACTIONS (IN ORDER)

### Step 1: Backup Current State
```bash
# Create a backup branch
git checkout -b pre-public-backup
git add -A
git commit -m "Backup before public release preparation"
git checkout dev
```

### Step 2: Rotate API Keys
Go to each service and regenerate:
1. OpenAI: https://platform.openai.com/api-keys
2. Google AI Studio: https://makersuite.google.com/app/apikey
3. Anthropic: https://console.anthropic.com/settings/keys
4. LangSmith: https://smith.langchain.com/settings
5. Confident AI: https://confident-ai.com/

### Step 3: Clean Repository
```bash
# Delete cache directories
rm -rf .langgraph_api/ notebooks/.result/ notebooks/.deepeval/ notebooks/.claudedocs/

# Clear notebook outputs
jupyter nbconvert --clear-output --inplace notebooks/*.ipynb

# Review deleted files
git status | grep "^D"
```

### Step 4: Fix Hardcoded Credentials
Edit these files:
- `server/core/config.py` - Remove hardcoded password on lines 56-59
- `server/api/routes/auth.py` - Add warnings about demo-only code

### Step 5: Final Verification
```bash
# Check what will be public
git ls-files | xargs grep -l "sk-proj\|sk-ant\|AIza" || echo "No API keys found"

# Verify .env files not tracked
git ls-files | grep "\.env$" || echo "Good - no .env files tracked"

# Check repo size
du -sh .git/
```

### Step 6: Test Clean Clone
```bash
cd /tmp
git clone /Users/duykhangh/Work/HCMUT/thesis-llms-multilayer-graph test-public-repo
cd test-public-repo
ls -la  # Verify no .env files
cat server/core/config.py | grep -i password  # Should not show real password
```

---

## 📊 RISK ASSESSMENT SUMMARY

| Category | Risk Level | Status | Action Required |
|----------|-----------|---------|-----------------|
| API Keys in .env | 🔴 CRITICAL | ✅ Gitignored | Rotate all keys |
| Hardcoded DB Password | 🟡 MEDIUM | 🔴 In git | Remove from code |
| Demo Auth Secrets | 🟢 LOW | 🟡 Acceptable | Add warnings |
| Large Cache Files | 🟡 MEDIUM | ✅ Gitignored | Delete locally |
| Notebook Outputs | 🟡 MEDIUM | 🔴 Some tracked | Clear outputs |
| Git History | ✅ CLEAN | ✅ Clean | Verify scan |

**Overall Risk:** 🟡 MEDIUM - Safe to make public AFTER completing checklist above

---

## 📝 ADDITIONAL RECOMMENDATIONS

### For Production Deployment
1. Use proper secrets management (AWS Secrets Manager, Azure Key Vault, etc.)
2. Implement API key rotation policy
3. Add rate limiting to API endpoints
4. Enable audit logging for sensitive operations
5. Use service accounts with minimal permissions
6. Consider adding .github/workflows/secret-scanning.yml

### For Documentation
1. Add SECURITY.md with vulnerability reporting process
2. Document all required environment variables in README
3. Create deployment guide with security best practices
4. Add LICENSE file if not present
5. Consider CODE_OF_CONDUCT.md for community guidelines

### For Development
1. Use pre-commit hooks to prevent committing secrets
2. Enable GitHub secret scanning (automatically enabled for public repos)
3. Consider using encrypted secrets for CI/CD
4. Implement proper authentication for production deployment
5. Review and update dependencies regularly

---

## 🔗 USEFUL COMMANDS

```bash
# Find all large files in git history
git rev-list --objects --all |
  git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' |
  sed -n 's/^blob //p' |
  sort --numeric-sort --key=2 --reverse |
  head -20

# Remove file from git history (if needed)
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch PATH_TO_FILE' \
  --prune-empty --tag-name-filter cat -- --all

# Scan for secrets (install gitleaks first)
gitleaks detect --source . --report-path gitleaks-report.json

# Check current repo status
git status --ignored
git ls-files --others --ignored --exclude-standard
```

---

**Generated:** 2026-01-08
**Tool:** Claude Code Security Review
**Next Review:** After completing checklist and before making repository public

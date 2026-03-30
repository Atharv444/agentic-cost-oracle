# Agentic Cost-Oracle GitHub Action

**AI-powered cloud cost optimization that runs on every Pull Request.**

Cost-Oracle automatically detects infrastructure changes in your PRs, calculates the cost impact using [Infracost](https://www.infracost.io/), sends the data to an LLM (Llama-3 via Groq), and posts a smart, human-like optimization report as a PR comment.

---

## Quick Start

### 1. Get API Keys (Free)

| Service | Purpose | Sign Up |
|---------|---------|---------|
| **Infracost** | Cloud cost estimation | [infracost.io/pricing](https://www.infracost.io/pricing/) |
| **Groq** | LLM inference (Llama-3) | [console.groq.com](https://console.groq.com/) |

### 2. Add Secrets to Your Repo

Go to **Settings > Secrets and variables > Actions** and add:

```
INFRACOST_API_KEY  = your_infracost_api_key
GROQ_API_KEY       = your_groq_api_key
```

`GITHUB_TOKEN` is provided automatically by GitHub Actions.

### 3. Copy the Workflow

Copy `.github/workflows/cost-oracle.yml` and the `app/` directory into your repository.

### 4. Push and Open a PR

Make any change to a `.tf`, `.yaml`, or `docker-compose` file and open a Pull Request. Cost-Oracle will automatically analyse the cost impact and post a comment.

---

## How It Works

```
 Developer pushes infra changes
            |
            v
 +---------------------+
 | GitHub Actions       |
 | (cost-oracle.yml)    |
 +----------+----------+
            |
     +------+------+
     |             |
     v             v
 +--------+   +--------+
 |Infracost|   |Infracost|
 |  BASE   |   |   PR   |
 +----+----+   +----+---+
      |             |
      +------+------+
             |
             v
   +---------+---------+
   | infracost diff     |
   | (JSON output)      |
   +---------+---------+
             |
             v
   +---------+---------+
   | infracost_parser   |
   | (Python module)    |
   +---------+---------+
             |
             v
   +---------+---------+
   | llm_agent          |
   | (Groq / Llama-3)   |
   +---------+---------+
             |
             v
   +---------+---------+
   | commenter          |
   | (GitHub API)       |
   +---------+---------+
             |
             v
   +-------------------+
   | PR Comment Posted  |
   | with AI analysis   |
   +-------------------+
```

---

## Project Structure

```
agentic-cost-oracle/
|-- .github/
|   +-- workflows/
|       +-- cost-oracle.yml        # GitHub Actions workflow
|-- app/
|   |-- __init__.py                # Package init
|   |-- config.py                  # Centralised configuration
|   |-- infracost_parser.py        # Infracost JSON parser
|   |-- llm_agent.py               # LLM provider (Groq + HF fallback)
|   |-- commenter.py               # GitHub PR comment manager
|   +-- main.py                    # Pipeline orchestrator
|-- examples/
|   |-- terraform/
|   |   |-- main.tf                # Sample AWS infrastructure
|   |   +-- cost-increase.tfvars   # Vars that trigger cost alerts
|   +-- kubernetes/
|       +-- deployment.yaml        # Sample K8s manifests
|-- Dockerfile                     # Production container
|-- requirements.txt               # Python dependencies
|-- .gitignore
+-- README.md
```

---

## Component Responsibilities

| Module | Responsibility |
|--------|---------------|
| `config.py` | Loads and validates all environment variables into an immutable dataclass |
| `infracost_parser.py` | Parses Infracost JSON (breakdown + diff formats) into structured Python objects |
| `llm_agent.py` | Sends cost data to Groq (primary) or HuggingFace (fallback) with a carefully engineered system prompt |
| `commenter.py` | Creates or **updates** (no spam) a PR comment via the GitHub REST API |
| `main.py` | Orchestrates the full pipeline with threshold checks and error handling |

---

## Configuration

All configuration is via environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GITHUB_TOKEN` | Yes | - | GitHub token for PR comments |
| `REPO_FULL_NAME` | Yes | - | `owner/repo` format |
| `PR_NUMBER` | Yes | - | Pull request number |
| `GROQ_API_KEY` | Yes* | - | Groq API key |
| `HF_API_KEY` | No | - | HuggingFace API key (fallback) |
| `LLM_PROVIDER` | No | `groq` | Primary LLM provider |
| `LLM_MODEL` | No | `llama-3.3-70b-versatile` | Model identifier |
| `COST_THRESHOLD_PCT` | No | `5.0` | Min % change to trigger full analysis |
| `DRY_RUN` | No | `false` | Write comment to file instead of posting |

*Required unless using HuggingFace as primary provider.

---

## Example PR Comment Output

> ## :crystal_ball: Agentic Cost-Oracle Report
>
> <details>
> <summary><b>Raw Cost Data</b></summary>
>
> ```
> Previous monthly cost : $88.40
> New monthly cost      : $1,198.72
> Monthly cost change   : +$1,110.32
> Percentage change     : +1255.7%
> Resources affected    : 4
> ```
> </details>
>
> ### Cost Impact Summary
> This PR increases monthly infrastructure costs by **$1,110.32** (+1,256%), primarily driven by
> upgrading the EC2 instance from `t3.medium` to `m5.2xlarge` and the RDS instance from
> `db.t3.medium` to `db.r6g.2xlarge`. These are significant jumps that warrant careful review.
>
> ### Resource Analysis
> | Resource | Change | Justified? |
> |----------|--------|-----------|
> | `aws_instance.web` | $30/mo -> $280/mo | Likely over-provisioned for staging |
> | `aws_db_instance.main` | $58/mo -> $830/mo | 14x increase without workload justification |
>
> ### Optimisation Recommendations
> 1. **Use `t3.xlarge` instead of `m5.2xlarge`** for the web server — saves ~$150/mo with comparable performance for web workloads.
> 2. **Use `db.r6g.large` instead of `db.r6g.2xlarge`** — saves ~$550/mo. Start smaller and scale up based on CloudWatch metrics.
> 3. **Enable Reserved Instance pricing** for production — 1-year RI on `m5.2xlarge` saves ~30%.
> 4. **Consider Aurora Serverless v2** instead of provisioned RDS for variable workloads.
>
> ### Anti-Pattern Alerts
> - Staging environment using production-grade instances
> - No auto-scaling configured for EC2
> - NAT Gateway running 24/7 (consider VPC endpoints for S3/DynamoDB)
>
> ### Confidence Score
> 85/100 -- High confidence based on standard AWS pricing; verify actual workload requirements.
>
> ---
> *Powered by Agentic Cost-Oracle | Model: `llama-3.3-70b-versatile` via groq*

---

## AI Prompt Design

The system prompt in `llm_agent.py` is engineered for:

| Aspect | Design Choice |
|--------|--------------|
| **Role** | MLOps + FinOps cost optimization expert |
| **Input** | Structured cost table (not raw JSON) |
| **Temperature** | 0.3 (factual, low hallucination) |
| **Output format** | Enforced Markdown sections |
| **Guardrails** | "Never fabricate prices", "say estimated if unsure" |
| **Scoring** | Confidence score (0-100) for transparency |

---

## Error Handling

| Scenario | Behaviour |
|----------|-----------|
| Infracost diff missing | Falls back to PR breakdown JSON |
| Both Infracost files missing | Exits with error (no comment spam) |
| Groq API fails | Auto-fallback to HuggingFace Inference API |
| All LLM providers fail | Posts raw cost data with warning badge |
| Cost change below threshold | Posts minimal "no significant change" comment |
| Existing bot comment found | Updates in-place (no duplicate comments) |

---

## Local Development

```bash
# Clone
git clone https://github.com/your-org/agentic-cost-oracle.git
cd agentic-cost-oracle

# Install deps
pip install -r requirements.txt

# Set environment
export GROQ_API_KEY="your-key"
export GITHUB_TOKEN="your-token"
export REPO_FULL_NAME="owner/repo"
export PR_NUMBER="1"
export DRY_RUN="true"

# Generate test Infracost data
infracost breakdown --path=examples/terraform --format=json --out-file=/tmp/infracost-pr.json

# Run
python -m app.main
```

---

## Docker

```bash
docker build -t cost-oracle .
docker run --rm \
  -e GROQ_API_KEY="..." \
  -e GITHUB_TOKEN="..." \
  -e REPO_FULL_NAME="owner/repo" \
  -e PR_NUMBER="1" \
  -e DRY_RUN="true" \
  cost-oracle
```

---

## System Design (Startup-Ready Architecture)

### Current MVP Architecture

```
+------------------+     +-------------+     +-----------+     +------------+
|  GitHub Actions   | --> |  Infracost  | --> |  Llama-3  | --> |  PR Comment|
|  (event trigger)  |     |  (cost API) |     |  (Groq)   |     |  (GH API)  |
+------------------+     +-------------+     +-----------+     +------------+
```

### Scaled SaaS Architecture

```
+------------------+     +------------------+     +------------------+
|   GitHub App     |     |   GitLab Webhook  |     |  Bitbucket App   |
+--------+---------+     +--------+---------+     +--------+---------+
         |                        |                        |
         +------------------------+------------------------+
                                  |
                         +--------v--------+
                         |   API Gateway   |
                         |   (FastAPI)     |
                         +--------+--------+
                                  |
              +-------------------+-------------------+
              |                   |                   |
    +---------v-------+  +--------v--------+  +-------v---------+
    |  Cost Engine    |  |  LLM Orchestrator|  |  Policy Engine  |
    |  (Infracost +   |  |  (Multi-model    |  |  (Custom rules  |
    |   cloud APIs)   |  |   routing)       |  |   + thresholds) |
    +---------+-------+  +--------+--------+  +-------+---------+
              |                   |                   |
              +-------------------+-------------------+
                                  |
                         +--------v--------+
                         |   PostgreSQL    |
                         |   (cost history |
                         |    + analytics) |
                         +--------+--------+
                                  |
                    +-------------+-------------+
                    |                           |
           +--------v--------+         +--------v--------+
           |   Dashboard     |         |   Slack/Teams   |
           |   (Next.js)     |         |   Notifications |
           +-----------------+         +-----------------+
```

### SaaS Features

| Feature | Description |
|---------|-------------|
| **Multi-tenant** | Organisation-level isolation with team-based access |
| **Cost History** | Track cost trends across all PRs over time |
| **Budget Alerts** | Notify when cumulative PR costs exceed budgets |
| **Policy Engine** | Custom rules (e.g. "block PRs over $500/mo increase") |
| **Dashboard** | Visual cost trends, top spenders, savings leaderboard |
| **Multi-cloud** | AWS, GCP, Azure cost APIs |
| **Multi-SCM** | GitHub, GitLab, Bitbucket |
| **Auto-fix** | Suggest and apply cheaper alternatives via PR suggestions |

### Pricing Model

| Tier | Price | Includes |
|------|-------|----------|
| **Free** | $0/mo | 50 PR analyses/mo, 1 repo |
| **Team** | $49/mo | 500 analyses/mo, 10 repos, dashboard |
| **Business** | $199/mo | Unlimited, policy engine, SSO, priority support |
| **Enterprise** | Custom | Self-hosted, custom models, dedicated support |

### Competitive Positioning

| Competitor | Gap We Fill |
|------------|-------------|
| Infracost (standalone) | No AI analysis, no optimisation suggestions |
| Env0 | Expensive, no LLM-powered insights |
| Spacelift | Focused on orchestration, not cost intelligence |
| Vantage | Post-deploy only, no PR-level prevention |

**Our edge**: AI-native, shift-left cost prevention at the PR level.

---

## Auto-Fix Approach

The auto-fix system (roadmap feature) works by:

1. **LLM generates a fix suggestion** as a structured JSON patch
2. **Parser validates** the patch against the original infra file
3. **GitHub Suggestions API** posts the fix as a reviewable code suggestion
4. **Developer accepts/rejects** each suggestion individually

```python
# Future: Auto-fix payload structure
{
    "file": "main.tf",
    "line_start": 52,
    "line_end": 52,
    "original": '  instance_type = "m5.2xlarge"',
    "suggestion": '  instance_type = "t3.xlarge"',
    "reason": "Saves ~$150/mo with comparable web workload performance",
    "confidence": 0.82
}
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

**Built for the future of FinOps.** Stop overpaying for cloud infrastructure.

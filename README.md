# Primary Prospect Scout

Researches **biotech companies**, scores them against Primary's ICP, and generates personalized outbound sequences — framed around runway extension, the core pain for every biotech founder.

Built as part of a growth teardown for Primary's Growth Generalist role — see [`teardown.md`](teardown.md) for the full strategic brief.

## What it does

1. **Filters** each company — non-biotech companies are skipped automatically
2. **Researches** each biotech company using Claude's web search
3. **Scores** them 0–100 against Primary's ICP (funding stage, cash balance, international ops, treasury need)
4. **Generates** a 3-email outbound sequence for the top-scoring prospect, framed around extending runway

## Setup

```bash
pip install anthropic rich gspread
export ANTHROPIC_API_KEY=your_key_here
```

For Google Sheets output, a one-time OAuth flow is required on first use:
1. Go to [Google Cloud Console](https://console.cloud.google.com) → APIs & Services → Credentials
2. Create an **OAuth 2.0 Client ID** (Desktop app) and download the JSON
3. Save it to `~/.config/gspread/credentials.json`
4. On first `--sheets` run, a browser window opens to authenticate — token is then cached

## Usage

Score companies (non-biotech are skipped automatically):
```bash
python prospect_scout.py "Canva" "Vaxine" "Umbo"
```

Score + generate outreach for the top prospect:
```bash
python prospect_scout.py "Vaxine" "Umbo" "Halo Diagnostics" --email
```

Score + save results to a Google Sheet:
```bash
python prospect_scout.py "Vaxine" "Umbo" --sheets YOUR_SHEET_ID
```

## Example output

```
  Primary — ICP Scoring
 ┌──────────────────────┬──────────┬──────────────────┬──────────────────────────────────┐
 │ Company              │  Score   │ Contact          │ Trigger                          │
 ├──────────────────────┼──────────┼──────────────────┼──────────────────────────────────┤
 │ ● Vaxine             │ 84/100   │ CFO              │ $28M Series B, AU/US dual-entity │
 │ ◐ Halo Diagnostics   │ 51/100   │ Head of Finance  │ $9M Series A, expanding to UK    │
 │ — Canva              │ skipped  │ —                │ not biotech                      │
 └──────────────────────┴──────────┴──────────────────┴──────────────────────────────────┘
```

## How this connects to the growth strategy

The tool automates the first three steps of the **funding-trigger outbound** playbook from the teardown:

1. Identify biotech companies that recently raised → run through Prospect Scout
2. Score against ICP → prioritize outreach
3. Generate runway-focused outreach → human reviews and sends

Biotech is a high-conviction vertical for Primary: pre-revenue companies sitting on large raise proceeds with zero yield, burning cash toward milestones. Every month of extra runway matters.

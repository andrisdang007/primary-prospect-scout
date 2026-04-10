# Primary Prospect Scout

Researches companies, scores them against Primary's ICP, and generates personalized outbound sequences.

Built as part of a growth teardown for Primary's Growth Generalist role — see [`teardown.md`](teardown.md) for the full strategic brief.

## What it does

1. **Researches** each company using Claude's web search
2. **Scores** them 0–100 against Primary's ICP (funding stage, cash balance, international ops, treasury complexity)
3. **Generates** a 3-email outbound sequence for the top-scoring prospect

## Setup

```bash
pip install anthropic rich
export ANTHROPIC_API_KEY=your_key_here
```

## Usage

Score companies:
```bash
python prospect_scout.py "SafetyCulture" "Canva" "Airwallex"
```

Score + generate outreach for the top prospect:
```bash
python prospect_scout.py "SafetyCulture" "Canva" "Airwallex" --email
```

## Example output

```
  Primary — ICP Scoring
 ┌──────────────────┬──────────┬──────────────────┬──────────────────────────┐
 │ Company          │  Score   │ Contact          │ Trigger                  │
 ├──────────────────┼──────────┼──────────────────┼──────────────────────────┤
 │ ● SafetyCulture  │ 88/100   │ CFO              │ $32M Series C, expanding │
 │ ◐ Canva          │ 52/100   │ VP Finance       │ Multi-entity AU/US/EU    │
 └──────────────────┴──────────┴──────────────────┴──────────────────────────┘
```

## How this connects to the growth strategy

The tool automates the first three steps of the **funding-trigger outbound** playbook from the teardown:

1. Identify companies that recently raised → run through Prospect Scout
2. Score against ICP → prioritize outreach
3. Generate personalized first lines → human reviews and sends

A single SDR running this against weekly funding announcements could generate 5–10 qualified demos per week.

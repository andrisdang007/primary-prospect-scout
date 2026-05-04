#!/usr/bin/env python3
"""
Primary Funding Monitor

Scans TechCrunch, Startup Daily, AFR, Crunchbase, and LinkedIn for recent
AU/NZ biotech funding announcements, then runs discovered companies through
the prospect scout and saves results to Google Sheets.

Usage:
  python funding_monitor.py
  python funding_monitor.py --days 14
  python funding_monitor.py --sheets SHEET_ID
"""

import anthropic
import argparse
import json
import os
import sys
import time

try:
    import gspread
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False

try:
    from rich.console import Console
    from rich.table import Table
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

console = Console() if RICH_AVAILABLE else None

PRIMARY_CONTEXT = """
Primary is a treasury management platform for growth companies. Core value props:
- Real-time cash visibility across all banks, entities, and currencies (6,000+ banks)
- 4.5%+ yield on idle cash via institutional money market funds (BlackRock, Goldman Sachs, State Street)
- FX exposure tracking and hedge execution
- No bank switching — overlays existing banking, 7-day implementation
- SEC-registered (US) + AFSL-licensed (AU)

Ideal customer profile:
- Series A–C VC-backed biotech company, recently raised ($5M–$100M)
- $3M+ in idle cash
- Multi-entity, multi-currency, or expanding internationally (AU, US, NZ, UK, EU)
- Finance team managing treasury via spreadsheets
- Industries: biotech, biopharma, genomics, medtech, drug discovery, clinical-stage therapeutics
"""

SHEET_ID = "1DBrv7HL3uJ4yL0cUOmtCwl_03xltpaWmEOFrlRj2vKo"


def find_recent_raises(client: anthropic.Anthropic, days: int) -> list[str]:
    """Search news sources for recent AU/NZ biotech funding rounds. Returns company names."""
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 8}],
        messages=[{
            "role": "user",
            "content": f"""Search TechCrunch, Startup Daily (startupdaily.net), AFR, Crunchbase, and LinkedIn for Australian and New Zealand biotech, biopharma, medtech, or life-sciences companies that announced a funding round (Series A, B, or C) in the last {days} days.

Include only:
- Companies headquartered in Australia or New Zealand
- Biotech, biopharma, genomics, medtech, drug discovery, or clinical-stage therapeutics
- Series A, B, or C rounds (exclude seed, pre-seed, Series D+)

Return ONLY a JSON array of company names, no other text:
["Company A", "Company B", "Company C"]

If no relevant raises are found, return an empty array: []"""
        }]
    )

    text = "".join(block.text for block in response.content if block.type == "text").strip()
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.split("```")[0]

    try:
        companies = json.loads(text.strip())
        return [c for c in companies if isinstance(c, str)]
    except json.JSONDecodeError:
        return []


def research_and_score(client: anthropic.Anthropic, company_name: str) -> dict:
    """Research a company and score it against Primary's ICP."""
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 4}],
        messages=[{
            "role": "user",
            "content": f"""Research {company_name} and evaluate them as a sales prospect for Primary treasury platform.

{PRIMARY_CONTEXT}

Score {company_name} on 4 criteria (0–25 points each):
1. funding_stage: Have they raised Series A–C? How recently? What amount?
2. cash_balance: Based on funding and typical burn, do they likely have $3M+ in idle cash?
3. international: Do they operate across multiple entities, currencies, or geographies?
4. treasury_need: Does their size and growth stage mean they'd benefit from treasury tooling?

Return ONLY a JSON object with this exact structure:
{{
  "company": "{company_name}",
  "total_score": <sum of all scores, 0-100>,
  "scores": {{
    "funding_stage": <0-25>,
    "cash_balance": <0-25>,
    "international": <0-25>,
    "treasury_need": <0-25>
  }},
  "key_signals": [
    "<most compelling ICP signal>",
    "<second signal>",
    "<third signal>"
  ],
  "recommended_contact": "<exact job title — e.g. CFO, Head of Finance, VP Finance>",
  "trigger": "<the specific event or fact that makes now the right time to reach out>",
  "linkedin_url": "<LinkedIn company page URL — leave empty string if not found>"
}}"""
        }]
    )

    text = "".join(block.text for block in response.content if block.type == "text").strip()
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.split("```")[0]

    return json.loads(text.strip())


def append_to_sheets(results: list, sheet_id: str) -> str:
    sa_path = os.path.expanduser("~/.config/gspread/service_account.json")
    gc = gspread.service_account(filename=sa_path)
    ws = gc.open_by_key(sheet_id).sheet1

    headers = [
        "Company", "Score", "Funding Stage", "Cash Balance",
        "International", "Treasury Need", "Key Signals",
        "Contact", "Trigger", "LinkedIn",
    ]
    if ws.acell("A1").value != "Company":
        ws.clear()
        ws.append_row(headers)
        ws.format("A1:J1", {"textFormat": {"bold": True}, "backgroundColor": {"red": 0.18, "green": 0.18, "blue": 0.18}})

    rows = []
    for p in results:
        scores = p.get("scores", {})
        rows.append([
            p.get("company", ""),
            p.get("total_score", ""),
            scores.get("funding_stage", ""),
            scores.get("cash_balance", ""),
            scores.get("international", ""),
            scores.get("treasury_need", ""),
            " | ".join(p.get("key_signals", [])),
            p.get("recommended_contact", ""),
            p.get("trigger", ""),
            p.get("linkedin_url", ""),
        ])

    ws.append_rows(rows, value_input_option="RAW")
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}"


def print_results(results: list) -> None:
    if not results:
        return
    if RICH_AVAILABLE:
        table = Table(title="[bold]Primary — Funding Monitor Results[/bold]", show_header=True, header_style="bold cyan", border_style="dim")
        table.add_column("Company", style="bold white", min_width=16)
        table.add_column("Score", justify="center", min_width=8)
        table.add_column("Contact", style="dim", min_width=16)
        table.add_column("Trigger")
        for p in results:
            score = p["total_score"]
            color = "green" if score >= 70 else "yellow" if score >= 45 else "red"
            indicator = "● " if score >= 70 else "◐ " if score >= 45 else "○ "
            trigger = p.get("trigger", "—")
            table.add_row(
                indicator + p["company"],
                Text(f"{score}/100", style=f"bold {color}"),
                p.get("recommended_contact", "—"),
                trigger[:55] + ("…" if len(trigger) > 55 else ""),
            )
        console.print()
        console.print(table)
    else:
        print("\nPrimary — Funding Monitor Results")
        print("-" * 70)
        for p in results:
            print(f"{p['company']:20} {p['total_score']:3}/100  {p.get('recommended_contact', '—')}")


def main():
    parser = argparse.ArgumentParser(
        description="Scan news sources for recent AU/NZ biotech raises and score them",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  python funding_monitor.py\n  python funding_monitor.py --days 14 --sheets SHEET_ID",
    )
    parser.add_argument("--days", type=int, default=7, help="How many days back to search (default: 7)")
    parser.add_argument("--sheets", metavar="SHEET_ID", default=SHEET_ID, help="Google Sheet ID to append results to")
    parser.add_argument("--no-sheets", action="store_true", help="Skip Google Sheets output")
    args = parser.parse_args()

    client = anthropic.Anthropic()

    if RICH_AVAILABLE:
        with console.status(f"[bold cyan]Scanning for AU/NZ biotech raises in the last {args.days} days…[/bold cyan]", spinner="dots"):
            companies = find_recent_raises(client, args.days)
    else:
        print(f"Scanning for AU/NZ biotech raises in the last {args.days} days…")
        companies = find_recent_raises(client, args.days)

    if not companies:
        print("No new raises found.")
        sys.exit(0)

    if RICH_AVAILABLE:
        console.print(f"\n[bold]Found {len(companies)} compan{'y' if len(companies) == 1 else 'ies'}:[/bold] {', '.join(companies)}\n")
    else:
        print(f"\nFound: {', '.join(companies)}\n")

    results = []
    for company in companies:
        time.sleep(5)
        if RICH_AVAILABLE:
            with console.status(f"[bold cyan]Scoring {company}…[/bold cyan]", spinner="dots"):
                for attempt in range(3):
                    try:
                        prospect = research_and_score(client, company)
                        results.append(prospect)
                        score = prospect["total_score"]
                        color = "green" if score >= 70 else "yellow" if score >= 45 else "red"
                        console.print(f"  [bold {color}]✓[/bold {color}] {company} — {score}/100")
                        break
                    except anthropic.RateLimitError:
                        if attempt < 2:
                            time.sleep(30)
                        else:
                            console.print(f"  [yellow]⚠[/yellow] {company} — rate limited, skipping")
                    except Exception as e:
                        console.print(f"  [red]✗[/red] {company} — {e}")
                        break
        else:
            print(f"Scoring {company}…")
            for attempt in range(3):
                try:
                    prospect = research_and_score(client, company)
                    results.append(prospect)
                    print(f"  ✓ {company} — {prospect['total_score']}/100")
                    break
                except anthropic.RateLimitError:
                    if attempt < 2:
                        time.sleep(30)
                    else:
                        print(f"  ⚠ {company} — rate limited, skipping")
                except Exception as e:
                    print(f"  ✗ {company} — {e}")
                    break

    if not results:
        print("No results scored.")
        sys.exit(0)

    results.sort(key=lambda x: x["total_score"], reverse=True)
    print_results(results)

    if not args.no_sheets:
        if not GSPREAD_AVAILABLE:
            print("gspread not installed — run: pip install gspread")
        else:
            if RICH_AVAILABLE:
                with console.status("[bold cyan]Saving to Google Sheets…[/bold cyan]", spinner="dots"):
                    url = append_to_sheets(results, args.sheets)
                console.print(f"\n[bold green]✓[/bold green] Saved → {url}")
            else:
                print("Saving to Google Sheets…")
                url = append_to_sheets(results, args.sheets)
                print(f"✓ Saved → {url}")


if __name__ == "__main__":
    main()

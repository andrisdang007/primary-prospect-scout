#!/usr/bin/env python3
"""
Primary Prospect Scout

Researches companies, scores them against Primary's ICP, and generates personalized outreach.

Usage:
  python prospect_scout.py "SafetyCulture" "Canva" "Airwallex"
  python prospect_scout.py "AfterQuery" --email
"""

import anthropic
import argparse
import json
import sys
import time

try:
    from rich.console import Console
    from rich.panel import Panel
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
- Series A–C VC-backed company, recently raised ($5M–$100M)
- $3M+ in idle cash
- Multi-entity, multi-currency, or expanding internationally (AU, US, NZ, UK, EU)
- Finance team managing treasury via spreadsheets
- Industries: SaaS, healthtech, fintech, e-commerce, legaltech, hardware

Proof points:
- Constantinople: $127K saved annually on currency conversions
- Eucalyptus (acquired for $1.6B): 40% reduction in payment processing costs
- Blinq: 1,200 manual transfers automated per year
- Average ROI within 7 days of implementation
"""


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
  "personalized_first_line": "<1 punchy sentence for a cold email — reference something specific about their funding, growth, or business>"
}}"""
        }]
    )

    text = ""
    for block in response.content:
        if hasattr(block, "text"):
            text += block.text

    text = text.strip()
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.split("```")[0]

    return json.loads(text.strip())


def generate_email_sequence(client: anthropic.Anthropic, prospect: dict) -> list:
    """Generate a 3-email outbound sequence for a prospect."""
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": f"""Write a 3-email cold outreach sequence from Primary treasury platform to {prospect['company']}.

{PRIMARY_CONTEXT}

Company context:
- Key signals: {', '.join(prospect['key_signals'])}
- Best contact: {prospect['recommended_contact']}
- Trigger: {prospect['trigger']}
- Personalized opener: {prospect['personalized_first_line']}

Email 1 (Day 1): Lead with the personalized opener, pitch the core value prop, CTA for 15-min call.
Email 2 (Day 5): Short follow-up. Offer a concrete next step (custom yield estimate based on their raise).
Email 3 (Day 12): Honest breakup email. No pressure, leave the door open.

Rules:
- 4 sentences max per email
- No "I hope this finds you well" or similar filler
- Peer-to-peer tone — not salesy, not overly formal
- Each email has a subject line

Return ONLY a JSON array:
[
  {{"subject": "...", "body": "..."}},
  {{"subject": "...", "body": "..."}},
  {{"subject": "...", "body": "..."}}
]"""
        }]
    )

    text = response.content[0].text.strip()
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.split("```")[0]

    return json.loads(text.strip())


def print_results(results: list) -> None:
    if RICH_AVAILABLE:
        table = Table(
            title="[bold]Primary — ICP Scoring[/bold]",
            show_header=True,
            header_style="bold cyan",
            border_style="dim",
        )
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

        if results:
            top = results[0]
            console.print(f"\n[bold cyan]Top prospect signals — {top['company']}:[/bold cyan]")
            for signal in top.get("key_signals", []):
                console.print(f"  [dim]→[/dim] {signal}")
    else:
        print("\nPrimary — ICP Scoring")
        print("-" * 70)
        for p in results:
            print(f"{p['company']:20} {p['total_score']:3}/100  {p.get('recommended_contact', '—')}")
            print(f"  Trigger: {p.get('trigger', '—')}")
        print()


def print_emails(company: str, emails: list) -> None:
    days = [1, 5, 12]
    if RICH_AVAILABLE:
        for i, email in enumerate(emails):
            console.print(Panel(
                f"[dim]Subject:[/dim] {email['subject']}\n\n{email['body']}",
                title=f"[bold]Email {i + 1} — Day {days[i]}[/bold]",
                border_style="cyan" if i == 0 else "dim",
                padding=(1, 2),
            ))
    else:
        for i, email in enumerate(emails):
            print(f"\n--- Email {i + 1} (Day {days[i]}) ---")
            print(f"Subject: {email['subject']}")
            print(email["body"])


def main():
    parser = argparse.ArgumentParser(
        description="Score companies against Primary's ICP and generate personalized outreach",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  python prospect_scout.py \"SafetyCulture\" \"Canva\"\n  python prospect_scout.py \"AfterQuery\" --email",
    )
    parser.add_argument("companies", nargs="+", help="Company names to research and score")
    parser.add_argument("--email", action="store_true", help="Generate 3-email sequence for top prospect")
    args = parser.parse_args()

    client = anthropic.Anthropic()
    results = []

    for company in args.companies:
        if RICH_AVAILABLE:
            with console.status(f"[bold cyan]Researching {company}…[/bold cyan]", spinner="dots"):
                for attempt in range(3):
                    try:
                        prospect = research_and_score(client, company)
                        results.append(prospect)
                        console.print(f"  [green]✓[/green] {company} — {prospect['total_score']}/100")
                        break
                    except anthropic.RateLimitError:
                        if attempt < 2:
                            time.sleep(30)
                        else:
                            console.print(f"  [yellow]⚠[/yellow] {company} — rate limited, try again in a minute")
                    except Exception as e:
                        console.print(f"  [red]✗[/red] {company} — {e}")
                        break
        else:
            print(f"Researching {company}...")
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
                        print(f"  ⚠ {company} — rate limited, try again in a minute")
                except Exception as e:
                    print(f"  ✗ {company} — {e}")
                    break

    if not results:
        print("No results.")
        sys.exit(1)

    results.sort(key=lambda x: x["total_score"], reverse=True)
    print_results(results)

    if args.email:
        top = results[0]
        if RICH_AVAILABLE:
            console.print(f"\n[bold]Generating 3-email sequence for {top['company']}…[/bold]")
            with console.status("[bold cyan]Writing emails…[/bold cyan]", spinner="dots"):
                for attempt in range(3):
                    try:
                        emails = generate_email_sequence(client, top)
                        break
                    except anthropic.RateLimitError:
                        if attempt < 2:
                            console.print("  [yellow]Rate limited — waiting 30s…[/yellow]")
                            time.sleep(30)
                        else:
                            console.print("[red]Still rate limited. Run again in a minute.[/red]")
                            sys.exit(1)
        else:
            print(f"\nGenerating 3-email sequence for {top['company']}...")
            for attempt in range(3):
                try:
                    emails = generate_email_sequence(client, top)
                    break
                except anthropic.RateLimitError:
                    if attempt < 2:
                        print("Rate limited — waiting 30s…")
                        time.sleep(30)
                    else:
                        print("Still rate limited. Run again in a minute.")
                        sys.exit(1)

        print_emails(top["company"], emails)


if __name__ == "__main__":
    main()

"""Command-line interface for WhatsApp Chat Analyzer.

Usage:
    python cli.py chat.txt
    python cli.py chat.txt --user "Ali" --export-json report.json
"""

import argparse
import json
import sys
from datetime import datetime

# Ensure utf-8 encoding on Windows console for emoji printing
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from whatsapp_analyzer import parse_chat_file, analyze_chat

def main():
    parser = argparse.ArgumentParser(
        description="WhatsApp Chat Analyzer - Analyze exported WhatsApp chats in Python"
    )
    parser.add_argument("file", help="Path to exported WhatsApp .txt or .zip file")
    parser.add_argument(
        "--user", default="Overall", help="Filter by specific participant (default: 'Overall')"
    )
    parser.add_argument(
        "--date-order", choices=["DMY", "MDY"], default=None,
        help="Override date format order (DMY or MDY)"
    )
    parser.add_argument(
        "--include-stopwords", action="store_true",
        help="Include stop words in word frequency analysis"
    )
    parser.add_argument(
        "--export-json", default=None,
        help="File path to save the complete analysis results in JSON format"
    )

    args = parser.parse_args()

    try:
        with open(args.file, "rb") as f:
            content = f.read()
    except Exception as e:
        print(f"Error opening file '{args.file}': {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Analyzing '{args.file}'...")
    res = parse_chat_file(content, filename=args.file, override_date_order=args.date_order)

    if res.status == "error":
        print(f"Error: {res.error_message}", file=sys.stderr)
        sys.exit(1)

    print(f"Detected Platform: {res.platform.upper()}")
    print(f"Date Order: {res.date_order}")
    print(f"Total Parsed Messages: {len(res.messages)}")
    print(f"Participants Found ({len(res.participants)}): {', '.join(res.participants)}\n")

    results = analyze_chat(
        res.messages,
        user=args.user,
        remove_stopwords=not args.include_stopwords
    )

    stats = results["stats"]
    print("=" * 50)
    print(f"CHAT STATISTICS ({args.user})")
    print("=" * 50)
    print(f"Total Messages:      {stats.total_messages:,}")
    print(f"Total Words:         {stats.total_words:,}")
    print(f"Media Shared:        {stats.media_count:,}")
    print(f"Links Shared:        {stats.link_count:,}")
    if stats.start_date and stats.end_date:
        print(f"Date Range:          {stats.start_date.strftime('%d %b %Y')} to {stats.end_date.strftime('%d %b %Y')} ({stats.total_days} days)")
        print(f"Avg Messages/Day:    {stats.avg_messages_per_day}")
    print(f"Longest Chat Streak: {results['longest_streak']} consecutive days")
    print("=" * 50)

    if not results["user_ranks"].empty:
        print("\nTOP PARTICIPANTS:")
        print(results["user_ranks"].to_string(index=False))

    if results["words"]:
        print("\nTOP 10 WORDS:")
        for word, count in results["words"][:10]:
            print(f"  - {word}: {count}")

    if not results["emojis"].empty:
        print("\nTOP 5 EMOJIS:")
        print(results["emojis"].head(5).to_string(index=False))

    if args.export_json:
        exportable = {
            "file": args.file,
            "user": args.user,
            "platform": res.platform,
            "date_order": res.date_order,
            "total_messages": stats.total_messages,
            "total_words": stats.total_words,
            "media_count": stats.media_count,
            "link_count": stats.link_count,
            "total_days": stats.total_days,
            "avg_messages_per_day": stats.avg_messages_per_day,
            "longest_streak_days": results["longest_streak"],
            "top_words": results["words"][:25],
            "participants": res.participants,
        }
        with open(args.export_json, "w", encoding="utf-8") as jf:
            json.dump(exportable, jf, indent=2, ensure_ascii=False)
        print(f"\nSaved analysis results to {args.export_json}")

if __name__ == "__main__":
    main()

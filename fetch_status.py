#!/usr/bin/env python3
"""
Fetch workflow runs and video stats from all YouTube automation repos.
Writes aggregated data to data/status.json for the dashboard.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

GITHUB_TOKEN = os.environ.get("PAT_TOKEN", "")
OWNER = "RomanBazylev"
API = "https://api.github.com"

CHANNELS = [
    {
        "id": "omni-mystery",
        "name": "Omni Mystery",
        "emoji": "\U0001f52e",
        "repo": "Omni-Mystery-Machine",
        "workflows": ["run_bot.yml", "generate_long_video.yml"],
        "schedules": {"run_bot.yml": "every 4h", "generate_long_video.yml": "daily 09:00"},
        "perf_log_path": "performance_log.json",
        "youtube_url": "",
    },
    {
        "id": "reddit-stories",
        "name": "Reddit Stories",
        "emoji": "\U0001f4d6",
        "repo": "youtube-reddit-stories",
        "workflows": ["generate_story_short.yml", "generate_story_long.yml"],
        "schedules": {"generate_story_short.yml": "every 4h", "generate_story_long.yml": "daily 07:00"},
        "perf_log_path": "performance_log.json",
        "youtube_url": "",
    },
    {
        "id": "poland",
        "name": "\u042f \u0432 \u041f\u043e\u043b\u044c\u0448\u0435",
        "emoji": "\U0001f1f5\U0001f1f1",
        "repo": "youtube-poland-automation",
        "workflows": ["generate_poland_short.yml", "generate_poland_long.yml"],
        "schedules": {"generate_poland_short.yml": "every 4h", "generate_poland_long.yml": "2x daily"},
        "perf_log_path": "performance_log.json",
        "youtube_url": "",
    },
    {
        "id": "salesforce",
        "name": "Salesforce Tips",
        "emoji": "\u26a1",
        "repo": "youtube-salesforce-automation",
        "workflows": ["generate_salesforce_short.yml"],
        "schedules": {"generate_salesforce_short.yml": "every 4h"},
        "perf_log_path": "performance_log.json",
        "youtube_url": "",
    },
    {
        "id": "money",
        "name": "Smart Money",
        "emoji": "\U0001f4b0",
        "repo": "youtube-smart-money-tips",
        "workflows": ["generate_money_short.yml", "generate_money_long.yml"],
        "schedules": {"generate_money_short.yml": "every 3h", "generate_money_long.yml": "daily 09:00"},
        "perf_log_path": "performance_log.json",
        "youtube_url": "",
    },
    {
        "id": "ironman",
        "name": "Iron Man",
        "emoji": "\U0001f9be",
        "repo": "youtube-ironman-automation",
        "workflows": ["generate_video.yml", "generate_longform.yml"],
        "schedules": {"generate_video.yml": "every 3h", "generate_longform.yml": "Mon/Wed/Fri 06:00"},
        "perf_log_path": "performance_log.json",
        "youtube_url": "",
    },
    {
        "id": "fishing",
        "name": "\u0420\u044b\u0431\u0430\u043b\u043a\u0430",
        "emoji": "\U0001f3a3",
        "repo": "youtube-fishing-automation",
        "workflows": ["generate_fishing_short.yml"],
        "schedules": {"generate_fishing_short.yml": "every 4h"},
        "perf_log_path": "performance_log.json",
        "youtube_url": "",
    },
    {
        "id": "hard4fun",
        "name": "GlitchRealityAI",
        "emoji": "\U0001f47e",
        "repo": "hard4fun",
        "workflows": ["daily-shorts.yml"],
        "schedules": {"daily-shorts.yml": "2x daily (00:00 + 14:00 UTC)"},
        "perf_log_path": "performance_log.json",
        "youtube_url": "",
    },
]


def gh_api(path: str) -> dict | list | None:
    """Make an authenticated GET request to the GitHub API."""
    url = f"{API}{path}" if path.startswith("/") else path
    req = Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    if GITHUB_TOKEN:
        req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        print(f"  [WARN] {url} -> {e.code}", file=sys.stderr)
        return None


def fetch_workflow_runs(repo: str, workflow_file: str) -> list[dict]:
    """Get the last 5 runs for a workflow."""
    data = gh_api(
        f"/repos/{OWNER}/{repo}/actions/workflows/{workflow_file}/runs?per_page=5"
    )
    if not data or "workflow_runs" not in data:
        return []
    runs = []
    for r in data["workflow_runs"]:
        runs.append(
            {
                "id": r["id"],
                "status": r["status"],
                "conclusion": r["conclusion"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
                "html_url": r["html_url"],
                "run_number": r["run_number"],
            }
        )
    return runs


def fetch_perf_log(repo: str, path: str) -> list[dict]:
    """Fetch performance_log.json from a repo's default branch."""
    data = gh_api(f"/repos/{OWNER}/{repo}/contents/{path}")
    if not data or "download_url" not in data:
        return []
    download_url = data["download_url"]
    req = Request(download_url)
    if GITHUB_TOKEN:
        req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
    try:
        with urlopen(req, timeout=30) as resp:
            raw = json.loads(resp.read().decode())
            return raw.get("videos", [])
    except Exception as e:
        print(f"  [WARN] perf_log {repo}: {e}", file=sys.stderr)
        return []


def resolve_channel_from_video(video_id: str) -> dict | None:
    """Use YouTube oEmbed to get channel info from a video ID."""
    url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
    req = Request(url)
    try:
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            author = data.get("author_name", "")
            author_url = data.get("author_url", "")
            return {"channel_name": author, "channel_url": author_url}
    except Exception:
        return None


def _is_short(video: dict) -> bool:
    """Detect if a video is a Short by title or tags."""
    title = (video.get("title") or "").lower()
    tags = [t.lower() for t in (video.get("tags") or [])]
    return "#shorts" in title or "shorts" in tags


def compute_video_stats(videos: list[dict]) -> dict:
    """Compute aggregate stats from a list of video entries."""
    if not videos:
        return {
            "total": 0,
            "last_30d": 0,
            "avg_views": 0,
            "avg_likes": 0,
            "avg_comments": 0,
            "best_video": None,
            "last_upload": None,
            "last_short": None,
            "last_long": None,
        }

    now = datetime.now(timezone.utc)
    last_30d = 0
    total_views = 0
    total_likes = 0
    total_comments = 0
    stats_count = 0
    best_video = None
    best_views = -1
    last_upload = None
    last_upload_dt = None
    last_short = None
    last_short_dt = None
    last_long = None
    last_long_dt = None

    for v in videos:
        # Count uploads in last 30 days
        uploaded = v.get("uploaded_at")
        if uploaded:
            try:
                dt = datetime.fromisoformat(uploaded)
                age_days = (now - dt).total_seconds() / 86400
                if age_days <= 30:
                    last_30d += 1
                entry = {
                    "title": v.get("title", ""),
                    "video_id": v.get("video_id", ""),
                    "uploaded_at": uploaded,
                }
                if last_upload_dt is None or dt > last_upload_dt:
                    last_upload_dt = dt
                    last_upload = entry
                if _is_short(v):
                    if last_short_dt is None or dt > last_short_dt:
                        last_short_dt = dt
                        last_short = entry
                else:
                    if last_long_dt is None or dt > last_long_dt:
                        last_long_dt = dt
                        last_long = entry
            except (ValueError, TypeError):
                pass

        # Aggregate stats if available
        s = v.get("stats")
        if s and isinstance(s, dict):
            views = s.get("views", 0) or 0
            likes = s.get("likes", 0) or 0
            comments = s.get("comments", 0) or 0
            total_views += views
            total_likes += likes
            total_comments += comments
            stats_count += 1
            if views > best_views:
                best_views = views
                best_video = {
                    "title": v.get("title", ""),
                    "video_id": v.get("video_id", ""),
                    "views": views,
                }

    return {
        "total": len(videos),
        "last_30d": last_30d,
        "avg_views": round(total_views / stats_count) if stats_count else 0,
        "avg_likes": round(total_likes / stats_count) if stats_count else 0,
        "avg_comments": round(total_comments / stats_count) if stats_count else 0,
        "best_video": best_video,
        "last_upload": last_upload,
        "last_short": last_short,
        "last_long": last_long,
    }


def process_channel(channel: dict) -> dict:
    """Fetch all data for one channel."""
    repo = channel["repo"]
    print(f"Processing {channel['name']} ({repo})...")

    # Fetch workflow runs
    workflows = {}
    schedules = channel.get("schedules", {})
    for wf in channel["workflows"]:
        wf_name = wf.replace(".yml", "").replace("_", " ").title()
        runs = fetch_workflow_runs(repo, wf)
        latest = runs[0] if runs else None

        # Count consecutive failures
        failure_streak = 0
        for r in runs:
            if r["conclusion"] == "failure":
                failure_streak += 1
            else:
                break

        workflows[wf] = {
            "name": wf_name,
            "schedule": schedules.get(wf, ""),
            "latest": latest,
            "failure_streak": failure_streak,
            "recent_runs": runs,
        }

    # Fetch video stats
    videos = []
    if channel["perf_log_path"]:
        videos = fetch_perf_log(repo, channel["perf_log_path"])

    video_stats = compute_video_stats(videos)

    # Resolve YouTube channel URL from latest video if not configured
    youtube_url = channel.get("youtube_url", "")
    if not youtube_url and videos:
        for v in reversed(videos):
            vid = v.get("video_id")
            if vid:
                info = resolve_channel_from_video(vid)
                if info and info["channel_url"]:
                    youtube_url = info["channel_url"]
                    print(f"  Resolved YT channel: {youtube_url}")
                    break

    return {
        "id": channel["id"],
        "name": channel["name"],
        "emoji": channel["emoji"],
        "repo": repo,
        "repo_url": f"https://github.com/{OWNER}/{repo}",
        "youtube_url": youtube_url,
        "workflows": workflows,
        "video_stats": video_stats,
    }


def main():
    if not GITHUB_TOKEN:
        print("WARNING: PAT_TOKEN not set. API rate limits will be very low.", file=sys.stderr)

    results = []
    for ch in CHANNELS:
        results.append(process_channel(ch))

    # Compute summary
    total_videos_30d = sum(c["video_stats"]["last_30d"] for c in results)
    total_views = sum(c["video_stats"]["avg_views"] * c["video_stats"]["total"] for c in results)

    failed_channels = []
    warning_channels = []
    for c in results:
        has_failure = False
        for wf_data in c["workflows"].values():
            latest = wf_data["latest"]
            if latest and latest["conclusion"] == "failure":
                has_failure = True
                break
        if has_failure:
            failed_channels.append(c["name"])

        last = c["video_stats"]["last_upload"]
        if last and last.get("uploaded_at"):
            try:
                dt = datetime.fromisoformat(last["uploaded_at"])
                hours_ago = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
                if hours_ago > 24:
                    warning_channels.append(c["name"])
            except (ValueError, TypeError):
                pass
        elif c["video_stats"]["total"] > 0:
            warning_channels.append(c["name"])

    # Success rate
    total_runs = 0
    success_runs = 0
    for c in results:
        for wf_data in c["workflows"].values():
            for r in wf_data["recent_runs"]:
                total_runs += 1
                if r["conclusion"] == "success":
                    success_runs += 1

    output = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_videos_30d": total_videos_30d,
            "total_views_estimate": total_views,
            "success_rate": round(success_runs / total_runs * 100, 1) if total_runs else 0,
            "total_runs_sampled": total_runs,
            "failed_channels": failed_channels,
            "warning_channels": warning_channels,
        },
        "channels": results,
    }

    out_dir = Path(__file__).parent / "data"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "status.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {out_path} ({out_path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()

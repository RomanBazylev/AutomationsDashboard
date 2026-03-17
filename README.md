# YouTube Automations Dashboard

Centralized monitoring dashboard for all YouTube automation channels.  
Hosted on GitHub Pages, updated every 30 minutes by GitHub Actions.

## Channels tracked

| Channel | Repo | Workflows |
|---------|------|-----------|
| 🔮 Omni Mystery | Omni-Mystery-Machine | run_bot, generate_long_video |
| 📖 Reddit Stories | youtube-reddit-stories | generate_story_short, generate_story_long |
| 🇵🇱 Я в Польше | youtube-poland-automation | generate_poland_short, generate_poland_long |
| ⚡ Salesforce Tips | youtube-salesforce-automation | generate_salesforce_short |
| 💰 Smart Money | youtube-smart-money-tips | generate_money_short |
| 🦾 Iron Man | youtube-ironman-automation | generate_video, generate_longform |
| 🎣 Рыбалка | youtube-fishing-automation | generate_fishing_short |

## Setup

1. Create a GitHub **Personal Access Token** (classic) with `repo` scope  
2. Add it as a secret named `PAT_TOKEN` in this repo's settings  
3. Enable **GitHub Pages** → Source: Deploy from a branch → `main` / `/ (root)`  
4. Trigger the workflow manually or wait for the next cron run  

## Local testing

```bash
export PAT_TOKEN="ghp_..."
python fetch_status.py
# then open index.html in a browser
```

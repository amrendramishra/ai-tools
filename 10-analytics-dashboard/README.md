# 📊 YouTube Analytics Dashboard

AI-powered YouTube channel analytics and strategy recommendation engine. Works with manual data input or generates simulated data for demo purposes.

## Features

- **Data Import**: Load analytics from CSV or JSON files
- **Simulation Mode**: Generate realistic demo data for 9 channels
- **AI Analysis**: Deep analysis of growth trends, content performance, and timing
- **Strategy Recommendations**: Actionable suggestions per channel
- **Cross-Channel Comparison**: Compare and benchmark across multiple channels
- **Markdown Reports**: Export comprehensive reports to `reports/` directory

## Prerequisites

- Python 3.8+
- Ollama running locally with `llama3.2` model
- Virtual environment at `~/Downloads/AI/.venv`

```bash
ollama pull llama3.2
```

## Usage

### Quick Demo (Simulated Data)
```bash
./analytics_dashboard.py --simulate
```

### Import Your Data
```bash
./analytics_dashboard.py --input my_analytics.json
./analytics_dashboard.py --input my_analytics.csv
```

### Generate Full Report
```bash
./analytics_dashboard.py --simulate --report
./analytics_dashboard.py --input data.json --report --channel "My Channel"
```

### Compare Channels
```bash
./analytics_dashboard.py --simulate --compare-channels
```

## Input Formats

### JSON Format
```json
{
  "channels": {
    "Channel Name": {
      "name": "Channel Name",
      "niche": "technology",
      "subscribers": 50000,
      "videos": [
        {
          "title": "Video Title",
          "date": "2025-01-15",
          "views": 10000,
          "likes": 500,
          "comments": 50,
          "ctr": 8.5,
          "watch_time_hours": 150.5
        }
      ]
    }
  }
}
```

### CSV Format
```csv
channel,title,date,views,likes,comments,ctr,watch_time_hours
Tech Channel,Video Title,2025-01-15,10000,500,50,8.5,150.5
```

## Output

- Terminal dashboard with ranked channel metrics
- Markdown reports saved to `reports/` directory
- Simulated data saved as `simulated_data.json`

## Channels in Demo Data

1. Tech Tutorials (technology)
2. Gyaan in 5 (education)
3. Gaming Pulse (gaming)
4. Fitness First (fitness)
5. Cook with Dev (cooking)
6. Code & Coffee (programming)
7. Daily Vlog Life (vlogging)
8. Finance Guru (finance)
9. Music Vibes (music)

## Analysis Includes

- Growth trend assessment
- Best performing content identification
- Optimal posting times
- Engagement improvement strategies
- CTR optimization tips
- Actionable next steps ranked by impact

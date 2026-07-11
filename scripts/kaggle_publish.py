#!/usr/bin/env python3
"""
Auto-publish Kaggle notebooks weekly.
Rotates through 10 AI topics based on week number.
Uses KAGGLE_TOKEN env var for authentication.
"""

import os
import json
import requests
from datetime import datetime

KAGGLE_TOKEN = os.environ.get("KAGGLE_TOKEN", "KGAT_c4dfec9a224cc16c3952a051359dd1d6")
KAGGLE_USERNAME = "amrendranmishra"
KAGGLE_API_BASE = "https://www.kaggle.com/api/v1"

# 10 notebook templates rotating weekly
NOTEBOOK_TEMPLATES = [
    {
        "title": "🤖 AI Tips: Top 5 Prompt Engineering Techniques",
        "topic": "ai-tips",
        "content": """# AI Tips: Prompt Engineering Techniques\n\n## 1. Chain of Thought\nBreak complex problems into steps.\n\n## 2. Few-Shot Learning\nProvide examples in your prompt.\n\n## 3. Role Playing\nAssign a role to the AI.\n\n## 4. Structured Output\nAsk for specific formats (JSON, tables).\n\n## 5. Iterative Refinement\nBuild on previous outputs.\n\n```python\nimport openai\n# Example: Chain of Thought prompting\nprompt = \"Let's think step by step...\"\nprint("Prompt engineering is key to better AI outputs!")\n```"""
    },
    {
        "title": "🐍 Python Tricks: One-Liners That Save Hours",
        "topic": "python-tricks",
        "content": """# Python Tricks: Powerful One-Liners\n\n```python\n# Flatten a nested list\nflat = [x for sublist in nested for x in sublist]\n\n# Dictionary comprehension with condition\nfiltered = {k: v for k, v in d.items() if v > 0}\n\n# Read file in one line\ndata = open('file.txt').read().splitlines()\n\n# Swap variables\na, b = b, a\n\n# Counter from list\nfrom collections import Counter\ncounts = Counter(['a', 'b', 'a', 'c', 'a'])\nprint(counts.most_common(3))\n```"""
    },
    {
        "title": "🦙 Ollama Tutorial: Run LLMs Locally for Free",
        "topic": "ollama-tutorials",
        "content": """# Ollama: Run LLMs Locally\n\n## Installation\n```bash\ncurl -fsSL https://ollama.com/install.sh | sh\n```\n\n## Running Models\n```python\nimport requests\n\ndef query_ollama(prompt, model="llama3"):\n    response = requests.post(\n        "http://localhost:11434/api/generate",\n        json={"model": model, "prompt": prompt, "stream": False}\n    )\n    return response.json()["response"]\n\nresult = query_ollama("Explain quantum computing in 3 sentences")\nprint(result)\n```\n\n## Available Models\n- llama3 (8B) - General purpose\n- codellama - Code generation\n- mistral - Fast and efficient"""
    },
    {
        "title": "🔗 LangChain Guide: Build AI Agents in 10 Minutes",
        "topic": "langchain-guides",
        "content": """# LangChain: Build AI Agents Fast\n\n```python\nfrom langchain_community.llms import Ollama\nfrom langchain.agents import initialize_agent, Tool\nfrom langchain.memory import ConversationBufferMemory\n\n# Setup LLM\nllm = Ollama(model="llama3")\n\n# Define tools\ntools = [\n    Tool(name="Calculator", func=lambda x: eval(x), description="Math operations"),\n]\n\n# Create agent with memory\nmemory = ConversationBufferMemory()\nagent = initialize_agent(tools, llm, memory=memory, verbose=True)\n\n# Run\nresult = agent.run("What is 25 * 4 + 100?")\nprint(result)\n```"""
    },
    {
        "title": "⚡ Automation Ideas: 5 Scripts That Run Your Life",
        "topic": "automation-ideas",
        "content": """# Automation Ideas: Scripts That Save Time\n\n```python\nimport schedule\nimport subprocess\nimport time\n\n# 1. Auto-backup important files\ndef backup_files():\n    subprocess.run(['rsync', '-av', '~/Documents/', '~/Backup/'])\n\n# 2. Auto-clean downloads folder\ndef clean_downloads():\n    import os, time\n    for f in os.listdir('~/Downloads'):\n        if os.path.getmtime(f) < time.time() - 30*86400:\n            os.remove(f)\n\n# 3. Auto-commit code changes\ndef git_autopush():\n    subprocess.run(['git', 'add', '-A'])\n    subprocess.run(['git', 'commit', '-m', f'Auto: {time.strftime(\"%Y-%m-%d\")}'])\n    subprocess.run(['git', 'push'])\n\nschedule.every().day.at("23:00").do(git_autopush)\nschedule.every().day.at("06:00").do(backup_files)\nschedule.every().week.do(clean_downloads)\n\nwhile True:\n    schedule.run_pending()\n    time.sleep(60)\n```"""
    },
    {
        "title": "📊 Data Science: Quick EDA with Pandas Profiling",
        "topic": "data-science",
        "content": """# Quick EDA with Pandas\n\n```python\nimport pandas as pd\nimport numpy as np\n\n# Generate sample data\ndf = pd.DataFrame({\n    'age': np.random.randint(18, 65, 1000),\n    'salary': np.random.normal(50000, 15000, 1000),\n    'department': np.random.choice(['Engineering', 'Sales', 'Marketing'], 1000)\n})\n\n# Quick stats\nprint(df.describe())\nprint(df.groupby('department').agg({'salary': ['mean', 'median', 'std']}))\n\n# Missing values\nprint(f"Missing values: {df.isnull().sum().sum()}")\n\n# Correlations\nprint(df.select_dtypes(include=[np.number]).corr())\n```"""
    },
    {
        "title": "🚀 FastAPI: Build REST APIs in Minutes",
        "topic": "fastapi",
        "content": """# FastAPI: Quick REST API\n\n```python\nfrom fastapi import FastAPI, HTTPException\nfrom pydantic import BaseModel\n\napp = FastAPI(title="AI Tools API")\n\nclass PredictionRequest(BaseModel):\n    text: str\n    model: str = "default"\n\n@app.get("/")\ndef root():\n    return {"status": "running", "version": "1.0"}\n\n@app.post("/predict")\ndef predict(req: PredictionRequest):\n    # Simulate prediction\n    return {"input": req.text, "prediction": "positive", "confidence": 0.95}\n\n@app.get("/health")\ndef health():\n    return {"healthy": True}\n\n# Run: uvicorn main:app --reload\n```"""
    },
    {
        "title": "🧠 Neural Networks: Build from Scratch in NumPy",
        "topic": "neural-networks",
        "content": """# Neural Network from Scratch\n\n```python\nimport numpy as np\n\ndef sigmoid(x): return 1 / (1 + np.exp(-x))\ndef sigmoid_deriv(x): return x * (1 - x)\n\n# Training data (XOR)\nX = np.array([[0,0],[0,1],[1,0],[1,1]])\ny = np.array([[0],[1],[1],[0]])\n\n# Initialize weights\nnp.random.seed(42)\nw1 = np.random.randn(2, 4)\nw2 = np.random.randn(4, 1)\n\n# Train\nfor epoch in range(10000):\n    h = sigmoid(X @ w1)\n    o = sigmoid(h @ w2)\n    \n    o_err = y - o\n    o_delta = o_err * sigmoid_deriv(o)\n    \n    h_err = o_delta @ w2.T\n    h_delta = h_err * sigmoid_deriv(h)\n    \n    w2 += h.T @ o_delta * 0.5\n    w1 += X.T @ h_delta * 0.5\n\nprint(f"Output after training: {o.round(2).flatten()}")\n```"""
    },
    {
        "title": "🐳 Docker for ML: Containerize Your Models",
        "topic": "docker-ml",
        "content": """# Docker for ML Models\n\n```python\n# app.py - Simple ML serving\nfrom flask import Flask, request, jsonify\nimport pickle\nimport numpy as np\n\napp = Flask(__name__)\nmodel = pickle.load(open('model.pkl', 'rb'))\n\n@app.route('/predict', methods=['POST'])\ndef predict():\n    data = request.json['features']\n    prediction = model.predict(np.array([data]))\n    return jsonify({'prediction': prediction.tolist()})\n\nif __name__ == '__main__':\n    app.run(host='0.0.0.0', port=5000)\n```\n\n```dockerfile\n# Dockerfile\nFROM python:3.11-slim\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install -r requirements.txt\nCOPY . .\nEXPOSE 5000\nCMD ["python", "app.py"]\n```"""
    },
    {
        "title": "📈 ML Monitoring: Track Model Performance",
        "topic": "ml-monitoring",
        "content": """# ML Model Monitoring\n\n```python\nimport numpy as np\nfrom datetime import datetime\n\nclass ModelMonitor:\n    def __init__(self, model_name):\n        self.model_name = model_name\n        self.predictions = []\n        self.actuals = []\n        \n    def log_prediction(self, pred, actual=None):\n        self.predictions.append({'value': pred, 'time': datetime.now()})\n        if actual: self.actuals.append(actual)\n    \n    def check_drift(self, window=100):\n        recent = [p['value'] for p in self.predictions[-window:]]\n        baseline = [p['value'] for p in self.predictions[:window]]\n        drift = abs(np.mean(recent) - np.mean(baseline))\n        return {'drift_score': drift, 'alert': drift > 0.1}\n    \n    def get_accuracy(self):\n        if not self.actuals: return None\n        correct = sum(p == a for p, a in zip(\n            [x['value'] for x in self.predictions[:len(self.actuals)]], \n            self.actuals\n        ))\n        return correct / len(self.actuals)\n\nmonitor = ModelMonitor("sentiment-v1")\nprint(f"Monitoring: {monitor.model_name}")\n```"""
    }
]


def get_notebook_for_week():
    """Pick notebook template based on current week number."""
    week_num = datetime.now().isocalendar()[1]
    index = week_num % len(NOTEBOOK_TEMPLATES)
    return NOTEBOOK_TEMPLATES[index]


def create_kernel_metadata(template):
    """Create Kaggle kernel metadata."""
    slug = f"{KAGGLE_USERNAME}/{template['topic']}-week-{datetime.now().strftime('%Y%W')}"
    return {
        "id": slug,
        "title": template["title"],
        "code_file": "notebook.py",
        "language": "python",
        "kernel_type": "notebook",
        "is_private": False,
        "enable_gpu": False,
        "enable_internet": True,
        "keywords": [template["topic"], "ai", "automation", "tutorial"],
        "dataset_sources": [],
        "kernel_sources": [],
        "competition_sources": []
    }


def publish_to_kaggle(template):
    """Publish notebook to Kaggle using API."""
    import base64
    
    headers = {
        "Authorization": f"Bearer {KAGGLE_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Create notebook content as Python script
    notebook_content = template["content"]
    encoded_content = base64.b64encode(notebook_content.encode()).decode()
    
    slug = f"{template['topic']}-week-{datetime.now().strftime('%Y%W')}"
    
    payload = {
        "id": f"{KAGGLE_USERNAME}/{slug}",
        "title": template["title"],
        "text": encoded_content,
        "language": "python",
        "kernel_type": "notebook",
        "is_private": "false",
        "enable_gpu": "false",
        "enable_internet": "true",
        "keywords": json.dumps([template["topic"], "ai", "automation"]),
    }
    
    # Push to Kaggle Kernels API
    url = f"{KAGGLE_API_BASE}/kernels/push"
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code in [200, 201]:
            print(f"✅ Published: {template['title']}")
            print(f"   URL: https://www.kaggle.com/code/{KAGGLE_USERNAME}/{slug}")
            return True
        else:
            print(f"❌ Failed ({response.status_code}): {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    print(f"🗓️  Week {datetime.now().isocalendar()[1]} - Kaggle Auto-Publisher")
    print(f"👤 Username: {KAGGLE_USERNAME}")
    print("-" * 50)
    
    template = get_notebook_for_week()
    print(f"📓 Selected topic: {template['title']}")
    
    success = publish_to_kaggle(template)
    
    if success:
        print("\n✅ Weekly notebook published successfully!")
    else:
        print("\n⚠️  Publishing failed - check token and API access")

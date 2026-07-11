#!/Users/amrendranarayanmishra/Downloads/AI/.venv/bin/python3
"""
Multi-Agent Crew - A from-scratch multi-agent pipeline system.

Orchestrates multiple AI agents (Researcher, Writer, Editor, Reviewer, Publisher)
through configurable pipelines to produce polished content from a topic.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

# Configuration
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR / "output"
AGENTS_FILE = SCRIPT_DIR / "agents.json"
PIPELINES_FILE = SCRIPT_DIR / "pipelines.json"


class Agent:
    """Represents a single AI agent with a specific role."""

    def __init__(self, config: dict):
        self.name = config["name"]
        self.role = config["role"]
        self.model = config.get("model", "llama3.2")
        self.system_prompt = config["system_prompt"]
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 2048)

    def __repr__(self):
        return f"Agent(name={self.name}, role={self.role}, model={self.model})"

    def think(self, prompt: str, context: str = "") -> str:
        """Send a prompt to the agent and get a response via Ollama."""
        messages = [
            {"role": "system", "content": self.system_prompt},
        ]
        if context:
            messages.append({"role": "user", "content": f"Context from previous agents:\n\n{context}\n\n---\n\nTask: {prompt}"})
        else:
            messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            },
        }

        try:
            resp = requests.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json=payload,
                timeout=300,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "")
        except requests.ConnectionError:
            print(f"  ✗ Error: Cannot connect to Ollama at {OLLAMA_BASE_URL}")
            print(f"    Make sure Ollama is running: ollama serve")
            sys.exit(1)
        except requests.HTTPError as e:
            print(f"  ✗ HTTP Error from Ollama: {e}")
            print(f"    Response: {resp.text[:200]}")
            sys.exit(1)
        except Exception as e:
            print(f"  ✗ Unexpected error: {e}")
            sys.exit(1)


class Pipeline:
    """Defines a sequence of agent steps to process content."""

    def __init__(self, name: str, steps: List[str], output_format: str = "markdown", context: str = ""):
        self.name = name
        self.steps = steps
        self.output_format = output_format
        self.context = context


class Crew:
    """Orchestrates agents through a pipeline."""

    def __init__(self, agents_file: Path = AGENTS_FILE, pipelines_file: Path = PIPELINES_FILE):
        self.agents: Dict[str, Agent] = {}
        self.pipelines: Dict[str, Pipeline] = {}
        self.results: List[Dict[str, Any]] = []
        self._load_agents(agents_file)
        self._load_pipelines(pipelines_file)

    def _load_agents(self, filepath: Path):
        """Load agent configurations from JSON file."""
        if not filepath.exists():
            print(f"Error: Agents file not found: {filepath}")
            sys.exit(1)
        with open(filepath) as f:
            data = json.load(f)
        for agent_config in data["agents"]:
            agent = Agent(agent_config)
            self.agents[agent.role] = agent

    def _load_pipelines(self, filepath: Path):
        """Load pipeline configurations from JSON file."""
        if not filepath.exists():
            print(f"Error: Pipelines file not found: {filepath}")
            sys.exit(1)
        with open(filepath) as f:
            data = json.load(f)
        for key, config in data["pipelines"].items():
            self.pipelines[key] = Pipeline(
                name=config["name"],
                steps=config["steps"],
                output_format=config.get("output_format", "markdown"),
                context=config.get("context", ""),
            )

    def list_agents(self):
        """Display all available agents."""
        print("\n╔══════════════════════════════════════════════════╗")
        print("║           Available Agents                       ║")
        print("╠══════════════════════════════════════════════════╣")
        for role, agent in self.agents.items():
            print(f"║  🤖 {agent.name:<12} │ Role: {role:<12} │ Model: {agent.model}")
            print(f"║     Temp: {agent.temperature}  │ Max Tokens: {agent.max_tokens}")
            print(f"║     Prompt: {agent.system_prompt[:60]}...")
            print("║──────────────────────────────────────────────────")
        print("╚══════════════════════════════════════════════════╝\n")

    def list_pipelines(self):
        """Display all available pipelines."""
        print("\n╔══════════════════════════════════════════════════╗")
        print("║           Available Pipelines                    ║")
        print("╠══════════════════════════════════════════════════╣")
        for key, pipeline in self.pipelines.items():
            steps_str = " → ".join(pipeline.steps)
            print(f"║  📋 {key:<15} │ {pipeline.name}")
            print(f"║     Steps: {steps_str}")
            print(f"║     Output: {pipeline.output_format}")
            print("║──────────────────────────────────────────────────")
        print("╚══════════════════════════════════════════════════╝\n")

    def show_steps(self, pipeline_name: str = "blog"):
        """Show pipeline step progress."""
        if pipeline_name not in self.pipelines:
            print(f"Error: Pipeline '{pipeline_name}' not found.")
            print(f"Available: {', '.join(self.pipelines.keys())}")
            return
        pipeline = self.pipelines[pipeline_name]
        print(f"\n📋 Pipeline: {pipeline.name}")
        print(f"   Format: {pipeline.output_format}")
        print(f"   Steps:")
        for i, step in enumerate(pipeline.steps, 1):
            agent = self.agents.get(step)
            name = agent.name if agent else step
            print(f"   {i}. {name} ({step})")
        print()

    def run(self, topic: str, pipeline_name: str = "blog", output_format: Optional[str] = None) -> str:
        """Run the full pipeline on a topic."""
        if pipeline_name not in self.pipelines:
            print(f"Error: Pipeline '{pipeline_name}' not found.")
            print(f"Available: {', '.join(self.pipelines.keys())}")
            sys.exit(1)

        pipeline = self.pipelines[pipeline_name]
        fmt = output_format or pipeline.output_format
        self.results = []

        print(f"\n{'='*60}")
        print(f"🚀 Multi-Agent Crew - Pipeline: {pipeline.name}")
        print(f"{'='*60}")
        print(f"📝 Topic: {topic}")
        print(f"📋 Steps: {' → '.join(pipeline.steps)}")
        print(f"📄 Output Format: {fmt}")
        print(f"{'='*60}\n")

        context = ""
        total_steps = len(pipeline.steps)
        start_time = time.time()

        for i, step_role in enumerate(pipeline.steps, 1):
            agent = self.agents.get(step_role)
            if not agent:
                print(f"  ⚠ Warning: No agent found for role '{step_role}', skipping.")
                continue

            print(f"\n┌─ Step {i}/{total_steps}: {agent.name} ({agent.role}) ─────────────")
            print(f"│  Model: {agent.model} | Temp: {agent.temperature}")
            print(f"│  Processing...")

            step_start = time.time()

            # Build the prompt based on the step
            if step_role == "researcher":
                prompt = f"Research the following topic thoroughly: {topic}\n\nAdditional context: {pipeline.context}"
            elif step_role == "writer":
                prompt = f"Write content about: {topic}\n\nUse the research provided. {pipeline.context}"
            elif step_role == "editor":
                prompt = f"Edit and improve the following content about '{topic}'. {pipeline.context}"
            elif step_role == "reviewer":
                prompt = f"Review and score the following content about '{topic}'."
            elif step_role == "publisher":
                prompt = f"Format the following content for publication in {fmt} format. Topic: '{topic}'. {pipeline.context}"
            else:
                prompt = f"Process the following content about '{topic}'."

            # Agent thinks
            result = agent.think(prompt, context)
            step_duration = time.time() - step_start

            # Store result
            self.results.append({
                "step": i,
                "agent": agent.name,
                "role": agent.role,
                "model": agent.model,
                "duration_seconds": round(step_duration, 2),
                "output": result,
            })

            # Show thinking process
            preview = result[:200].replace("\n", " ")
            print(f"│  ✓ Done in {step_duration:.1f}s")
            print(f"│  Preview: {preview}...")
            print(f"└{'─'*55}")

            # Pass output as context to next agent
            context = result

        total_duration = time.time() - start_time
        print(f"\n{'='*60}")
        print(f"✅ Pipeline complete in {total_duration:.1f}s")
        print(f"{'='*60}\n")

        # Save output
        final_output = self._format_output(topic, fmt, pipeline_name)
        self._save_output(topic, final_output, fmt, pipeline_name)

        return final_output

    def _format_output(self, topic: str, fmt: str, pipeline_name: str) -> str:
        """Format the final output."""
        if fmt == "json":
            output = {
                "topic": topic,
                "pipeline": pipeline_name,
                "timestamp": datetime.now().isoformat(),
                "steps": self.results,
                "final_content": self.results[-1]["output"] if self.results else "",
            }
            return json.dumps(output, indent=2)
        else:
            # Markdown format
            lines = [
                f"# {topic}",
                f"",
                f"*Generated by Multi-Agent Crew | Pipeline: {pipeline_name}*",
                f"*Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
                f"",
                f"---",
                f"",
            ]
            # Add final content
            if self.results:
                lines.append(self.results[-1]["output"])
            lines.append("")
            lines.append("---")
            lines.append("")
            lines.append("## Pipeline Summary")
            lines.append("")
            for r in self.results:
                lines.append(f"- **{r['agent']}** ({r['role']}): {r['duration_seconds']}s")
            lines.append("")
            return "\n".join(lines)

    def _save_output(self, topic: str, content: str, fmt: str, pipeline_name: str):
        """Save output to file."""
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        slug = topic.lower().replace(" ", "-")[:50]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = "json" if fmt == "json" else "md"
        filename = f"{pipeline_name}_{slug}_{timestamp}.{ext}"
        filepath = OUTPUT_DIR / filename

        with open(filepath, "w") as f:
            f.write(content)

        print(f"💾 Output saved to: {filepath}")


def main():
    parser = argparse.ArgumentParser(
        description="Multi-Agent Crew - AI Pipeline System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --topic "AI in Healthcare"
  %(prog)s --topic "Python Best Practices" --pipeline blog --output markdown
  %(prog)s --topic "Climate Change" --pipeline research
  %(prog)s --agents
  %(prog)s --steps --pipeline video_script
        """,
    )
    parser.add_argument("--topic", "-t", type=str, help="Topic to process through the pipeline")
    parser.add_argument("--agents", action="store_true", help="List all available agents")
    parser.add_argument("--steps", action="store_true", help="Show pipeline steps")
    parser.add_argument("--output", "-o", choices=["markdown", "json"], help="Output format (overrides pipeline default)")
    parser.add_argument("--pipeline", "-p", type=str, default="blog",
                        help="Pipeline to use: blog, video_script, research, social_media")
    parser.add_argument("--agents-file", type=str, help="Custom agents configuration file")
    parser.add_argument("--pipelines-file", type=str, help="Custom pipelines configuration file")

    args = parser.parse_args()

    # Determine config files
    agents_file = Path(args.agents_file) if args.agents_file else AGENTS_FILE
    pipelines_file = Path(args.pipelines_file) if args.pipelines_file else PIPELINES_FILE

    # Initialize crew
    crew = Crew(agents_file=agents_file, pipelines_file=pipelines_file)

    if args.agents:
        crew.list_agents()
        crew.list_pipelines()
        return

    if args.steps:
        crew.show_steps(args.pipeline)
        return

    if not args.topic:
        parser.print_help()
        print("\n⚠ Error: --topic is required to run the pipeline.")
        sys.exit(1)

    # Run the pipeline
    crew.run(args.topic, pipeline_name=args.pipeline, output_format=args.output)


if __name__ == "__main__":
    main()

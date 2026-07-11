#!/Users/amrendranarayanmishra/Downloads/AI/.venv/bin/python3
"""
Fine-Tune Interactive Guide

An interactive guide for fine-tuning LLMs on Apple Silicon Macs.
Supports MLX, Ollama Modelfile, and LoRA methods.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from textwrap import dedent
from typing import Optional

import requests

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
SCRIPT_DIR = Path(__file__).parent
MODELFILE_TEMPLATE = SCRIPT_DIR / "Modelfile.template"


# ─── Guide Content ──────────────────────────────────────────────────────────────

GUIDE_MLX = """
╔══════════════════════════════════════════════════════════════╗
║          Fine-Tuning with MLX (Apple Silicon Native)         ║
╚══════════════════════════════════════════════════════════════╝

MLX is Apple's machine learning framework optimized for Apple Silicon.
It enables efficient fine-tuning directly on your Mac's unified memory.

┌─ Prerequisites ─────────────────────────────────────────────┐
│  • Apple Silicon Mac (M1/M2/M3/M4)                          │
│  • macOS 14+ (Sonoma or later recommended)                  │
│  • Python 3.10+                                             │
│  • 16GB+ RAM (32GB+ recommended for 7B models)              │
└─────────────────────────────────────────────────────────────┘

┌─ Installation ──────────────────────────────────────────────┐
│                                                              │
│  pip install mlx mlx-lm                                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘

┌─ Steps ─────────────────────────────────────────────────────┐
│                                                              │
│  1. Prepare data in JSONL format (use prepare_data.py)      │
│                                                              │
│  2. Convert model to MLX format:                            │
│     python -m mlx_lm.convert \\                              │
│       --hf-path mistralai/Mistral-7B-v0.1 \\                 │
│       --mlx-path ./mlx-model                                │
│                                                              │
│  3. Fine-tune with LoRA:                                    │
│     python -m mlx_lm.lora \\                                 │
│       --model ./mlx-model \\                                  │
│       --data ./data \\                                        │
│       --train \\                                              │
│       --batch-size 4 \\                                       │
│       --lora-layers 16 \\                                     │
│       --iters 1000                                           │
│                                                              │
│  4. Test the fine-tuned model:                              │
│     python -m mlx_lm.generate \\                             │
│       --model ./mlx-model \\                                  │
│       --adapter-path ./adapters \\                            │
│       --prompt "Your test prompt"                            │
│                                                              │
│  5. Fuse adapters into model:                               │
│     python -m mlx_lm.fuse \\                                 │
│       --model ./mlx-model \\                                  │
│       --adapter-path ./adapters \\                            │
│       --save-path ./fused-model                              │
│                                                              │
└─────────────────────────────────────────────────────────────┘

┌─ Tips ──────────────────────────────────────────────────────┐
│  • Start with smaller models (1B-3B) to test your pipeline  │
│  • Use batch-size 1-4 for 16GB RAM, 4-8 for 32GB+          │
│  • Monitor memory with: sudo powermetrics --samplers gpu    │
│  • Training 1000 iterations on 7B takes ~1-2 hours on M2    │
│  • Data quality > quantity: 500 high-quality pairs > 5000   │
└─────────────────────────────────────────────────────────────┘
"""

GUIDE_OLLAMA = """
╔══════════════════════════════════════════════════════════════╗
║       Fine-Tuning with Ollama Modelfile (Easiest)           ║
╚══════════════════════════════════════════════════════════════╝

Ollama Modelfiles let you create custom models with specific
personas, system prompts, and parameters without actual training.
This is the fastest way to customize model behavior.

┌─ Prerequisites ─────────────────────────────────────────────┐
│  • Ollama installed and running                              │
│  • A base model pulled (e.g., llama3.2, mistral)            │
└─────────────────────────────────────────────────────────────┘

┌─ How It Works ──────────────────────────────────────────────┐
│                                                              │
│  A Modelfile defines:                                        │
│  • FROM: Base model to customize                             │
│  • SYSTEM: System prompt (persona/instructions)              │
│  • PARAMETER: Temperature, top_p, etc.                       │
│  • TEMPLATE: Custom prompt template                          │
│  • MESSAGE: Few-shot examples                                │
│                                                              │
└─────────────────────────────────────────────────────────────┘

┌─ Steps ─────────────────────────────────────────────────────┐
│                                                              │
│  1. Create a Modelfile (use --create-modelfile flag)         │
│                                                              │
│  2. Build the custom model:                                  │
│     ollama create my-model -f Modelfile                      │
│                                                              │
│  3. Test it:                                                 │
│     ollama run my-model "Hello, who are you?"                │
│                                                              │
│  4. Use via API:                                             │
│     curl http://localhost:11434/api/chat -d '{               │
│       "model": "my-model",                                   │
│       "messages": [{"role":"user","content":"Hi"}]           │
│     }'                                                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘

┌─ Advantages ────────────────────────────────────────────────┐
│  • No training required - instant results                    │
│  • No extra RAM needed beyond model inference                │
│  • Easy to iterate and experiment                            │
│  • Can add few-shot examples for better behavior             │
│  • Share custom models via ollama push                       │
└─────────────────────────────────────────────────────────────┘

┌─ Limitations ───────────────────────────────────────────────┐
│  • Doesn't change model weights                              │
│  • Limited by base model's capabilities                      │
│  • System prompt can be "forgotten" in long conversations    │
│  • Not true fine-tuning, more like prompt engineering         │
└─────────────────────────────────────────────────────────────┘
"""

GUIDE_LORA = """
╔══════════════════════════════════════════════════════════════╗
║           Fine-Tuning with LoRA (Advanced)                   ║
╚══════════════════════════════════════════════════════════════╝

LoRA (Low-Rank Adaptation) adds small trainable adapters to a
frozen base model. It's memory-efficient and produces portable
adapter weights that can be merged or swapped.

┌─ Prerequisites ─────────────────────────────────────────────┐
│  • Apple Silicon Mac with 32GB+ RAM (for 7B models)          │
│  • Python 3.10+ with pip                                     │
│  • Training data in JSONL format                             │
│  • ~2-4 hours training time for 7B model                     │
└─────────────────────────────────────────────────────────────┘

┌─ Installation ──────────────────────────────────────────────┐
│                                                              │
│  # Option A: MLX LoRA (recommended for Mac)                  │
│  pip install mlx mlx-lm                                      │
│                                                              │
│  # Option B: Unsloth (if you have GPU access)                │
│  pip install unsloth                                          │
│                                                              │
│  # Option C: HuggingFace PEFT                                │
│  pip install peft transformers datasets accelerate            │
│                                                              │
└─────────────────────────────────────────────────────────────┘

┌─ Data Format ───────────────────────────────────────────────┐
│                                                              │
│  JSONL with instruction/input/output format:                 │
│  {"instruction": "...", "input": "...", "output": "..."}     │
│                                                              │
│  Recommended: 500-5000 high-quality pairs                    │
│  Split: 90% train, 10% validation                            │
│                                                              │
└─────────────────────────────────────────────────────────────┘

┌─ MLX LoRA Steps ────────────────────────────────────────────┐
│                                                              │
│  1. Prepare data:                                            │
│     python prepare_data.py --input ./raw --source documents  │
│                                                              │
│  2. Split into train/valid:                                  │
│     Split data/training.jsonl → train.jsonl + valid.jsonl    │
│                                                              │
│  3. Train:                                                   │
│     python -m mlx_lm.lora \\                                  │
│       --model mlx-community/Llama-3.2-3B-4bit \\             │
│       --data ./data \\                                        │
│       --train \\                                              │
│       --batch-size 2 \\                                       │
│       --lora-layers 8 \\                                      │
│       --iters 500 \\                                          │
│       --learning-rate 1e-5                                   │
│                                                              │
│  4. Evaluate:                                                │
│     python -m mlx_lm.lora \\                                  │
│       --model mlx-community/Llama-3.2-3B-4bit \\             │
│       --adapter-path ./adapters \\                            │
│       --data ./data \\                                        │
│       --test                                                 │
│                                                              │
│  5. Convert to GGUF for Ollama:                              │
│     python -m mlx_lm.fuse ... → convert to GGUF             │
│     ollama create my-lora-model -f Modelfile                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘

┌─ Key Parameters ────────────────────────────────────────────┐
│  • lora-layers: 4-32 (more = better quality, more memory)    │
│  • batch-size: 1-8 (limited by RAM)                          │
│  • learning-rate: 1e-5 to 5e-5                               │
│  • iters: 200-2000 (watch for overfitting)                   │
│  • lora-rank: 8-64 (higher = more parameters)                │
└─────────────────────────────────────────────────────────────┘
"""


# ─── Modelfile Generation ────────────────────────────────────────────────────────

def generate_modelfile(
    base_model: str = "llama3.2",
    persona_name: str = "assistant",
    system_prompt: str = "",
    temperature: float = 0.7,
    top_p: float = 0.9,
    output_path: Optional[Path] = None,
) -> str:
    """Generate a Modelfile for Ollama."""
    if not system_prompt:
        system_prompt = f"""You are {persona_name}, a helpful and knowledgeable AI assistant. You provide clear, accurate, and concise responses. You are friendly but professional, and you always strive to be helpful while being honest about your limitations."""

    modelfile = f"""# Modelfile for {persona_name}
# Generated by finetune_guide.py on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# Base model: {base_model}

FROM {base_model}

# System prompt defining the model's persona
SYSTEM \"\"\"
{system_prompt}
\"\"\"

# Model parameters
PARAMETER temperature {temperature}
PARAMETER top_p {top_p}
PARAMETER top_k 40
PARAMETER num_predict 2048
PARAMETER repeat_penalty 1.1
PARAMETER stop "<|eot_id|>"
PARAMETER stop "<|end_of_turn|>"
PARAMETER stop "</s>"

# Template (uses default chat template from base model)
# Uncomment and customize if needed:
# TEMPLATE \"\"\"
# {{{{ if .System }}}}<|start_header_id|>system<|end_header_id|>
# {{{{ .System }}}}<|eot_id|>{{{{ end }}}}
# <|start_header_id|>user<|end_header_id|>
# {{{{ .Prompt }}}}<|eot_id|>
# <|start_header_id|>assistant<|end_header_id|>
# {{{{ .Response }}}}<|eot_id|>
# \"\"\"
"""

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(modelfile)
        print(f"💾 Modelfile saved to: {output_path}")

    return modelfile


def create_ollama_model(modelfile_path: Path, model_name: str):
    """Create an Ollama model from a Modelfile."""
    print(f"\n🔨 Creating Ollama model '{model_name}' from {modelfile_path}...")

    try:
        # Use Ollama API to create model
        with open(modelfile_path) as f:
            modelfile_content = f.read()

        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/create",
            json={"name": model_name, "modelfile": modelfile_content},
            stream=True,
            timeout=300,
        )
        resp.raise_for_status()

        for line in resp.iter_lines():
            if line:
                data = json.loads(line)
                status = data.get("status", "")
                if status:
                    print(f"   {status}")

        print(f"\n✅ Model '{model_name}' created successfully!")
        print(f"   Run with: ollama run {model_name}")
        return True

    except requests.ConnectionError:
        print(f"✗ Cannot connect to Ollama at {OLLAMA_BASE_URL}")
        print("  Make sure Ollama is running: ollama serve")
        return False
    except Exception as e:
        print(f"✗ Error creating model: {e}")
        return False


def test_model(model_name: str, prompt: str = "Hello! Who are you and what can you help me with?"):
    """Test a model with a sample prompt."""
    print(f"\n🧪 Testing model '{model_name}'...")
    print(f"   Prompt: {prompt}")
    print(f"   {'─'*50}")

    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        response = data.get("message", {}).get("content", "No response")

        print(f"\n   Response:")
        print(f"   {'─'*50}")
        for line in response.split("\n"):
            print(f"   {line}")
        print(f"   {'─'*50}")

        # Show timing info
        total_duration = data.get("total_duration", 0) / 1e9
        eval_count = data.get("eval_count", 0)
        if total_duration > 0:
            print(f"\n   ⏱  Duration: {total_duration:.2f}s")
            if eval_count:
                print(f"   📊 Tokens: {eval_count} ({eval_count/total_duration:.1f} tok/s)")

        return True

    except requests.ConnectionError:
        print(f"✗ Cannot connect to Ollama at {OLLAMA_BASE_URL}")
        return False
    except requests.HTTPError as e:
        print(f"✗ Error: {e}")
        if "not found" in str(e).lower() or resp.status_code == 404:
            print(f"  Model '{model_name}' not found. Create it first with --create-modelfile")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def interactive_modelfile_creation():
    """Interactive wizard for creating a Modelfile."""
    print("\n╔══════════════════════════════════════════════════════════════╗")
    print("║         Interactive Modelfile Creator                         ║")
    print("╚══════════════════════════════════════════════════════════════╝\n")

    # Get base model
    print("Available base models (make sure they're pulled in Ollama):")
    print("  1. llama3.2 (default, good all-rounder)")
    print("  2. mistral (fast, good for chat)")
    print("  3. codellama (optimized for code)")
    print("  4. phi3 (small but capable)")
    print("  5. custom (enter model name)")
    print()

    choice = input("Select base model [1]: ").strip() or "1"
    models = {"1": "llama3.2", "2": "mistral", "3": "codellama", "4": "phi3"}
    if choice == "5":
        base_model = input("Enter model name: ").strip()
    else:
        base_model = models.get(choice, "llama3.2")

    # Get persona
    persona_name = input("\nPersona name [assistant]: ").strip() or "assistant"

    # Get system prompt
    print(f"\nEnter system prompt for {persona_name}")
    print("(Press Enter twice to finish, or leave empty for default):")
    lines = []
    while True:
        line = input()
        if line == "" and (not lines or lines[-1] == ""):
            break
        lines.append(line)
    system_prompt = "\n".join(lines).strip()

    # Get parameters
    try:
        temperature = float(input("\nTemperature [0.7]: ").strip() or "0.7")
    except ValueError:
        temperature = 0.7
    try:
        top_p = float(input("Top-p [0.9]: ").strip() or "0.9")
    except ValueError:
        top_p = 0.9

    # Model name for Ollama
    model_name = input(f"\nOllama model name [{persona_name}]: ").strip() or persona_name

    # Generate
    output_path = SCRIPT_DIR / f"Modelfile.{model_name}"
    modelfile = generate_modelfile(
        base_model=base_model,
        persona_name=persona_name,
        system_prompt=system_prompt,
        temperature=temperature,
        top_p=top_p,
        output_path=output_path,
    )

    print(f"\n📄 Generated Modelfile:")
    print("─" * 60)
    print(modelfile)
    print("─" * 60)

    # Offer to create the model
    create = input(f"\nCreate model '{model_name}' in Ollama now? [y/N]: ").strip().lower()
    if create == "y":
        success = create_ollama_model(output_path, model_name)
        if success:
            test = input(f"\nTest the model now? [y/N]: ").strip().lower()
            if test == "y":
                test_model(model_name)


def show_guide(method: str):
    """Display the guide for a specific method."""
    guides = {
        "mlx": GUIDE_MLX,
        "ollama_modelfile": GUIDE_OLLAMA,
        "lora": GUIDE_LORA,
    }

    if method == "all":
        for guide in guides.values():
            print(guide)
    elif method in guides:
        print(guides[method])
    else:
        print(f"Unknown method: {method}")
        print(f"Available: {', '.join(guides.keys())}")


def main():
    parser = argparse.ArgumentParser(
        description="Fine-Tune Interactive Guide for Apple Silicon",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --method mlx              # Show MLX fine-tuning guide
  %(prog)s --method ollama_modelfile  # Show Ollama Modelfile guide
  %(prog)s --method lora             # Show LoRA fine-tuning guide
  %(prog)s --create-modelfile        # Interactive Modelfile creator
  %(prog)s --test my-model           # Test a custom model
  %(prog)s --method all              # Show all guides
        """,
    )
    parser.add_argument("--method", "-m", type=str,
                        choices=["mlx", "ollama_modelfile", "lora", "all"],
                        help="Fine-tuning method to explain")
    parser.add_argument("--create-modelfile", action="store_true",
                        help="Interactive Modelfile creation wizard")
    parser.add_argument("--test", type=str, metavar="MODEL",
                        help="Test a custom model")
    parser.add_argument("--test-prompt", type=str,
                        default="Hello! Who are you and what can you help me with?",
                        help="Custom prompt for testing")
    parser.add_argument("--generate-modelfile", type=str, metavar="NAME",
                        help="Generate a Modelfile non-interactively")
    parser.add_argument("--base-model", type=str, default="llama3.2",
                        help="Base model for Modelfile generation")
    parser.add_argument("--system-prompt", type=str, default="",
                        help="System prompt for Modelfile generation")
    parser.add_argument("--temperature", type=float, default=0.7,
                        help="Temperature for Modelfile generation")

    args = parser.parse_args()

    if args.create_modelfile:
        interactive_modelfile_creation()
        return

    if args.test:
        test_model(args.test, args.test_prompt)
        return

    if args.generate_modelfile:
        output_path = SCRIPT_DIR / f"Modelfile.{args.generate_modelfile}"
        modelfile = generate_modelfile(
            base_model=args.base_model,
            persona_name=args.generate_modelfile,
            system_prompt=args.system_prompt,
            temperature=args.temperature,
            output_path=output_path,
        )
        print(f"\n📄 Generated Modelfile:")
        print("─" * 60)
        print(modelfile)
        print("─" * 60)
        print(f"\nTo create the model: ollama create {args.generate_modelfile} -f {output_path}")
        return

    if args.method:
        show_guide(args.method)
        return

    # Default: show overview
    print("""
╔══════════════════════════════════════════════════════════════╗
║       Fine-Tuning Guide for Apple Silicon Macs              ║
╚══════════════════════════════════════════════════════════════╝

Choose a fine-tuning method:

┌─────────────────────────────────────────────────────────────┐
│                                                              │
│  1. Ollama Modelfile (--method ollama_modelfile)             │
│     • Easiest: No training needed                            │
│     • Customize persona via system prompt                    │
│     • Instant results, good for behavior tuning              │
│                                                              │
│  2. MLX Fine-Tuning (--method mlx)                          │
│     • Native Apple Silicon performance                       │
│     • True weight updates via LoRA                           │
│     • Best balance of quality vs effort on Mac               │
│                                                              │
│  3. LoRA Advanced (--method lora)                            │
│     • Full LoRA training pipeline                            │
│     • Multiple framework options                             │
│     • Best for serious fine-tuning projects                  │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Quick Actions:                                              │
│    --create-modelfile     Create a custom Ollama model       │
│    --test <model>         Test any model                     │
│    --method all           Show all guides                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘

Recommended Workflow:
  1. Start with Ollama Modelfile for quick persona customization
  2. If you need deeper customization, prepare data with prepare_data.py
  3. Use MLX LoRA for actual fine-tuning on Apple Silicon
""")


if __name__ == "__main__":
    main()

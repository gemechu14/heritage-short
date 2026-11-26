"""ACE-Step 1.5 score candidates on a Kaggle GPU (T4 is enough: the turbo DiT needs ~6 GB).

How to run (Kaggle notebook, GPU T4 x2 or P100, Internet ON):
  1. Upload outputs/music/ace_step_job.json from the repo as a Kaggle dataset, or paste its
     contents into JOB below.
  2. In the first cell:
       !git clone https://github.com/ACE-Step/ACE-Step-1.5.git
       %cd ACE-Step-1.5
       !pip install -q uv && uv pip install --system -e .
  3. In the next cell paste this file and run it.
  4. Download /kaggle/working/candidates/*.wav and copy them into outputs/music/candidates/
     in the repo, then: python -m pipeline.music --choose candidate_seed22.wav --why "..."

API calls follow docs/en/INFERENCE.md in the ACE-Step-1.5 repo (GenerationParams,
GenerationConfig, generate_music). The language-model planner is switched off
(ACESTEP_INIT_LLM=false): the caption already says what we want, and it saves memory.
If the API has moved, check that file first, and note what changed in FAILURES.md.
"""
import json
import os
import shutil
import time
from pathlib import Path

os.environ.setdefault("ACESTEP_INIT_LLM", "false")

JOB_PATHS = [Path("/kaggle/input/heritage-short/ace_step_job.json"), Path("ace_step_job.json")]
JOB = None  # or paste the JSON from outputs/music/ace_step_job.json here as a dict
OUT = Path("/kaggle/working/candidates")


def load_job():
    if JOB:
        return JOB
    for p in JOB_PATHS:
        if p.exists():
            return json.loads(p.read_text())
    raise SystemExit("ace_step_job.json not found: upload it or paste it into JOB")


def main():
    from acestep.handler import AceStepHandler
    from acestep.inference import GenerationConfig, GenerationParams, generate_music

    job = load_job()
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    dit = AceStepHandler()
    dit.initialize_service(project_root=os.getcwd(), config_path=job.get("model", "acestep-v15-turbo"),
                           device="cuda")
    load_s = time.time() - t0

    log = []
    for seed in job["seeds"]:
        params = GenerationParams(caption=job["caption"], lyrics=job.get("lyrics", "[Instrumental]"),
                                  instrumental=True, duration=float(job["duration"]), seed=seed,
                                  inference_steps=job.get("inference_steps", 8))
        config = GenerationConfig(batch_size=1, use_random_seed=False, audio_format="wav")
        t = time.time()
        result = generate_music(dit, None, params, config, save_dir=str(OUT / f"raw_{seed}"))
        secs = time.time() - t
        src = Path(result.audios[0]["path"])
        dst = OUT / f"candidate_seed{seed}.wav"
        shutil.copyfile(src, dst)
        log.append({"seed": seed, "file": dst.name, "latency_s": round(secs, 1),
                    "sample_rate": result.audios[0].get("sample_rate")})
        print(f"seed {seed}: {secs:.1f}s -> {dst}")

    summary = {"model": job.get("model"), "load_s": round(load_s, 1), "candidates": log,
               "gpu": os.popen("nvidia-smi --query-gpu=name --format=csv,noheader").read().strip()}
    (OUT / "ace_step_log.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print("Copy ace_step_log.json too: its latencies go into COSTS.md.")


if __name__ == "__main__":
    main()

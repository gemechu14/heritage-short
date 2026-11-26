# Wan 2.2 moving shots (optional)

The storyboard marks three shots as `"motion": {"type": "wan"}`: s01, s04 and s09. If a clip exists at
`outputs/shots/wan/<shot>.mp4`, `python -m pipeline.shots` uses it; otherwise the shot falls back to an
FFmpeg pan and zoom over the keyframe, and the pipeline still finishes.

**Memory warning.** The Wan 2.2 README says TI2V-5B with `--offload_model True --convert_model_dtype --t5_cpu`
"can run on a GPU with at least 24GB VRAM (e.g., RTX 4090)". A Kaggle T4 has 16 GB, so expect an
out-of-memory error at 1280×704. Record what happens in FAILURES.md either way.

## Kaggle cells (GPU, Internet on)

```bash
!git clone https://github.com/Wan-Video/Wan2.2.git
%cd Wan2.2
!pip install -q -r requirements.txt   # if flash_attn fails, install the rest first, flash_attn last
!pip install -q "huggingface_hub[cli]"
!huggingface-cli download Wan-AI/Wan2.2-TI2V-5B --local-dir ./Wan2.2-TI2V-5B
```

Upload the keyframes for s01, s04 and s09 (from `outputs/keyframes/`), then for each shot
(prompt = the shot's `motion_prompt` from storyboard.json; seed = its `seed`):

```bash
!python generate.py --task ti2v-5B --size 1280*704 --ckpt_dir ./Wan2.2-TI2V-5B \
  --offload_model True --convert_model_dtype --t5_cpu \
  --image /kaggle/input/keyframes/s01.jpg --base_seed 1001 --frame_num 121 \
  --prompt "slow push-in, mist drifting, smoke rising gently, fixed horizon" \
  --save_file /kaggle/working/s01.mp4
```

`--frame_num` must be 4n+1; 121 frames is about 5 s at 24 fps. Time each run (it goes into COSTS.md),
download the mp4s into `outputs/shots/wan/`, and run `python -m pipeline.shots`. Only those shots re-render.

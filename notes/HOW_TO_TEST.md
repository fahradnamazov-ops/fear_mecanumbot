# How to test

```bash
cd fear_mecanumbot
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate.bat
pip install -r requirements.txt
python scripts/check_setup.py
pytest -v
python scripts/residual_fear_demo.py
python scripts/train_hri_rl.py
python scripts/run_hri_rl.py
python scripts/scan_fear_preview.py
python scripts/v1_final_demo.py
```

If `v1_final_demo.py` prints `pytest: FAILED (pytest not installed)`, run `pip install -r requirements.txt` in **this** folder.

Residual demo: gap > 0 after the person is far.  
Train writes `models/hri_q.npy`.  
`v1_final_demo.py` writes `output/v1_summary.json`.

See `notes/LOCAL_VS_ROS.md` for what is simulated locally vs planned on `/scan`.

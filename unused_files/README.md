# unused_files

Files moved out of the main project tree during a cleanup pass (2026-08-01) because they were stray, duplicate, or superseded — not because they're confirmed safe to delete. Review before removing permanently.

## root/
- `OrganicLink_Codebase.zip` — old zip snapshot of the codebase, not referenced by any code.
- `organiclink.db` — stray duplicate DB at repo root. The app's real DB (per `backend/config.py`) lives at `backend/organiclink.db`.
- `test_organiclink.db` — stray duplicate test DB at repo root, same reasoning.

## backend/
- `test_organiclink.db` — duplicate/leftover test DB inside `backend/`, regenerated automatically by the test suite.

## backend_cv/
- `debug/` — debug output images (`bulk_grading_annotated.jpg`, `detection_debug.jpg`) written by CV scripts during manual runs, not source.
- `inference_WORKING.py` — an older, superseded copy of `backend/cv/inference.py`. Not imported anywhere in the app.
- `dedupe_check.py` / `rescore_dedup.py` — one-off dataset-cleanup scripts used during model dev, not imported by the app or its tests.

## Not moved (left in place, still needed)
- `backend/cv/data/`, `backend/cv/quality dataset/` — active training datasets used by `backend/cv/train.py` (8.1GB total, skipped per your instruction).
- `backend/cv/models_backup/` — intentionally kept per `.gitignore` exception as a backup of `quality_model.pt`.
- `backend/yolov8n.pt` — used as a fallback COCO model in `backend/cv/detection.py`.
- `scratch/` — already a self-labeled scratch folder for manual verification scripts.
- `PROJECT_STATUS.md` — a dated but legitimate audit doc, not clutter.

## Also cleaned up (deleted, not moved)
`__pycache__/` and `.pytest_cache/` folders across the backend were untracked from git and deleted from disk — they were accidentally committed despite being gitignored, and moving them is pointless since Python/pytest regenerate them in their original location on the next run.

"""One-command regeneration of statistical tables, figures and signed verdict."""
from pathlib import Path
import hashlib
from report import main as summarize
from manuscript import main as manuscript
from run import TASK,save

if __name__=="__main__":
    summarize()
    manuscript()
    entries={}
    for p in sorted(TASK.rglob("*")):
        if not p.is_file() or p.name=="manifest.json" or p.suffix in (".tmp",".lock",".pyc"):
            continue
        if "development_point_calibration_episodes" in p.parts or "__pycache__" in p.parts:
            continue
        data=p.read_bytes()
        if p.suffix!=".png":
            data=data.replace(b"\r\n",b"\n")
        entries[p.relative_to(TASK).as_posix()]=hashlib.sha256(data).hexdigest()
    save(TASK/"manifest.json",dict(algorithm="SHA-256; UTF-8 text with LF, binary PNG unmodified",files=entries))

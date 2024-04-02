import os
from glob import glob

[os.remove(f) for f in glob("./execution-*-*.log")]
[os.remove(f) for f in glob("./failure_*.txt")]
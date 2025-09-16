# Installation

```bash
# From source (editable)
git clone https://github.com/VitPavelka/sciwork.git
cd sciwork
pip install -e .[docs]

# From GitHub (non-editable)
pip install "git+https://github.com/VitPavelka/sciwork.git"

# Then
from robust_config import RobustConfig, KeySpec

# And the CLI is available as:
robust-config --help
```
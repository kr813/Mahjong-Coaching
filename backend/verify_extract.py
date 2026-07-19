import sys
from pathlib import Path
sys.path.insert(0, r'c:\Users\champ\bunkakai\Bunkakai_migToOCI\Mahjong-Coaching\backend')
import extract
html_path = Path(r'c:\Users\champ\bunkakai\Bunkakai_migToOCI\Mahjong-Coaching\backend\result\url-20260718-220738.html')
print(extract.extract_report(str(html_path)))

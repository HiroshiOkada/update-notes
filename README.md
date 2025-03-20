# update-notes

A simple command-line tool to process Obsidian Markdown files.

## Installation

```bash
pipx install git+https://github.com/YourUsername/update-notes.git
```

## Usage

```bash
update-notes /path/to/obsidian/vault [-i INPUT_DIR] [-o OUTPUT_DIR]
```

### Required Arguments:
- Path to Obsidian vault directory - The root directory of your Obsidian vault

### Optional Arguments:
- `-i, --input-dir`: Input directory name within the vault (default: "日々の記録")
- `-o, --output-dir`: Output directory name within the vault (default: input_dir + "まとめ")

### Notes:
- The input directory must exist within your vault
- The output directory will be created if it doesn't exist
- The tool processes Markdown files in the format `yyyy-mm-dd.md` (e.g., `2023-01-15.md`)
- Files are processed in chronological order
- Markdown content is split by headings (any level: #, ##, ###, etc.)
- Content before the first heading is treated as if it belongs to a heading called "# はじめに"
- Output files are named after the headings (e.g., "はじめに.md", "旅行.md")
- Each section in the output files includes a level 2 heading with the date (e.g., "## 2023-01-15")
- Empty sections are skipped
- Processed files are moved to an "oldfiles" directory within the input directory
- Referenced image files are copied from the input directory to the output directory
- Both standard Markdown image syntax `![alt](path)` and Obsidian wiki syntax `![[path]]` are supported

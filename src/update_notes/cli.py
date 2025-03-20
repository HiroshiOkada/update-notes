"""Command line interface for update-notes."""

import argparse
import sys
from pathlib import Path

from update_notes.processor import process_markdown_files


def main():
    """Execute the main program."""
    parser = argparse.ArgumentParser(description="Process Obsidian Markdown files")
    parser.add_argument(
        "vault_dir", type=str, help="Path to Obsidian vault directory"
    )
    parser.add_argument(
        "-i", "--input-dir", type=str, default="日々の記録",
        help="Input directory name within the vault (default: '日々の記録')"
    )
    parser.add_argument(
        "-o", "--output-dir", type=str,
        help="Output directory name within the vault (default: input_dir + 'まとめ')"
    )
    
    args = parser.parse_args()
    vault_path = Path(args.vault_dir)
    
    if not vault_path.exists() or not vault_path.is_dir():
        print(f"Error: {vault_path} is not a valid directory", file=sys.stderr)
        sys.exit(1)
    
    input_dir = args.input_dir
    input_path = vault_path / input_dir
    
    if not input_path.exists() or not input_path.is_dir():
        print(f"Error: Input directory '{input_dir}' does not exist in the vault", file=sys.stderr)
        sys.exit(1)
    
    output_dir = args.output_dir if args.output_dir else input_dir + "まとめ"
    output_path = vault_path / output_dir
    
    # Create output directory if it doesn't exist
    output_path.mkdir(exist_ok=True, parents=True)
    
    # Process the markdown files
    process_markdown_files(input_path, output_path)
    

if __name__ == "__main__":
    main()

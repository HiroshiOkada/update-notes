"""Process Obsidian Markdown files."""

import re
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Tuple, Set


def process_markdown_files(input_directory: Path, output_directory: Path) -> None:
    """Process all markdown files in the given directory.
    
    Args:
        input_directory: Path to the directory containing markdown files
        output_directory: Path to the directory where processed files will be saved
    """
    print(f"Processing markdown files from {input_directory}")
    print(f"Output will be saved to {output_directory}")
    
    # Create oldfiles directory for processed files
    oldfiles_dir = input_directory / "oldfiles"
    oldfiles_dir.mkdir(exist_ok=True)
    print(f"Processed files will be moved to {oldfiles_dir}")
    
    # Find all markdown files with yyyy-mm-dd.md pattern
    date_pattern = re.compile(r'^(\d{4})-(\d{2})-(\d{2})\.md$')
    daily_notes = []
    
    for file_path in input_directory.glob("*.md"):
        match = date_pattern.match(file_path.name)
        if match:
            # Parse date from filename
            year, month, day = match.groups()
            try:
                file_date = datetime(int(year), int(month), int(day))
                date_str = f"{year}-{month}-{day}"
                daily_notes.append((file_path, file_date, date_str))
            except ValueError:
                # Skip files with invalid dates
                print(f"Skipping file with invalid date: {file_path.name}")
    
    # Sort files by date
    daily_notes.sort(key=lambda x: x[1])
    
    print(f"Found {len(daily_notes)} daily note files")
    
    # Dictionary to accumulate content by heading
    heading_contents: Dict[str, List[str]] = {}
    
    # Set to track all referenced image files
    all_image_refs: Set[str] = set()
    
    # Process each file in chronological order
    for file_path, file_date, date_str in daily_notes:
        file_sections, image_refs = process_file(file_path, date_str)
        
        # Accumulate sections by heading
        for heading, content in file_sections.items():
            if heading not in heading_contents:
                heading_contents[heading] = []
            
            # Only add content if it's not empty
            if content and not all(line.strip() == "" for line in content):
                heading_contents[heading].extend(content)
        
        # Add image references
        all_image_refs.update(image_refs)
        
        # Move the processed file to oldfiles directory
        destination = oldfiles_dir / file_path.name
        try:
            # Windows workaround: First try to rename, if that fails try copy and delete
            try:
                file_path.rename(destination)
            except OSError:
                # If rename fails (common on Windows), try copy and delete
                shutil.copy2(file_path, destination)
                os.unlink(file_path)
            print(f"Moved {file_path.name} to oldfiles directory")
        except Exception as e:
            print(f"Error moving {file_path.name}: {e}")
            print("The file will be kept in its original location")
    
    # Copy referenced image files to output directory
    copy_image_files(input_directory, output_directory, all_image_refs)
    
    # Write each heading to a separate file
    write_output_files(heading_contents, output_directory)


def process_file(file_path: Path, date_str: str) -> Tuple[Dict[str, List[str]], Set[str]]:
    """Process a single markdown file.
    
    Args:
        file_path: Path to the markdown file
        date_str: Date string in yyyy-mm-dd format from the filename
    
    Returns:
        Tuple of (Dictionary mapping headings to their content, Set of image references)
    """
    print(f"Processing {file_path.name}")
    
    # Parse the file content
    with open(file_path, 'r', encoding='utf-8') as infile:
        content = infile.read()
    
    # Split content by headings
    # Regex matches any markdown heading (# followed by space and text)
    heading_pattern = re.compile(r'^(#{1,6}\s+.+)$', re.MULTILINE)
    
    # Split the content by headings
    sections: Dict[str, List[str]] = {}
    current_heading = "# はじめに"  # Default heading for content before first heading
    sections[current_heading] = []
    
    # Process the file line by line
    for line in content.split('\n'):
        # Check if line is a heading
        if heading_pattern.match(line):
            current_heading = line
            # Initialize the list for this heading if it doesn't exist
            if current_heading not in sections:
                sections[current_heading] = []
        else:
            # Add the line to the current heading's content
            sections[current_heading].append(line)
    
    # Add the date header to the beginning of each section's content
    date_header = f"## {date_str}"
    for heading, lines in sections.items():
        # Only add the date header if there's non-empty content
        if lines and not all(line.strip() == "" for line in lines):
            sections[heading] = [date_header, ""] + lines + [""]
    
    # Find all referenced image files
    image_references = find_image_references(content)
    
    return sections, image_references


def find_image_references(content: str) -> Set[str]:
    """Find all referenced image files in Markdown content.
    
    Args:
        content: Markdown content
    
    Returns:
        Set of image file paths
    """
    # Regex patterns for both Markdown image syntax ![alt](path) and wiki syntax ![[path]]
    md_image_pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
    wiki_image_pattern = re.compile(r'!\[\[([^\]]+)\]\]')
    
    image_paths = set()
    
    # Find Markdown style images
    for match in md_image_pattern.finditer(content):
        image_path = match.group(2)
        # Remove any URL fragments or query parameters
        image_path = image_path.split('#')[0].split('?')[0]
        # Remove any URL scheme
        if '://' in image_path:
            continue  # Skip external images
        image_paths.add(image_path)
    
    # Find Obsidian wiki style images
    for match in wiki_image_pattern.finditer(content):
        image_path = match.group(1)
        # In Obsidian, image references might not include the file extension
        image_paths.add(image_path)
    
    return image_paths


def copy_image_files(input_directory: Path, output_directory: Path, image_refs: Set[str]) -> None:
    """Copy referenced image files from the input directory to the output directory.
    
    Args:
        input_directory: Source directory
        output_directory: Destination directory
        image_refs: Set of image file paths or references
    """
    if not image_refs:
        return
    
    print(f"Copying referenced image files...")
    
    # Common image extensions
    image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.webp']
    
    # Track images that were copied
    copied_images = []
    
    for ref in image_refs:
        # Check if the reference is a direct path
        ref_path = Path(ref)
        
        # Check if the referenced file exists in the input directory
        source_path = input_directory / ref_path
        if source_path.exists() and source_path.is_file():
            # Copy the image file to the output directory
            dest_path = output_directory / ref_path.name
            try:
                # Create parent directories if needed
                dest_path.parent.mkdir(exist_ok=True, parents=True)
                shutil.copy2(source_path, dest_path)
                copied_images.append(ref_path.name)
            except Exception as e:
                print(f"Error copying image {ref_path.name}: {e}")
            continue

        # If the reference doesn't have a file extension (common in Obsidian),
        # try adding common image extensions
        if not ref_path.suffix:
            for ext in image_extensions:
                source_path = input_directory / f"{ref}{ext}"
                if source_path.exists() and source_path.is_file():
                    # Copy the image file to the output directory
                    dest_path = output_directory / f"{ref_path.name}{ext}"
                    try:
                        # Create parent directories if needed
                        dest_path.parent.mkdir(exist_ok=True, parents=True)
                        shutil.copy2(source_path, dest_path)
                        copied_images.append(f"{ref_path.name}{ext}")
                    except Exception as e:
                        print(f"Error copying image {ref_path.name}{ext}: {e}")
                    break
    
    if copied_images:
        print(f"Copied {len(copied_images)} image files: {', '.join(copied_images[:5])}{'...' if len(copied_images) > 5 else ''}")
    else:
        print("No image files found to copy")


def write_output_files(heading_contents: Dict[str, List[str]], output_directory: Path) -> None:
    """Write accumulated content to output files by heading.
    
    Args:
        heading_contents: Dictionary mapping headings to their content
        output_directory: Directory to write the output files
    """
    # Create output directory if it doesn't exist
    output_directory.mkdir(exist_ok=True, parents=True)
    
    # Process each heading
    for heading, content in heading_contents.items():
        # Skip empty content
        if not content or all(line.strip() == "" for line in content):
            continue
        
        # Create a safe filename from the heading
        # Remove the heading marks (# characters) and trim
        heading_text = heading.lstrip('#').strip()
        # Replace any characters that aren't safe for filenames
        safe_filename = re.sub(r'[\\/*?:"<>|]', '_', heading_text) + '.md'
        
        # Create the output file path
        output_file_path = output_directory / safe_filename
        
        # Check if file already exists and append instead of overwriting
        if output_file_path.exists():
            # Read existing content
            with open(output_file_path, 'r', encoding='utf-8') as infile:
                existing_content = infile.read().rstrip()
            
            # Append the new content
            with open(output_file_path, 'w', encoding='utf-8') as outfile:
                # Check if existing content already has the heading
                heading_line = heading + '\n'
                if heading_line in existing_content:
                    # If heading already exists, just append the content without the heading
                    outfile.write(existing_content + '\n\n' + '\n'.join(content))
                else:
                    # If heading doesn't exist, append with the heading
                    outfile.write(existing_content + '\n\n' + '\n'.join([heading] + [""] + content))
            
            print(f"Appended to existing file for heading '{heading_text}' at {output_file_path.name}")
        else:
            # Create a new file if it doesn't exist
            with open(output_file_path, 'w', encoding='utf-8') as outfile:
                outfile.write('\n'.join([heading] + [""] + content))
            
            print(f"Created new file for heading '{heading_text}' at {output_file_path.name}")
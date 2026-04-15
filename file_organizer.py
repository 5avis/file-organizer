import os
import shutil
import argparse
import logging
import json
from pathlib import Path

# --- Configuration ---

EXTENSION_MAPPING = {
    # Images
    '.jpg': 'Images',
    '.jpeg': 'Images',
    '.png': 'Images',
    '.gif': 'Images',
    '.svg': 'Images',
    '.bmp': 'Images',
    
    # Videos
    '.mp4': 'Videos',
    '.mkv': 'Videos',
    '.avi': 'Videos',
    '.mov': 'Videos',
    
    # Documents
    '.pdf': 'Documents',
    '.docx': 'Documents',
    '.doc': 'Documents',
    '.txt': 'Documents',
    '.xlsx': 'Documents',
    '.pptx': 'Documents',
    '.csv': 'Documents',
    
    # Audio
    '.mp3': 'Audio',
    '.wav': 'Audio',
    '.aac': 'Audio',
    '.flac': 'Audio',
    
    # Code
    '.py': 'Code',
    '.java': 'Code',
    '.cpp': 'Code',
    '.c': 'Code',
    '.html': 'Code',
    '.css': 'Code',
    '.js': 'Code',
    '.json': 'Code',
    '.sh': 'Code'
}

DEFAULT_CATEGORY = 'Others'
UNDO_FILE = 'undo_history.json'

def setup_logging(folder_path):
    """Sets up basic logging into a file named 'organizer.log' in the target folder."""
    log_file = Path(folder_path) / 'organizer.log'
    logging.basicConfig(
        filename=str(log_file),
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    # Also log to console
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)
    return log_file

def get_unique_filename(destination_folder, original_stem, extension):
    """
    Generates a unique filename if the file already exists in the destination.
    E.g., if file.txt exists, it returns file_1.txt, file_2.txt, etc.
    """
    counter = 1
    new_filename = f"{original_stem}{extension}"
    while (destination_folder / new_filename).exists():
        new_filename = f"{original_stem}_{counter}{extension}"
        counter += 1
    return new_filename

def save_undo_history(folder_path, history):
    """Saves the file movement history to a JSON file."""
    if not history:
        return
        
    history_file = Path(folder_path) / UNDO_FILE
    
    # If a history file already exists, load and append to it
    existing_history = []
    if history_file.exists():
        try:
            with open(history_file, 'r') as f:
                existing_history = json.load(f)
        except json.JSONDecodeError:
            pass
            
    existing_history.extend(history)
    
    with open(history_file, 'w') as f:
        json.dump(existing_history, f, indent=4)
        
    logging.info(f"Undo history saved to {history_file.name}")

def organize_directory(folder_path):
    """
    Scans the folder and organizes files into category subfolders based on extensions.
    """
    target_dir = Path(folder_path).resolve()
    
    if not target_dir.exists() or not target_dir.is_dir():
        print(f"Error: The path '{folder_path}' is not a valid directory.")
        return

    setup_logging(target_dir)
    logging.info(f"Starting organization of: {target_dir}")
    
    moved_files_history = []
    processed_count = 0
    
    for item in target_dir.iterdir():
        # Skip directories, hidden files, the log file, and the undo history file
        if item.is_dir():
            continue
        if item.name.startswith('.'): # Handle hidden/system files
            continue
        if item.name in ['organizer.log', UNDO_FILE, 'file_organizer.py']: # Also skip itself if in the same folder
            continue

        # Determine category based on extension
        extension = item.suffix.lower()
        category_name = EXTENSION_MAPPING.get(extension, DEFAULT_CATEGORY)
        
        # Create category folder if it doesn't exist
        category_folder = target_dir / category_name
        category_folder.mkdir(exist_ok=True)
        
        # Handle duplicate filenames
        unique_filename = get_unique_filename(category_folder, item.stem, item.suffix)
        destination_path = category_folder / unique_filename
        
        # Move the file
        try:
            shutil.move(str(item), str(destination_path))
            logging.info(f"Moved: '{item.name}' -> '{category_name}/{unique_filename}'")
            
            # Record structural changes for undo functionality
            moved_files_history.append({
                "original_path": str(item),
                "current_path": str(destination_path)
            })
            processed_count += 1
            
        except Exception as e:
            logging.error(f"Failed to move '{item.name}': {str(e)}")

    # Save tracking history
    save_undo_history(target_dir, moved_files_history)
    
    logging.info(f"Organization complete! Successfully moved {processed_count} files.")
    print(f"\nSummary:")
    print(f"- Total files moved: {processed_count}")
    print(f"- Log created at: {target_dir / 'organizer.log'}")
    print(f"- Undo history saved to: {target_dir / UNDO_FILE}")

def undo_last_action(folder_path):
    """
    Reverses the last organization operation based on the undo history file.
    """
    target_dir = Path(folder_path).resolve()
    
    if not target_dir.exists() or not target_dir.is_dir():
        print(f"Error: The path '{folder_path}' is not a valid directory.")
        return
        
    history_file = target_dir / UNDO_FILE
    
    if not history_file.exists():
        print(f"No undo history found at '{history_file}'. Cannot undo.")
        return
        
    try:
        with open(history_file, 'r') as f:
            history = json.load(f)
    except json.JSONDecodeError:
        print("Error: Undo history file is corrupted.")
        return
        
    if not history:
        print("Undo history is empty.")
        return
        
    print(f"Found {len(history)} files to restore. Reversing actions...")
    restored_count = 0
    errors = 0
    
    # We process in reverse order just in case
    for record in reversed(history):
        orig_path = Path(record['original_path'])
        curr_path = Path(record['current_path'])
        
        if curr_path.exists():
            try:
                # If there's a conflict when moving back, use a unique name
                if orig_path.exists():
                    safe_filename = get_unique_filename(orig_path.parent, orig_path.stem, orig_path.suffix)
                    orig_path = orig_path.parent / safe_filename
                    
                shutil.move(str(curr_path), str(orig_path))
                print(f"Restored: '{curr_path.name}' -> '{orig_path.parent.name}/'")
                restored_count += 1
            except Exception as e:
                print(f"Error restoring '{curr_path.name}': {e}")
                errors += 1
        else:
            print(f"Warning: File '{curr_path}' not found. Cannot restore.")
            errors += 1
            
    # Clear the history file after undo to prevent reusing stale data
    if errors == 0:
        history_file.unlink() # Delete the undo file
        print(f"\nUndo complete! Restored {restored_count} files successfully.")
    else:
        # Save remaining or problem files back to JSON... or just leave it for now.
        print(f"\nUndo partially completed: {restored_count} restored, {errors} errors or missing files.")

def main():
    parser = argparse.ArgumentParser(description="Smart File Organizer: Categorize your files automatically.")
    parser.add_argument("folder_path", type=str, nargs="?", default=".", help="The path to the folder you want to organize (defaults to current directory).")
    parser.add_argument("--undo", action="store_true", help="Undo the file organization in the specified folder.")
    
    args = parser.parse_args()
    
    if args.undo:
        undo_last_action(args.folder_path)
    else:
        organize_directory(args.folder_path)

    # If running on Windows, prevent the terminal from instantly closing when double-clicking the file
    if os.name == 'nt':
        input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()

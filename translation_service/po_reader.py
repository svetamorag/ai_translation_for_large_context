"""
PO File Reader - Extract and convert gettext .po file content to plain text
"""
import re, polib
from pathlib import Path
from typing import List, Dict, Optional


class POEntry:
    """Represents a single entry in a PO file."""
    
    def __init__(self):
        self.msgctxt: Optional[str] = None  # Message context
        self.msgid: str = ""  # Original text
        self.msgid_plural: Optional[str] = None  # Plural form
        self.msgstr: str = ""  # Translated text
        self.msgstr_plural: Dict[int, str] = {}  # Plural translations
        self.comments: List[str] = []  # Translator comments
        self.extracted_comments: List[str] = []  # Extracted comments
        self.references: List[str] = []  # Source code references
        self.flags: List[str] = []  # Flags like fuzzy, python-format
        self.previous_msgid: Optional[str] = None  # Previous msgid (for fuzzy)
        self.obsolete: bool = False  # Obsolete entry
    
    def is_translated(self) -> bool:
        """Check if entry has a translation."""
        if self.msgstr_plural:
            return any(text.strip() for text in self.msgstr_plural.values())
        return bool(self.msgstr.strip())
    
    def is_fuzzy(self) -> bool:
        """Check if entry is marked as fuzzy."""
        return 'fuzzy' in self.flags


def read_po_to_text(po_path, include_untranslated=True, include_fuzzy=True, 
                    include_obsolete=False, include_metadata=True,
                    include_comments=False):
    """
    Read a .po file and return all text content as a plain string.
    
    Args:
        po_path (str): Path to the .po file
        include_untranslated (bool): Include untranslated entries
        include_fuzzy (bool): Include fuzzy entries
        include_obsolete (bool): Include obsolete entries
        include_metadata (bool): Include PO file metadata/headers
        include_comments (bool): Include comments and references
        
    Returns:
        str: Plain text string containing all the PO file content
        
    Raises:
        FileNotFoundError: If the .po file doesn't exist
    """
    po_path = Path(po_path)
    
    if not po_path.exists():
        raise FileNotFoundError(f"PO file not found: {po_path}")
    
    # Read and parse the PO file
    with open(po_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    entries = _parse_po_file(content)
    
    # Separate metadata from regular entries
    metadata = None
    regular_entries = []
    
    for entry in entries:
        if entry.msgid == "" and not entry.obsolete:
            metadata = entry
        else:
            regular_entries.append(entry)
    
    # Build plain text output
    text_parts = []
    
    # Add metadata section
    if include_metadata and metadata:
        text_parts.append("=" * 80)
        text_parts.append("METADATA")
        text_parts.append("=" * 80)
        
        if metadata.msgstr:
            lines = metadata.msgstr.split('\\n')
            for line in lines:
                if line.strip():
                    text_parts.append(line)
        
        text_parts.append("")
    
    # Calculate statistics
    total = len(regular_entries)
    translated = sum(1 for e in regular_entries if e.is_translated() and not e.is_fuzzy())
    fuzzy = sum(1 for e in regular_entries if e.is_fuzzy())
    untranslated = sum(1 for e in regular_entries if not e.is_translated())
    obsolete_count = sum(1 for e in regular_entries if e.obsolete)
    
    # Add statistics
    text_parts.append("=" * 80)
    text_parts.append("STATISTICS")
    text_parts.append("=" * 80)
    text_parts.append(f"Total Entries: {total}")
    text_parts.append(f"Translated: {translated}")
    text_parts.append(f"Fuzzy: {fuzzy}")
    text_parts.append(f"Untranslated: {untranslated}")
    if obsolete_count > 0:
        text_parts.append(f"Obsolete: {obsolete_count}")
    
    if total > 0:
        completion = (translated / total) * 100
        text_parts.append(f"Completion: {completion:.1f}%")
    
    text_parts.append("")
    text_parts.append("=" * 80)
    text_parts.append("ENTRIES")
    text_parts.append("=" * 80)
    text_parts.append("")
    
    # Add entries
    for i, entry in enumerate(regular_entries, 1):
        # Skip based on filters
        if entry.obsolete and not include_obsolete:
            continue
        if entry.is_fuzzy() and not include_fuzzy:
            continue
        if not entry.is_translated() and not include_untranslated:
            continue
        
        # Entry separator
        text_parts.append("-" * 80)
        
        # Status indicator
        if entry.obsolete:
            text_parts.append(f"[Entry {i}] [OBSOLETE]")
        elif entry.is_fuzzy():
            text_parts.append(f"[Entry {i}] [FUZZY]")
        elif entry.is_translated():
            text_parts.append(f"[Entry {i}] [TRANSLATED]")
        else:
            text_parts.append(f"[Entry {i}] [UNTRANSLATED]")
        
        text_parts.append("")
        
        # Add flags
        if entry.flags and include_comments:
            text_parts.append(f"Flags: {', '.join(entry.flags)}")
            text_parts.append("")
        
        # Add context
        if entry.msgctxt:
            text_parts.append(f"Context: {entry.msgctxt}")
            text_parts.append("")
        
        # Add comments
        if include_comments:
            if entry.comments:
                for comment in entry.comments:
                    text_parts.append(f"# {comment}")
            
            if entry.extracted_comments:
                for comment in entry.extracted_comments:
                    text_parts.append(f"#. {comment}")
            
            if entry.references:
                for ref in entry.references:
                    text_parts.append(f"#: {ref}")
            
            if entry.comments or entry.extracted_comments or entry.references:
                text_parts.append("")
        
        # Add msgid
        text_parts.append("Original:")
        text_parts.append(entry.msgid)
        text_parts.append("")
        
        # Add msgid_plural if exists
        if entry.msgid_plural:
            text_parts.append("Plural:")
            text_parts.append(entry.msgid_plural)
            text_parts.append("")
        
        # Add msgstr
        text_parts.append("Translation:")
        if entry.msgstr_plural:
            for idx, text in sorted(entry.msgstr_plural.items()):
                display_text = text if text.strip() else "(not translated)"
                text_parts.append(f"  [Plural form {idx}]: {display_text}")
        else:
            display_text = entry.msgstr if entry.msgstr.strip() else "(not translated)"
            text_parts.append(display_text)
        
        text_parts.append("")
        
        # Add previous msgid for fuzzy entries
        if entry.previous_msgid and include_comments:
            text_parts.append(f"Previous msgid: {entry.previous_msgid}")
            text_parts.append("")
    
    return '\n'.join(text_parts)


def assemble_po_from_text(text_path: str, original_po_path: str, output_po_path: str):
    """
    Reassembles a .po file from a plain text file containing translations.

    This function reads the original .po file to preserve its structure,
    comments, and flags. It then parses the provided text file, extracts the
    translations, and updates the corresponding entries in the .po file object.
    Finally, it saves the result to a new .po file.

    Args:
        text_path (str): Path to the plain text file with translations.
        original_po_path (str): Path to the original .po file.
        output_po_path (str): Path where the new .po file will be saved.

    Raises:
        FileNotFoundError: If the text file or original .po file doesn't exist.
        ValueError: If the text file format is invalid.
    """
    if not Path(text_path).exists():
        raise FileNotFoundError(f"Text file not found: {text_path}")
    if not Path(original_po_path).exists():
        raise FileNotFoundError(f"Original PO file not found: {original_po_path}")

    # 1. Parse the original .po file using polib to preserve all metadata
    po = polib.pofile(original_po_path, encoding='utf-8', wrapwidth=0)
    
    # Create a lookup dictionary for easy access to entries
    # Key: (msgctxt, msgid)
    entry_map: Dict[(Optional[str], str), polib.POEntry] = {
        (entry.msgctxt, entry.msgid): entry for entry in po
    }

    # 2. Parse the translated text file
    with open(text_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split content into individual entry blocks
    entry_blocks = content.split("-" * 80)[1:] # Skip header/stats

    for block in entry_blocks:
        if not block.strip():
            continue

        lines = block.strip().split('\n')
        
        msgctxt: Optional[str] = None
        msgid = ""
        msgid_plural: Optional[str] = None
        msgstr = ""
        msgstr_plural: Dict[int, str] = {}

        current_section = None
        for line in lines:
            line_strip = line.strip()
            if not line_strip:
                continue

            if line_strip.startswith('[Entry'):
                current_section = None
                continue
            if line_strip.startswith('Context:'):
                msgctxt = line_strip.replace('Context:', '').strip()
                current_section = None
                continue
            if line_strip == 'Original:':
                current_section = 'msgid'
                continue
            if line_strip == 'Plural:':
                current_section = 'msgid_plural'
                msgid_plural = ""
                continue
            if line_strip == 'Translation:':
                current_section = 'msgstr'
                continue

            if current_section == 'msgid':
                msgid += line + '\n'
            elif current_section == 'msgid_plural':
                msgid_plural += line + '\n'
            elif current_section == 'msgstr':
                plural_match = re.match(r'\s*\[Plural form (\d+)\]:\s*(.*)', line)
                if plural_match:
                    idx = int(plural_match.group(1))
                    translation = plural_match.group(2)
                    msgstr_plural[idx] = translation if translation != '(not translated)' else ''
                else:
                    msgstr += line + '\n'

        # Clean up collected strings
        msgid = msgid.strip()
        if msgid_plural:
            msgid_plural = msgid_plural.strip()
        msgstr = msgstr.strip()
        if msgstr == '(not translated)':
            msgstr = ''

        # 3. Find and update the corresponding entry in the polib object
        entry = entry_map.get((msgctxt, msgid))
        if entry:
            if entry.msgid_plural is not None and msgstr_plural:
                entry.msgstr_plural = msgstr_plural
            else:
                entry.msgstr = msgstr

    # 4. Save the updated .po file
    po.save(output_po_path)

def _parse_po_file(content: str) -> List[POEntry]:
    """
    Parse PO file content into a list of POEntry objects.
    
    Args:
        content (str): Content of the PO file
        
    Returns:
        List[POEntry]: List of parsed entries
    """
    entries = []
    current_entry = POEntry()
    current_field = None
    
    lines = content.split('\n')
    
    for line in lines:
        # Skip empty lines at the start of an entry
        if not line.strip() and current_field is None:
            continue
        
        # Empty line marks end of entry
        if not line.strip():
            if current_entry.msgid is not None:
                entries.append(current_entry)
                current_entry = POEntry()
                current_field = None
            continue
        
        # Translator comments
        if line.startswith('# ') and not line.startswith('#.') and not line.startswith('#:') and not line.startswith('#,') and not line.startswith('#|'):
            current_entry.comments.append(line[2:].strip())
            continue
        
        # Extracted comments
        if line.startswith('#.'):
            current_entry.extracted_comments.append(line[2:].strip())
            continue
        
        # References
        if line.startswith('#:'):
            current_entry.references.append(line[2:].strip())
            continue
        
        # Flags
        if line.startswith('#,'):
            flags = line[2:].strip().split(',')
            current_entry.flags.extend(flag.strip() for flag in flags)
            continue
        
        # Previous msgid (for fuzzy entries)
        if line.startswith('#|'):
            prev_match = re.match(r'#\|\s+msgid\s+"(.*)"', line)
            if prev_match:
                current_entry.previous_msgid = _unescape_string(prev_match.group(1))
            continue
        
        # Obsolete entries
        if line.startswith('#~'):
            current_entry.obsolete = True
            line = line[2:].strip()
        
        # msgctxt
        if line.startswith('msgctxt'):
            match = re.match(r'msgctxt\s+"(.*)"', line)
            if match:
                current_entry.msgctxt = _unescape_string(match.group(1))
                current_field = 'msgctxt'
            continue
        
        # msgid
        if line.startswith('msgid '):
            match = re.match(r'msgid\s+"(.*)"', line)
            if match:
                current_entry.msgid = _unescape_string(match.group(1))
                current_field = 'msgid'
            continue
        
        # msgid_plural
        if line.startswith('msgid_plural'):
            match = re.match(r'msgid_plural\s+"(.*)"', line)
            if match:
                current_entry.msgid_plural = _unescape_string(match.group(1))
                current_field = 'msgid_plural'
            continue
        
        # msgstr (singular)
        if line.startswith('msgstr '):
            match = re.match(r'msgstr\s+"(.*)"', line)
            if match:
                current_entry.msgstr = _unescape_string(match.group(1))
                current_field = 'msgstr'
            continue
        
        # msgstr[n] (plural)
        if line.startswith('msgstr['):
            match = re.match(r'msgstr\[(\d+)\]\s+"(.*)"', line)
            if match:
                idx = int(match.group(1))
                current_entry.msgstr_plural[idx] = _unescape_string(match.group(2))
                current_field = f'msgstr[{idx}]'
            continue
        
        # Continuation line (quoted string)
        if line.startswith('"') and current_field:
            match = re.match(r'"(.*)"', line)
            if match:
                continuation = _unescape_string(match.group(1))
                
                if current_field == 'msgctxt':
                    current_entry.msgctxt += continuation
                elif current_field == 'msgid':
                    current_entry.msgid += continuation
                elif current_field == 'msgid_plural':
                    current_entry.msgid_plural += continuation
                elif current_field == 'msgstr':
                    current_entry.msgstr += continuation
                elif current_field.startswith('msgstr['):
                    idx = int(current_field[7:-1])
                    current_entry.msgstr_plural[idx] += continuation
    
    # Don't forget the last entry
    if current_entry.msgid is not None:
        entries.append(current_entry)
    
    return entries


def _unescape_string(s: str) -> str:
    """
    Unescape a string from PO file format.
    
    Args:
        s (str): Escaped string
        
    Returns:
        str: Unescaped string
    """
    # Replace escape sequences
    s = s.replace('\\n', '\n')
    s = s.replace('\\t', '\t')
    s = s.replace('\\r', '\r')
    s = s.replace('\\"', '"')
    s = s.replace('\\\\', '\\')
    
    return s


# Example usage
if __name__ == '__main__':
   # In po_reader.py, inside if __name__ == '__main__':

    # Example for re-assembly
    try:
        assemble_po_from_text(
            'output.txt', 
            'en_GB.po', 
            'en_GB_reassembled.po'
        )
        print("✓ Successfully reassembled PO file.")
    except Exception as e:
        print(f"✗ Error during reassembly: {e}")

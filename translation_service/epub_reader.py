"""
EPUB Reader - Extracts content from EPUB files.

This module properly extracts EPUB content and converts it to plain text.
"""
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
import re
import html


class EPUBHandler:
    """Handle EPUB reading operations."""
    
    def __init__(self, epub_path: str):
        self.epub_path = Path(epub_path)
        self.metadata = {}
        self.content_files = []
        self.spine_order = []
        self.manifest = {}
        
    def read_epub_to_text(self) -> str:
        """
        Read EPUB file and return content as a single plain text string.
        
        Returns:
            str: Plain text content of the EPUB.
        """
        if not self.epub_path.exists():
            raise FileNotFoundError(f"EPUB file not found: {self.epub_path}")
        
        with zipfile.ZipFile(self.epub_path, 'r') as epub_zip:
            # Get the OPF file path
            content_opf_path = self._find_opf_path(epub_zip)
            content_dir = str(Path(content_opf_path).parent) if content_opf_path else ''
            
            # Parse OPF for metadata and structure
            opf_content = epub_zip.read(content_opf_path).decode('utf-8')
            self._parse_opf(opf_content, content_dir)
            
            # Extract content files in reading order
            text_parts = []
            
            for content_file in self.content_files:
                try:
                    raw_content = epub_zip.read(content_file).decode('utf-8', errors='replace')
                    # Extract plain text from the XHTML content
                    text_content = self._extract_text_from_xhtml(raw_content)
                    if text_content:
                        text_parts.append(text_content)
                except Exception as e:
                    print(f"Warning: Could not process {content_file}: {e}")
            
            return '\n\n'.join(text_parts)
    
    def _find_opf_path(self, epub_zip: zipfile.ZipFile) -> str:
        """Find the content.opf file path from container.xml"""
        try:
            container_content = epub_zip.read('META-INF/container.xml')
            container_tree = ET.fromstring(container_content)
            ns = {'ns': 'urn:oasis:names:tc:opendocument:xmlns:container'}
            rootfile = container_tree.find('.//ns:rootfile', ns)
            
            if rootfile is not None:
                return rootfile.get('full-path')
        except:
            pass
        
        # Fallback to common locations
        for path in ['OEBPS/content.opf', 'content.opf', 'EPUB/content.opf']:
            if path in epub_zip.namelist():
                return path
        
        raise ValueError("Could not find content.opf in EPUB")
    
    def _parse_opf(self, opf_content: str, content_dir: str):
        """Parse OPF file to get manifest and spine"""
        opf_tree = ET.fromstring(opf_content)
        
        ns = {
            'opf': 'http://www.idpf.org/2007/opf',
            'dc': 'http://purl.org/dc/elements/1.1/'
        }
        
        # Extract metadata
        metadata = opf_tree.find('.//opf:metadata', ns)
        if metadata is not None:
            title = metadata.find('.//dc:title', ns)
            self.metadata['title'] = title.text if title is not None else 'Unknown'
            
            creator = metadata.find('.//dc:creator', ns)
            self.metadata['author'] = creator.text if creator is not None else 'Unknown'
        
        # Build manifest
        manifest = opf_tree.find('.//opf:manifest', ns)
        if manifest is not None:
            for item in manifest.findall('opf:item', ns):
                item_id = item.get('id')
                href = item.get('href')
                media_type = item.get('media-type', '')
                if item_id and href:
                    self.manifest[item_id] = {
                        'href': href,
                        'media_type': media_type
                    }
        
        # Get spine order
        spine = opf_tree.find('.//opf:spine', ns)
        if spine is not None:
            for itemref in spine.findall('opf:itemref', ns):
                idref = itemref.get('idref')
                if idref in self.manifest:
                    href = self.manifest[idref]['href']
                    full_path = f"{content_dir}/{href}" if content_dir and content_dir != '.' else href
                    self.content_files.append(full_path)
    
    def _extract_text_from_xhtml(self, xhtml_content: str) -> str:
        """Extract plain text from an XHTML content string."""
        try:
            # Clean up XML declaration for robust parsing
            content = re.sub(r'<\?xml[^>]*\?>', '', xhtml_content, count=1)
            tree = ET.fromstring(content)

            # Find the body tag, considering namespaces
            body = tree.find('.//{http://www.w3.org/1999/xhtml}body')
            if body is None:
                body = tree.find('.//body')

            if body is not None:
                # Join all text nodes within the body
                plain_text = ' '.join(body.itertext()).strip()
                return html.unescape(plain_text)

        except ET.ParseError:
            # Fallback for malformed XML: regex to strip tags
            body_match = re.search(r'<body[^>]*>(.*?)</body>', xhtml_content, re.DOTALL | re.IGNORECASE)
            content_to_clean = body_match.group(1) if body_match else xhtml_content
            text = re.sub(r'<[^>]+>', ' ', content_to_clean)
            clean_text = ' '.join(text.split()).strip()
            return html.unescape(clean_text)

        return "" # Return empty string if nothing is found


# Convenience functions for backward compatibility
def read_epub_to_text(epub_path: str) -> str:
    """Read EPUB and return as plain text string"""
    handler = EPUBHandler(epub_path)
    return handler.read_epub_to_text()


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Read EPUB:  python epub_reader.py read <input.epub> [output.txt]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == 'read':
        epub_file = sys.argv[2]
        output_file = sys.argv[3] if len(sys.argv) > 3 else Path(epub_file).stem + '_output.txt'
        
        try:
            text_content = read_epub_to_text(epub_file)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(text_content)
            
            print(f"✓ Successfully converted EPUB to plain text")
            print(f"✓ Output: {output_file}")
            print(f"✓ Length: {len(text_content):,} characters")
            
        except Exception as e:
            print(f"✗ Error: {e}", file=sys.stderr)
            sys.exit(1)
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
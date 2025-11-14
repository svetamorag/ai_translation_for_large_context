"""
EPUB Reader and Writer - Preserve HTML structure and convert between formats

This module properly extracts EPUB content preserving all HTML tags and structure,
and can reassemble HTML back into valid EPUB format.
"""
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from typing import Dict, List, Tuple
import re
from datetime import datetime
import uuid


class EPUBHandler:
    """Handle EPUB reading and writing operations with HTML preservation"""
    
    def __init__(self, epub_path: str):
        self.epub_path = Path(epub_path)
        self.metadata = {}
        self.content_files = []
        self.spine_order = []
        self.manifest = {}
        
    def read_epub_to_html(self) -> str:
        """
        Read EPUB file and return content as properly formatted HTML string.
        Preserves all HTML tags, attributes, and structure.
        
        Returns:
            str: Complete HTML document with all content
        """
        if not self.epub_path.exists():
            raise FileNotFoundError(f"EPUB file not found: {self.epub_path}")
        
        with zipfile.ZipFile(self.epub_path, 'r') as epub_zip:
            # Get the OPF file path
            content_opf_path = self._find_opf_path(epub_zip)
            content_dir = str(Path(content_opf_path).parent)
            
            # Parse OPF for metadata and structure
            opf_content = epub_zip.read(content_opf_path).decode('utf-8')
            self._parse_opf(opf_content, content_dir)
            
            # Extract content files in reading order
            html_parts = self._build_html_header()
            
            for content_file in self.content_files:
                try:
                    raw_content = epub_zip.read(content_file).decode('utf-8', errors='replace')
                    # Extract body content while preserving HTML
                    body_content = self._extract_html_body(raw_content)
                    if body_content:
                        html_parts.append(f'\n<!-- Source: {Path(content_file).name} -->\n')
                        html_parts.append(body_content)
                except Exception as e:
                    html_parts.append(f'\n<!-- Error reading {content_file}: {e} -->\n')
            
            html_parts.append('\n</body>\n</html>')
            
            return ''.join(html_parts)
    
    def write_html_to_epub(self, html_content: str, output_path: str):
        """
        Convert HTML content back to EPUB format.
        
        Args:
            html_content: HTML string to convert
            output_path: Path for output EPUB file
        """
        output_path = Path(output_path)
        
        # Split HTML into logical chapters (you can customize the splitting logic)
        chapters = self._split_html_to_chapters(html_content)
        
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as epub_zip:
            # Write mimetype (must be first, uncompressed)
            epub_zip.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
            
            # Write container.xml
            container_xml = self._create_container_xml()
            epub_zip.writestr('META-INF/container.xml', container_xml)
            
            # Write content files
            for idx, chapter_html in enumerate(chapters, 1):
                chapter_file = f'OEBPS/chapter{idx}.xhtml'
                xhtml_content = self._wrap_as_xhtml(chapter_html, f'Chapter {idx}')
                epub_zip.writestr(chapter_file, xhtml_content)
            
            # Write content.opf
            content_opf = self._create_content_opf(len(chapters))
            epub_zip.writestr('OEBPS/content.opf', content_opf)
            
            # Write toc.ncx
            toc_ncx = self._create_toc_ncx(len(chapters))
            epub_zip.writestr('OEBPS/toc.ncx', toc_ncx)
    
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
    
    def _extract_html_body(self, xhtml_content: str) -> str:
        """
        Extract body content from XHTML while preserving all HTML tags.
        """
        # Remove XML declaration
        xhtml_content = re.sub(r'<\?xml[^>]+\?>', '', xhtml_content)
        
        try:
            # Try to parse as XML
            # Register common namespaces
            namespaces = {
                'xhtml': 'http://www.w3.org/1999/xhtml',
                'epub': 'http://www.idpf.org/2007/ops'
            }
            
            for prefix, uri in namespaces.items():
                ET.register_namespace(prefix, uri)
            
            tree = ET.fromstring(xhtml_content)
            
            # Find body element (with or without namespace)
            body = tree.find('.//{http://www.w3.org/1999/xhtml}body')
            if body is None:
                body = tree.find('.//body')
            
            if body is not None:
                # Convert element tree to string preserving all tags
                return self._element_to_html_string(body, skip_body_tag=True)
            
        except ET.ParseError:
            pass
        
        # Fallback: extract body using regex
        body_match = re.search(r'<body[^>]*>(.*?)</body>', xhtml_content, re.DOTALL | re.IGNORECASE)
        if body_match:
            return body_match.group(1)
        
        # Last resort: return cleaned content
        return xhtml_content
    
    def _element_to_html_string(self, element, skip_body_tag=False) -> str:
        """
        Convert ElementTree element to HTML string preserving all tags and attributes.
        """
        # Get tag without namespace
        tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
        
        parts = []
        
        # Opening tag with attributes
        if not skip_body_tag:
            attrs = ' '.join([f'{k}="{v}"' for k, v in element.attrib.items()])
            opening = f'<{tag} {attrs}>' if attrs else f'<{tag}>'
            parts.append(opening)
        
        # Text content
        if element.text:
            parts.append(element.text)
        
        # Process children recursively
        for child in element:
            parts.append(self._element_to_html_string(child))
            if child.tail:
                parts.append(child.tail)
        
        # Closing tag
        if not skip_body_tag:
            parts.append(f'</{tag}>')
        
        return ''.join(parts)
    
    def _build_html_header(self) -> List[str]:
        """Build HTML document header with metadata"""
        title = self.metadata.get('title', 'Untitled')
        author = self.metadata.get('author', 'Unknown Author')
        
        return [
            '<!DOCTYPE html>\n',
            '<html lang="en">\n',
            '<head>\n',
            '  <meta charset="UTF-8">\n',
            '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n',
            f'  <title>{title}</title>\n',
            f'  <meta name="author" content="{author}">\n',
            '</head>\n',
            '<body>\n'
        ]
    
    def _split_html_to_chapters(self, html_content: str) -> List[str]:
        """
        Split HTML content into chapters for EPUB creation.
        Uses heading tags or splits by length if no structure found.
        """
        # Extract body content
        body_match = re.search(r'<body[^>]*>(.*?)</body>', html_content, re.DOTALL | re.IGNORECASE)
        if body_match:
            content = body_match.group(1)
        else:
            content = html_content
        
        # Try to split by h1 or h2 tags
        chapter_pattern = r'(<h[12][^>]*>.*?</h[12]>)'
        splits = re.split(chapter_pattern, content, flags=re.IGNORECASE | re.DOTALL)
        
        if len(splits) > 2:  # Found chapter markers
            chapters = []
            for i in range(1, len(splits), 2):
                if i + 1 < len(splits):
                    chapters.append(splits[i] + splits[i + 1])
                else:
                    chapters.append(splits[i])
            return chapters if chapters else [content]
        
        # No clear structure - split by approximate size
        max_chars = 50000  # ~50KB per chapter
        if len(content) <= max_chars:
            return [content]
        
        chapters = []
        current_pos = 0
        while current_pos < len(content):
            end_pos = min(current_pos + max_chars, len(content))
            # Try to break at paragraph
            if end_pos < len(content):
                break_point = content.rfind('</p>', current_pos, end_pos)
                if break_point > current_pos:
                    end_pos = break_point + 4
            
            chapters.append(content[current_pos:end_pos])
            current_pos = end_pos
        
        return chapters
    
    def _wrap_as_xhtml(self, html_content: str, title: str) -> str:
        """Wrap HTML content as valid XHTML for EPUB"""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>{title}</title>
  <meta charset="UTF-8"/>
</head>
<body>
{html_content}
</body>
</html>'''
    
    def _create_container_xml(self) -> str:
        """Create META-INF/container.xml"""
        return '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>'''
    
    def _create_content_opf(self, num_chapters: int) -> str:
        """Create OEBPS/content.opf"""
        book_id = str(uuid.uuid4())
        title = self.metadata.get('title', 'Converted Book')
        author = self.metadata.get('author', 'Unknown')
        date = datetime.now().strftime('%Y-%m-%d')
        
        manifest_items = '\n'.join([
            f'    <item id="chapter{i}" href="chapter{i}.xhtml" media-type="application/xhtml+xml"/>'
            for i in range(1, num_chapters + 1)
        ])
        
        spine_items = '\n'.join([
            f'    <itemref idref="chapter{i}"/>'
            for i in range(1, num_chapters + 1)
        ])
        
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>{title}</dc:title>
    <dc:creator>{author}</dc:creator>
    <dc:language>en</dc:language>
    <dc:identifier id="bookid">{book_id}</dc:identifier>
    <dc:date>{date}</dc:date>
  </metadata>
  <manifest>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
{manifest_items}
  </manifest>
  <spine toc="ncx">
{spine_items}
  </spine>
</package>'''
    
    def _create_toc_ncx(self, num_chapters: int) -> str:
        """Create OEBPS/toc.ncx"""
        title = self.metadata.get('title', 'Converted Book')
        book_id = str(uuid.uuid4())
        
        nav_points = '\n'.join([
            f'''    <navPoint id="chapter{i}" playOrder="{i}">
      <navLabel><text>Chapter {i}</text></navLabel>
      <content src="chapter{i}.xhtml"/>
    </navPoint>'''
            for i in range(1, num_chapters + 1)
        ])
        
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="{book_id}"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle>
    <text>{title}</text>
  </docTitle>
  <navMap>
{nav_points}
  </navMap>
</ncx>'''


# Convenience functions for backward compatibility
def read_epub_to_html(epub_path: str) -> str:
    """Read EPUB and return as HTML string"""
    handler = EPUBHandler(epub_path)
    return handler.read_epub_to_html()


def write_html_to_epub(html_content: str, output_path: str, 
                        title: str = 'Converted Book', author: str = 'Unknown'):
    """Write HTML content to EPUB file"""
    handler = EPUBHandler('')  # No input file needed
    handler.metadata = {'title': title, 'author': author}
    handler.write_html_to_epub(html_content, output_path)


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Read EPUB:  python epub_handler.py read <input.epub> [output.html]")
        print("  Write EPUB: python epub_handler.py write <input.html> <output.epub>")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == 'read':
        epub_file = sys.argv[2]
        output_file = sys.argv[3] if len(sys.argv) > 3 else Path(epub_file).stem + '_output.html'
        
        try:
            html_content = read_epub_to_html(epub_file)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"✓ Successfully converted EPUB to HTML")
            print(f"✓ Output: {output_file}")
            print(f"✓ Length: {len(html_content):,} characters")
            
        except Exception as e:
            print(f"✗ Error: {e}", file=sys.stderr)
            sys.exit(1)
    
    elif command == 'write':
        html_file = sys.argv[2]
        epub_file = sys.argv[3]
        
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            write_html_to_epub(html_content, epub_file)
            
            print(f"✓ Successfully converted HTML to EPUB")
            print(f"✓ Output: {epub_file}")
            
        except Exception as e:
            print(f"✗ Error: {e}", file=sys.stderr)
            sys.exit(1)
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
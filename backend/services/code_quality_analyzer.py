import logging
import ast
import re
from typing import List, Dict, Any
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger(__name__)


class CodeQualityAnalyzer:
    """Analyzes code quality issues and code smells."""
    
    def __init__(self):
        self.long_function_threshold = 50
        self.large_class_threshold = 500
        self.complexity_threshold = 10
        self.max_nesting = 4
    
    def analyze(
        self,
        repository_path: str,
        code_elements: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Analyze code quality issues."""
        debt_items = []
        
        # Group elements by file
        files_elements = defaultdict(list)
        for element in code_elements:
            file_path = element.get("file_path", "")
            files_elements[file_path].append(element)
        
        # Analyze each file
        for file_path, elements in files_elements.items():
            try:
                file_items = self._analyze_file(file_path, elements)
                debt_items.extend(file_items)
            except Exception as e:
                logger.error(f"Error analyzing file {file_path}: {e}")
        
        # Detect code duplication
        try:
            duplication_items = self._detect_duplication(code_elements)
            debt_items.extend(duplication_items)
        except Exception as e:
            logger.error(f"Error detecting duplication: {e}")
        
        return debt_items
    
    def _analyze_file(
        self,
        file_path: str,
        elements: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Analyze a single file for quality issues."""
        items = []
        
        # Read file content
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.split("\n")
        except Exception:
            return items
        
        # Analyze each code element
        for element in elements:
            element_type = element.get("type", "")
            name = element.get("name", "")
            line_start = element.get("line_start", 0)
            line_end = element.get("line_end", line_start)
            
            # Long function/method
            if element_type in ["function", "method"]:
                length = line_end - line_start + 1
                if length > self.long_function_threshold:
                    items.append({
                        "id": f"long_func_{file_path}_{line_start}",
                        "category": "code_quality",
                        "severity": "medium" if length < 100 else "high",
                        "title": f"Long {element_type}: {name}",
                        "description": f"{element_type.capitalize()} '{name}' is {length} lines long (threshold: {self.long_function_threshold})",
                        "file_path": file_path,
                        "line_start": line_start,
                        "line_end": line_end,
                        "code_snippet": "\n".join(lines[line_start-1:min(line_start+10, len(lines))]),
                        "impact_score": min(length / 200, 1.0),
                        "effort_estimate": "hours",
                    })
            
            # Large class
            elif element_type == "class":
                length = line_end - line_start + 1
                if length > self.large_class_threshold:
                    items.append({
                        "id": f"large_class_{file_path}_{line_start}",
                        "category": "code_quality",
                        "severity": "high",
                        "title": f"Large class: {name}",
                        "description": f"Class '{name}' is {length} lines long (threshold: {self.large_class_threshold})",
                        "file_path": file_path,
                        "line_start": line_start,
                        "line_end": line_end,
                        "impact_score": min(length / 1000, 1.0),
                        "effort_estimate": "days",
                    })
        
        # Detect deep nesting
        nesting_items = self._detect_deep_nesting(file_path, content)
        items.extend(nesting_items)
        
        # Detect magic numbers/strings
        magic_items = self._detect_magic_values(file_path, content)
        items.extend(magic_items)
        
        # Detect commented-out code
        commented_items = self._detect_commented_code(file_path, content)
        items.extend(commented_items)
        
        return items
    
    def _detect_duplication(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect code duplication using simple AST comparison."""
        items = []
        
        # Group functions by approximate size
        functions = [
            e for e in elements
            if e.get("type") in ["function", "method"]
        ]
        
        # Simple duplication detection: same name and similar line count
        seen = {}
        for func in functions:
            name = func.get("name", "")
            length = func.get("line_end", 0) - func.get("line_start", 0) + 1
            key = f"{name}_{length}"
            
            if key in seen:
                # Potential duplication
                items.append({
                    "id": f"dup_{func.get('file_path')}_{func.get('line_start')}",
                    "category": "code_quality",
                    "severity": "medium",
                    "title": f"Potential code duplication: {name}",
                    "description": f"Function '{name}' appears to be duplicated or similar to another function",
                    "file_path": func.get("file_path", ""),
                    "line_start": func.get("line_start", 0),
                    "line_end": func.get("line_end", 0),
                    "impact_score": 0.6,
                    "effort_estimate": "hours",
                })
            else:
                seen[key] = func
        
        return items
    
    def _detect_deep_nesting(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Detect deep nesting levels."""
        items = []
        lines = content.split("\n")
        
        max_nesting = 0
        current_nesting = 0
        problem_line = 0
        
        for i, line in enumerate(lines, 1):
            # Count opening braces/brackets
            opening = line.count("{") + line.count("[") + line.count("(")
            closing = line.count("}") + line.count("]") + line.count(")")
            
            current_nesting += opening - closing
            
            if current_nesting > max_nesting:
                max_nesting = current_nesting
                problem_line = i
            
            if max_nesting > self.max_nesting:
                items.append({
                    "id": f"deep_nest_{file_path}_{problem_line}",
                    "category": "code_quality",
                    "severity": "medium",
                    "title": f"Deep nesting detected",
                    "description": f"Nesting level of {max_nesting} exceeds threshold of {self.max_nesting}",
                    "file_path": file_path,
                    "line_start": problem_line,
                    "line_end": problem_line,
                    "impact_score": min(max_nesting / 10, 1.0),
                    "effort_estimate": "hours",
                })
                break
        
        return items
    
    def _detect_magic_values(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Detect magic numbers and strings."""
        items = []
        lines = content.split("\n")
        
        # Pattern for magic numbers (not constants)
        magic_number_pattern = r'\b(?:[0-9]{2,}|[0-9]+\.[0-9]+)\b'
        
        for i, line in enumerate(lines, 1):
            # Skip comments and strings
            if line.strip().startswith("#") or line.strip().startswith("//"):
                continue
            
            # Check for magic numbers
            matches = re.findall(magic_number_pattern, line)
            if matches and not any(keyword in line.lower() for keyword in ["const", "final", "static", "="]):
                items.append({
                    "id": f"magic_{file_path}_{i}",
                    "category": "code_quality",
                    "severity": "low",
                    "title": "Magic number detected",
                    "description": f"Line contains magic number(s): {', '.join(matches[:3])}",
                    "file_path": file_path,
                    "line_start": i,
                    "line_end": i,
                    "code_snippet": line,
                    "impact_score": 0.3,
                    "effort_estimate": "hours",
                })
                break  # One per file to avoid spam
        
        return items
    
    def _detect_commented_code(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Detect commented-out code blocks."""
        items = []
        lines = content.split("\n")
        
        commented_blocks = []
        in_block = False
        block_start = 0
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Detect commented code (lines that look like code but are commented)
            if stripped.startswith("#") or stripped.startswith("//"):
                code_like = any(keyword in stripped for keyword in [
                    "def ", "class ", "if ", "for ", "while ", "return ", "=", "(", ")"
                ])
                if code_like and not in_block:
                    in_block = True
                    block_start = i
                elif code_like and in_block:
                    commented_blocks.append((block_start, i))
            else:
                if in_block:
                    in_block = False
        
        if commented_blocks:
            items.append({
                "id": f"commented_code_{file_path}",
                "category": "code_quality",
                "severity": "low",
                "title": "Commented-out code detected",
                "description": f"Found {len(commented_blocks)} block(s) of commented-out code",
                "file_path": file_path,
                "line_start": commented_blocks[0][0],
                "line_end": commented_blocks[-1][1],
                "impact_score": 0.2,
                "effort_estimate": "hours",
            })
        
        return items

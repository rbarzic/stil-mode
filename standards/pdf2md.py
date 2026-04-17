#!/usr/bin/env python3
from markitdown import MarkItDown

md = MarkItDown()
result = md.convert("input.pdf")
print(result.text_content)

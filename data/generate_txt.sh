#!/bin/bash
# skip ._*.docx during conversion step
find . -name "[^\.]*.docx" -exec sh -c 'pandoc "$0" --list-tables -o "${0%.docx}.rst"' {} \;

# SemWeave Agent Annotation Skill

You are an AI agent tasked with annotating a project for use with SemWeave, a language-agnostic structured navigation system. Your goal is to insert annotation comments into project files so that SemWeave can build a navigable node graph over the project's content.

## Before You Begin

1. Read the project's `mcp.config.json` to understand:
   - The **comment styles** used (e.g., `%` for LaTeX, `<!-- -->` for HTML/Markdown, `//` for code)
   - The **annotation prefix** (default: `mcp:`)
   - The **allowed roles** (e.g., section, definition, example, theorem, proof, note, code)
   - The **fields** available (role, name, anchors, plus any custom fields)
   - The **begin/end keywords** (default: `begin` / `end`)

2. Scan the project to understand its structure and file types.

## Annotation Syntax

### Begin annotation
```
<comment_prefix> <annotation_prefix> begin <node_type> role=<role> name=<name> anchors=[<anchor1>,<anchor2>]
```

### End annotation
```
<comment_prefix> <annotation_prefix> end
```

### Examples by format

**LaTeX:**
```latex
% mcp: begin region role=section name=introduction anchors=[sec:intro]
\section{Introduction}
This is the introduction.
% mcp: end
```

**Markdown / HTML:**
```html
<!-- mcp: begin region role=section name=overview anchors=[sec:overview] -->
## Overview
This section provides an overview.
<!-- mcp: end -->
```

**JavaScript / TypeScript / C / Java:**
```javascript
// mcp: begin region role=code name=auth-handler anchors=[code:auth]
function handleAuth(req, res) {
  // ...
}
// mcp: end
```

**Python / Shell / YAML:**
```python
# mcp: begin region role=code name=main-loop anchors=[code:main]
def main():
    while True:
        process()
# mcp: end
```

## Rules

1. **Use only configured roles.** Do not invent roles not listed in the config.

2. **Proper nesting.** Every `begin` must have a matching `end` in the same file. Regions must nest cleanly (no overlapping).

3. **Same-file boundaries.** Never start a region in one file and end it in another.

4. **Meaningful names.** Use short, descriptive, kebab-case names that identify the region's purpose (e.g., `name=data-validation`, not `name=section3`).

5. **Stable anchors.** Assign anchors to important nodes that other parts of the project might reference. Use a consistent naming convention:
   - `sec:` for sections
   - `def:` for definitions
   - `thm:` for theorems
   - `ex:` for examples
   - `code:` for code blocks
   - `note:` for notes

6. **Do not modify content.** Only insert comment lines. Never change the meaning, structure, or formatting of existing content.

7. **Appropriate granularity.** Annotate at the level that provides useful navigation:
   - Top-level logical sections (chapters, major sections)
   - Important definitions, theorems, or concepts
   - Significant code blocks or functions
   - Examples and illustrations
   - Do NOT annotate every paragraph or trivial element.

8. **Hierarchical structure.** Use nesting to reflect containment:
   ```
   % mcp: begin region role=section name=methods anchors=[sec:methods]
   \section{Methods}
   
   % mcp: begin region role=definition name=algorithm anchors=[def:algo]
   \subsection{Algorithm}
   ...
   % mcp: end
   
   % mcp: end
   ```

9. **Cross-references.** When content in one region refers to another region's concept, the anchor system enables this. The referencing happens automatically when anchor strings appear in content.

## Workflow

1. **Read the config** to learn the annotation syntax and allowed roles.
2. **Survey the project** to understand its structure and identify logical regions.
3. **Plan the annotation hierarchy** before inserting any comments.
4. **Annotate top-down:** Start with the largest regions, then add nested sub-regions.
5. **Verify nesting:** Ensure every `begin` has a matching `end` and regions don't overlap.
6. **Assign anchors** to nodes that represent important, referenceable concepts.

## Common Patterns

### Document with sections
```
begin region role=section name=<section-name> anchors=[sec:<id>]
  begin region role=definition name=<def-name> anchors=[def:<id>]
  end
  begin region role=example name=<example-name> anchors=[ex:<id>]
  end
end
```

### Code with functions
```
begin region role=code name=<module-name> anchors=[code:<id>]
  begin region role=code name=<function-name> anchors=[code:<func-id>]
  end
end
```

### Mixed content
```
begin region role=section name=<topic>
  begin region role=note name=<note-name>
  end
  begin region role=code name=<code-name>
  end
end
```

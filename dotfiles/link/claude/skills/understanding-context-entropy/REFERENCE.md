# Context Entropy Reference

Examples illustrating the entropy reduction hierarchy and when to use each mechanism.

## The Hierarchy in Practice

### Priority 1: Types/Protocols

**Example: `ApolloQueryCoastGraphQLRequest` protocol**

The codebase enforces the Request → transform → Model pattern through protocol requirements. You can't forget to implement `transform(apolloData:)` because it won't compile.

**Why types won:** This pattern is critical, recurring, and easy to forget. Compiler enforcement means zero documentation needed—the type system teaches the pattern.

**Lesson:** If you can make the compiler reject wrong code, do that instead of writing documentation.

---

### Priority 2: Code Structure

**Example: Package organization (`Interfaces` / `Services` / `UI` split)**

The circular dependency prevention isn't documented in a skill—it's encoded in the package structure itself. When you try to import the wrong module, you get a build error.

**Why code structure won:** The architecture makes wrong paths impossible. No skill needed.

---

### Priority 3: CLAUDE.md

**Example: Date formatting guidance**

```markdown
## Date Formatting
- **API/Serialization**: Use `Date.FormatStyle.api`
- **Display**: Define formatters as static properties, reuse them
```

**Why CLAUDE.md won:** The knowledge is:
- Small (a few sentences)
- Project-wide (applies everywhere)
- Stable (not changing)
- Always loaded (no discovery needed)

A skill would be over-engineering for this.

---

### Priority 4: Skill

**Example: `styling-project-ui`**

**What it codifies:** Access design tokens via `.lighthouse` namespace, with SwiftUI and UIKit examples.

**Why a skill won:** The knowledge is:
- Recurring (every view)
- Needs examples (both SwiftUI and UIKit patterns)
- Has depth (colors, fonts, spacing, animations, haptics)
- Benefits from progressive disclosure (basic usage in SKILL.md, advanced in REFERENCE.md)

CLAUDE.md would be too long. Types can't enforce "use `.lighthouse.textPrimary` not `UIColor.label`".

---

### Priority 5: README

**Example: Project setup instructions for humans**

The README explains how to clone, install dependencies, and run the app—for human developers, not Claude.

**Why README won:** This is human-facing documentation. Claude doesn't need "how to clone" instructions.

---

### Priority 6: Code Comments

**Example: iOS bug workaround**

```swift
// Workaround for rdar://12345678: UIKit doesn't properly
// invalidate layout when trait collection changes mid-animation.
// Remove when targeting iOS 18+.
DispatchQueue.main.async { self.view.setNeedsLayout() }
```

**Why a comment won:** This knowledge is:
- Rare (one specific workaround)
- Context-specific (only relevant here)
- Temporary (will be removed)

A skill would be overkill. CLAUDE.md would clutter project-wide context.

---

## Choosing the Right Mechanism

### "Always validate before saving"

| Option | Verdict |
|--------|---------|
| Skill documenting validation | No—easy to forget to read |
| CLAUDE.md reminder | No—still easy to forget |
| **`ValidatedModel` type** | **Yes—can't save without validating** |

### "Use specific error types, not generic Error"

| Option | Verdict |
|--------|---------|
| Skill with examples | Maybe—if many patterns to show |
| **Protocol requiring `associatedtype Failure: Error`** | **Better—compiler enforces it** |

### "Format dates consistently for API calls"

| Option | Verdict |
|--------|---------|
| Skill | No—too small |
| **CLAUDE.md section** | **Yes—small, stable, project-wide** |
| Static formatter property | Also good—code structure guides usage |

---

## Anti-Pattern Examples

### Type-encoded knowledge doesn't need documentation

The `ApolloQueryCoastGraphQLRequest` protocol requires implementing `transform(apolloQueryData:)`. You don't need a skill saying "remember to implement transform"—the compiler already enforces it.

**Don't document what types already enforce.**

### Temporary workarounds don't need skills

If you're working around a bug that'll be fixed in the next iOS release, use a code comment. Don't pollute the skill library with temporary knowledge.

### One-off solutions don't need codification

You wrote a complex migration script. Great. But it runs once. Don't create a `running-migrations` skill for one script.

---

## The Maintenance Test

Before codifying knowledge, ask: "When this changes, will I remember to update the documentation?"

| Mechanism | Maintenance burden | Self-updating? |
|-----------|-------------------|----------------|
| Types/Protocols | Low | Yes—code changes update behavior |
| Code structure | Low | Yes—structure is the documentation |
| CLAUDE.md | Medium | No—requires manual updates |
| Skill | Medium-High | No—requires manual updates |
| Code comments | Low | Naturally co-located with code |

**Prefer self-updating mechanisms.** Types and code structure are better than prose because they can't drift out of sync.

---

## Edge Cases

### "We might need this someday"
Don't codify it. Wait for recurrence. Speculative documentation adds noise without proven value.

### "This is complex but rare"
If it's rare, a code comment is fine. Skills are for recurring patterns.

### "I just spent 4 hours figuring this out"
Pain alone isn't enough. Ask:
1. Will someone else hit this? (Recurrence)
2. Is it stable? (Stability)
3. Can it be enforced with types? (Prefer types)

If the answer to #3 is yes, add types. Otherwise, choose the lightest mechanism that works.

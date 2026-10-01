# Design interpretation template

Fill in every section, keeping each one short (1–4 lines). Show it to the
developer **before** editing any file, and repeat it in the final report.
Write it for English Tutor, not as a description of the reference.

```markdown
## Design interpretation: <page>

**References used**: <files>; skipped: <file — reason> (or "none")

**Visual direction**: <1–2 sentences>

**Typography hierarchy**:
- Prompt: <relative size / weight>
- Question / instruction: <…>
- Supporting info (labels, progress, hints): <…>

**Spacing system**: <base unit and scale>; generous around <…>, tight within <…>

**Actions**: primary = <one action per state>; secondary = <…, how de-emphasized>

**Component treatment**: inputs <…>; buttons <…>; feedback block <…>;
progress <…>; cards <used only for … / not used>

**Feedback behavior**: correct <…>; incorrect <…>; loading/review <shown while …,
gone after …>

**Responsive strategy**: at ~390px <what stacks or resizes>; hierarchy unchanged
because <…>

**Not carried over**: <logos, brand colors as identity, illustrations, copy,
navigation chrome, dashboard structure, …>

**Conflicts / decisions**: <reference A vs. B → chose …, because …>;
<reference vs. learning rule → rule wins: …>
```

## Worked example (shape only, not a prescription)

**Visual direction**: Clean, focused learning interface with generous
whitespace. The exercise sits alone near the top of a single narrow column.

**Typography hierarchy**: a large exercise prompt; medium-weight instruction
text; small, low-emphasis supporting information.

**Actions**: one clearly dominant primary action per state. Secondary actions
are text-style and placed after it.

**Feedback behavior**: correct answers use calm positive color and a short
confirmation. Incorrect answers use clear but non-aggressive error color and
show the expected answer. The spinner disappears as soon as the review
arrives.

**Not carried over**: the reference's logo, illustration and marketing copy,
its sidebar navigation and its card grid.

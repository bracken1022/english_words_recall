# Reference analysis checklist

Look at every reference image, one at a time, then all together. For each
dimension, write down what the reference *does* and the *principle* behind it.
Extract principles, not pixels: "the prompt is ~3× body size and is the only
heavy-weight text" transfers, but "the prompt is 44px Inter Bold" does not.

## Structure

- **Layout**: column count, content width, where the focal element sits
  (centered, top-left), what is fixed vs. scrolling.
- **Information hierarchy**: what the eye lands on first, second and third,
  and how many levels of emphasis there are.
- **Content density**: how much is on screen at once, and the ratio of empty
  space to content.
- **Alignment**: the shared edges and axes, whether text is centered or
  left-aligned, and how consistently.
- **Navigation**: whether it exists, how prominent it is, and where it sits.
  Learning screens usually need very little.

## Type and space

- **Typography**: number of type sizes, size ratio between prompt, body and
  supporting text, weights used, line-height, letter-case, and serif vs. sans.
- **Spacing**: apparent base unit, the scale (tight inside groups, generous
  between groups), padding inside controls.

## Surface

- **Color**: background, ink, a single accent or several, and which colors
  mean success and error. Note the roles, not the hex values.
- **Borders**: present or absent, weight, and whether they divide sections or
  outline controls.
- **Border radius**: sharp, slightly rounded or pill, and whether it is
  consistent across buttons, inputs and containers.
- **Shadow**: none, subtle elevation or heavy, and what it is used for.

## Components

- **Buttons**: how the primary action is told apart from secondary ones
  (fill, size, position), and how many are visible at once.
- **Inputs**: size relative to the text, label placement, the focus
  treatment.
- **Cards**: whether content is boxed, and whether the boxing adds meaning or
  is decoration. Prefer fewer boxes on learning screens.
- **Feedback states**: how correct, incorrect, loading and empty states look,
  how loud they are, and whether they use color, icon, text or motion.

## Behavior

- **Responsive behavior**: if a narrow screenshot exists, what stacks, what
  shrinks, and what stays the same. If not, infer what would have to change
  at about 390px.

## Files you can't use

- Unsupported or unreadable files: skip them and list them in the
  interpretation's "References used".
- Logos, brand marks, illustrations and marketing copy: note that they exist
  so the interpretation can list them under "Not carried over". Never
  describe them for reuse.

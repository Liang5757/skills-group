---
name: create-cinematic-slide-decks
description: "Create or redesign browser-based presentations with interactive navigation and cinematic transitions. Use for cinematic slide decks, scrollytelling talks, 2D-to-3D chart reveals, spatial storytelling, or a presentation inspired by The Last Boring Slide."
metadata:
  version: "0.1.0"
---

# Create Cinematic Slide Decks

Turn a talk, draft deck, or dataset into an interactive presentation. Use motion to make a specific idea easier to understand.

## Storyboard the reveal

1. Identify the audience, presentation setting, and one conclusion the audience should remember. Extract the claims, evidence, and constraints from the supplied material. Flag missing evidence and label illustrative data.
2. Pick one visual whose meaning changes as the story develops. An ordinary chart can establish a baseline before the timeline extends, layers separate, or the camera pulls back to reveal a larger system. Keep a recognizable mark, axis, label, or object visible across the transition.
3. Define the scenes as ordered states. Give each state a claim, the evidence visible before the presenter advances, and the single change triggered by the next step. Hold the reveal long enough for the audience to read it.
4. End with a takeaway that reads on its own, including the implication or next action. See [the source breakdown](references/the-last-boring-slide.md) for an example and a reusable storyboard.

## Build the deck

- Follow the requested output format and the existing project's tooling. For a new browser deck, start with semantic HTML for slide content and CSS or the Web Animations API for shared-element transitions. Use Canvas or WebGL when depth or camera movement carries the explanation. Keep claims, labels, and data available in the DOM.
- Use one active scene index for keyboard, pointer, and touch controls. Support previous and next, clamp navigation at the ends, and ensure interrupted transitions settle on the active scene. Keep navigation keys scoped to the deck and preserve native input behavior in editable fields and focused controls.
- Keep units, axis labels, and data sources attached to their values. Label changes in scale, projections, and gaps in coverage as they appear. Preserve the same data and takeaway in the reduced-motion and WebGL fallback views.
- If the deck must run offline, bundle its runtime, fonts, and media locally. If the user requests a static export, preserve the key states as separate slides or pages.

## Verify the delivered deck

- Run through the full presentation and back across the reveal. Try fast repeated input, check the first and last steps, and verify that visible controls and the keyboard reach the same states.
- Check the reveal at the intended display size and on a narrow viewport. Verify legibility and navigation with reduced motion enabled, and simulate WebGL initialization failure if applicable.
- Match every plotted value, source label, and unit against the supplied evidence. Confirm that the final takeaway remains clear in the static or fallback view.

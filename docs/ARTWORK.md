# Pawgress artwork

## Supplied branding and reused items

The original logo is copied unchanged from the user's supplied source:
https://github.com/milinkway-create/Pawgress/blob/main/assets/logo.png

The owner's existing `assets/item-bed.webp`, `assets/item-ball.webp`, and `assets/item-treat.webp` are reused from the same repository. They are local files; the running application does not fetch assets from GitHub. This reuse is for the owner's Pawgress project and does not grant a third-party asset license.

## Generated companions

`app/static/assets/pets-stages.png` is the final transparent 3×3 sprite atlas. Rows: cat, dog, fish. Columns: baby, youth, grown. The original exploratory `pets.png` is retained as the reference source. All sprites use equal display cells, matching illustration style, consistent palettes and similar species scale. CSS selects a cell; the app never generates an image at runtime.

Generated using the built-in image generation tool, then revised with the initial atlas as reference. No API generation runner or ongoing image-generation endpoint is included.

Final prompt brief:

> Create a transparent 3×3 Pawgress atlas: orange/cream cat, caramel/cream floppy-eared dog, sky-blue/peach fish. Equal cells; no text, grids or accessories. Warm, rounded, cute painted cartoons with consistent dark outlines, blush cheeks and gentle expressions. Babies are low/curling with large heads and short limbs; youths sit or swim playfully with developing proportions; adults sit proudly with fluffy chests and longer tails. Fish progress from round fry with tiny fins to oval youth and an adult with a flowing fantail. Maintain recognizable identity, species scale, transparent padding and distinct silhouettes.

The repository includes the prepared assets, so pet growth, feeding, room decoration and idle reactions incur no image-generation calls. UI motion is a small CSS reaction, not a full sprite-animation rig.

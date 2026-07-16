# Sculpture art

Drop these two files here — the landing page picks them up automatically
(each `<img>` has an `onError` hide handler, so missing files degrade
gracefully to the canvas-only background):

- `hero-sculpture.jpg` — landscape crop, right side of the Hero section
- `mission-sculpture.jpg` — portrait crop, left side of The Mission section

Both are treated with `grayscale(100%) brightness(0.75) contrast(1.1)` in code.

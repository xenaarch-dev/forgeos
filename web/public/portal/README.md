# public/portal/ — Act II imagery slots

Act II shipped on **Path B**: the four portal scenes (hero / field /
garden / loop) are generative compositions rendered live by
`components/fx/PortalScene.tsx` — no binary assets required.

When Higgsfield (or any image-generation) access lands, drop the four
generated 16:9 assets here as:

```
portal-hero.webp     IMG-1 "The Portal"        — S01 hero background
portal-field.webp    IMG-2 "The Field"         — S02 problem background
portal-garden.webp   IMG-3 "The Machine Garden"— S11 proof background
portal-loop.webp     IMG-4 "The Loop"          — S12 loop background
```

Then render them inside `PortalScene` (next/image, quality 80,
`priority` on hero only, explicit `sizes`) *underneath* the existing
canvas/SVG light layers. The vignette + grain layers stay on top — they
lock the Night Forge palette and guarantee text contrast even if
generation drifts. The component API (`<PortalScene variant>`) and all
call sites stay untouched.

Art direction per image is specified in the Act II brief (exact
prompts, Night Forge palette: #060D08 / #3EB489 / #D9832A / #E8E3D2,
no faces, no text, no blue/purple sci-fi).

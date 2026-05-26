# Pixel Fourcut Frame Design Spec

## Output target

- Printer paper: Canon SELPHY postcard size (`4x6`)
- Working overlay canvas: `1200 x 1800` px
- Orientation: portrait
- Usage: two-photo overlay frame PNG placed above already-composited images

Canon SELPHY postcard media is effectively a 4x6 portrait print at 300 dpi, so
`1200 x 1800` is the correct working size for a final overlay asset.

## Layout

The print should read from top to bottom like this:

1. frame header / title zone
2. normal photo
3. AI photo
4. footer / stickers / date / club tag

## Recommended slot geometry

These coordinates assume the frame is a transparent PNG overlay, while the
actual photo composite is rendered underneath.

- Canvas: `1200 x 1800`
- Outer safe margin: `72`
- Header zone: `x=72, y=72, w=1056, h=150`
- Photo slot 1: `x=150, y=270, w=900, h=600`
- Photo slot 2: `x=150, y=950, w=900, h=600`
- Footer zone: `x=72, y=1590, w=1056, h=120`

Notes:
- Each photo slot is `3:2` to match DSLR-origin images cleanly.
- The frame can overlap into the photo area by `12-36px` on each edge.
- Inner corner radius should stay moderate, usually `16-36px`, unless the
  concept is deliberately square and game-like.

## Direction learned from current Korean photo booth brands

Current Korean booth frames trend toward:

- strong brand header bands
- simple but high-contrast borders
- limited-edition collaboration styling
- color-led variants instead of only black/white
- sticker or doodle accents for playful editions
- clean typography with one strong focal accent

That suggests six useful frame families for this booth:

1. `frame-01-signature-white`
2. `frame-02-signature-black`
3. `frame-03-colored-pop`
4. `frame-04-festival-sticker`
5. `frame-05-pixel-arcade`
6. `frame-06-club-badge`

## Generation prompts

These are meant for image generation of the overlay artwork itself, not the
photo content.

### 1. Signature White

Create a portrait 4x6 photo booth overlay frame for a Korean festival photo booth.
Use a clean premium white frame with a bold top title band, two stacked landscape
photo windows, subtle gray line work, and a small footer area for date and club tag.
The style should feel modern Korean photo booth, minimal, glossy, and premium.
Leave the two photo windows fully open for image insertion. No sample photos.

### 2. Signature Black

Create a portrait 4x6 photo booth overlay frame for a Korean festival photo booth.
Use a deep matte black frame with crisp white typography, two stacked landscape photo
windows, thin white border accents, and a polished premium booth aesthetic. Keep it
minimal and high contrast. Leave both photo windows empty and open for image insertion.
No sample photos.

### 3. Colored Pop

Create a portrait 4x6 Korean photo booth overlay frame with a saturated candy-color
look inspired by current color-themed booth frames. Use a bright main color, a clean
title band, rounded window edges, small sparkle accents, and two stacked empty photo
windows. The result should feel trendy, youthful, and easy to read on a real print.
No sample photos.

### 4. Festival Sticker

Create a portrait 4x6 Korean festival photo booth overlay frame with playful sticker
decoration. Use a clean base frame, hand-drawn stars, hearts, lightning bolts, tape,
and doodle accents around two stacked empty photo windows. Keep the layout balanced
and printable. The style should feel like a limited-edition campus festival frame.
No sample photos.

### 5. Pixel Arcade

Create a portrait 4x6 overlay frame for a booth called Pixel Fourcut. The frame should
blend modern Korean photo booth layout with pixel-game UI decoration. Use two stacked
empty photo windows, a bold top header, pixel corners, small inventory-slot motifs,
and subtle retro game HUD accents. Keep it clean enough for real printing, not noisy.
No sample photos.

### 6. Club Badge

Create a portrait 4x6 Korean photo booth overlay frame with a strong custom event badge
look. Use a top banner area that feels like a club patch or festival pass, two stacked
empty photo windows, and a footer area for event date and club name. The style should
feel collectible, commemorative, and premium. No sample photos.

## Color guidance

- Signature White: white, warm gray, soft silver
- Signature Black: black, white, cool gray
- Colored Pop: mint / coral / sky / lilac, one dominant color only
- Festival Sticker: cream base with multicolor sticker accents
- Pixel Arcade: charcoal, off-white, pixel green, electric cyan
- Club Badge: navy or burgundy with gold or cream accents

## File naming

Final frame overlay assets should be saved as:

- `frontend/src/assets/frames/frame-01-signature-white.png`
- `frontend/src/assets/frames/frame-02-signature-black.png`
- `frontend/src/assets/frames/frame-03-colored-pop.png`
- `frontend/src/assets/frames/frame-04-festival-sticker.png`
- `frontend/src/assets/frames/frame-05-pixel-arcade.png`
- `frontend/src/assets/frames/frame-06-club-badge.png`

Preferred format:

- transparent PNG overlay for production use
- optional JPG preview alongside it if needed during selection

# Surface (U17 to U20)

Only when the user asks for visual cleanup. If the project has tokens (Tailwind theme, CSS variables, a design-system package), fix toward those values.

- **U17. Gradients and glows.** Purple-to-blue gradients, gradient text (`bg-clip-text`), colored glows (`shadow-purple-500/50`), blurred blobs → solid neutral surface, solid text, small neutral shadow `0 1px 2px rgb(0 0 0 / 0.05)` or a hairline border.
- **U18. Random spacing.** `mt-[13px]`, `gap: 7px` → nearest of 4, 8, 12, 16, 20, 24, 32, 40, 48, 64.
- **U19. Extra-heavy fonts.** `font-black`, `font-extrabold`, 800/900 → 600 or 500.
- **U20. Bouncy motion.** `transition-all`, `hover:scale-105` on cards, `animate-bounce` → `transition-colors` 150ms ease-out; buttons may press to 0.97.

Never change the palette, font family, sizes, radii or section order. Replace a value, don't redesign.


---
name: modern-ui-craft
description: Design and implement high-craft, tactile, anti-slop user interfaces inspired by Linear and Apple HIG across any platform or framework (Web, Desktop, Mobile, Apps, Games).
---

# Modern UI Craft: The Anti-Slop Design & Engineering System

This skill teaches the principles, design tokens, visual hierarchy, and cross-platform implementation patterns required to build modern, high-craft user interfaces inspired by Linear and Apple Human Interface Guidelines (HIG).

Use this skill whenever you are asked to design, build, or refactor an interface—whether it is a web app, desktop tool, mobile application, dashboard, or game UI—to ensure it looks intentional, elegant, tactile, and completely free of "AI slop".

---

## 1. The Anti-Slop Manifesto (Why Most Generated UIs Look Bad & How to Fix Them)

AI-generated interfaces almost always fall into three traps:
1. **Wordy Filler Text**: Filling empty space with verbose, corporate paragraphs (*"Welcome to our next-generation tactical combat simulation..."*).
2. **Emoji & Glyph Clutter**: Scattering random emojis (🎮, 🧠, ⚔️, 🚀, 🏆) to simulate personality instead of crafting real visual hierarchy.
3. **Gaudy / Monotonous Palettes**: Either stark, blinding `#000000`/`#FFFFFF` or tacky dark-mode neon gradients (purple/cyan) and casino dark-gold.

### The 5 Core Principles:

| Principle | The Amateur / AI Slop Mistake | The Modern High-Craft Rule |
| :--- | :--- | :--- |
| **Copy & Text** | Long explanatory paragraphs and redundant subtitles. | **70% reduction in words**. Use punchy verbs, crisp titles, and let visual diagrams or cards do the explaining. |
| **Iconography** | Random emojis, mismatched SVG packs, or non-standard Unicode. | **Strict keyboard ASCII or procedural monochrome vectors**. Use circular tokens, badges, or SF-Symbols-style line art. |
| **Color Base** | Pure cold digital white (`#FFFFFF`) or pure pitch black (`#000000`). | **Warm, tactile canvas** (Warm linen/parchment `#F7F7F4` or `#F4F3EE`). It feels like tangible, premium editorial paper. |
| **Card Borders** | Heavy, blurry, muddy drop-shadows (Bootstrap 2012 style). | **Hairline 1px border** (`#E1E3DC` or `#DDD7CC`) with high-contrast white card surface (`#FFFFFF`) and optional micro-ambient shadow. |
| **Spatial Rhythm** | Elements crammed together with inconsistent 5px/10px margins. | **Strict 8pt spatial grid** with generous outer breathing room (32-48px) and card padding (20-28px). |

---

## 2. Universal Design Token Architecture

Regardless of the technology stack (CSS/Tailwind, Flutter, Qt, Tkinter, SwiftUI), implement this cohesive token scale:

### A. The Organic & Restrained Palette
- **Canvas / Page**: `#F7F7F4` or `#F4F3EE` (Warm linen neutral, never stark grey)
- **Surface / Card**: `#FFFFFF` (Crisp white elevated surface)
- **Hairline Border**: `#E1E3DC` or `#DDD7CC` (Subtle 1px boundary)
- **Ink Primary**: `#1A1A1B` or `#1C2621` (High-contrast charcoal, softer than pure black)
- **Ink Muted**: `#595C57` or `#73766E` (Metadata, hints, secondary labels)
- **Primary Accent (Forest Pine)**: `#2D6A4F` or `#2F6B2B` (Hover: `#20503B`, Tint: `#E8F2EC`)
- **Secondary Accent (Warm Oak / Clay)**: `#8C5E3C` or `#B3362B` (Hover: `#6E482D`, Tint: `#F5ECE3`)
- **Warning / Destructive (Rust)**: `#C84630` (Tint: `#FBEAE8`, Border: `#F1BEB7`)
- **Highlight (Amber Gold)**: `#F7CF3D` / `#D48B28` (Stars, achievements, focal points)

### B. Spacing Scale (8pt Grid)
```
SPACE_XS : 4px   (Tight inline tags, icon padding)
SPACE_S  : 8px   (Button padding, gap between tag and title)
SPACE_M  : 16px  (Gap between small cards, section margins)
SPACE_L  : 24px  (Internal padding of cards, grid gap)
MARGIN   : 32px  (Outer viewport padding on mobile/compact)
PAGE_PAD : 40px+ (Outer viewport padding on desktop/web)
```

### C. Standardized Corner Radius
Never mix random border radii. Enforce **one primary radius** across the entire UI:
- Primary Radius: `10px` to `14px` (for cards, modals, primary buttons).
- Secondary / Pill Radius: `9999px` or `4px - 6px` (for compact badges and chips).

### D. Typography Hierarchy
```
Hero Display : 32px - 48px | Bold     | High tracking / confident impact
Title        : 20px - 24px | Bold     | Card headers, modal titles
Heading      : 14px - 16px | SemiBold | Section labels, card sub-headers
Body         : 13px - 14px | Regular  | Informational copy (kept concise)
Caption/Pill : 10px - 12px | Bold     | All-caps or small-caps badges
```

---

## 3. Core Component Anatomy & Patterns

### 1. The Two-Tier Interactive Card Grid
When presenting options (game modes, project types, dashboard tools), use a two-tier hierarchy:
1. **Tier 1 (Hero Cards)**: 2 large cards side-by-side with high visual weight.
   - **Pill Badge**: Small-caps badge at the top (`SOLO PLAY`, `CAMPAIGN`).
   - **Prominent Title**: 20-24pt Bold.
   - **Primary Action Button**: Solid accent color, high contrast.
   - **Interaction**: The entire card surface is hoverable (`border-color` shifts to accent) and clickable.
2. **Tier 2 (Utility Shelf)**: 3-4 compact cards below the hero row for tools/secondary workflows.
   - Consistent height, subtle border, secondary outline button.

### 2. Tactile Buttons with Micro-Affordances
A modern button must feel satisfying and physical to click:
- **Rest State**: Crisp hairline border or solid fill, legible typography.
- **Hover State**: Border shifts to primary accent or background brightens by 5-8%. Cursor: `pointer` / `hand2`.
- **Pressed / Active State**: Subtle translation downward (1-2px sink) or background darkens by 10%.
- **Focus Ring**: 2px outline with 2px offset for keyboard accessibility (Tab navigation).
- *Avoid the Tkinter / Framework width blowout*: Never set fixed button widths based on characters. Use generous horizontal padding (`px-5 py-2.5` / `padx=20, pady=8`).

### 3. Category Pill Badges
Replace wordy explanatory text with compact, tinted pill tags:
- Height: ~22-26px.
- Padding: 2px vertical, 8-10px horizontal.
- Style: 10-15% tint of the accent color as background (`#E8F2EC`), with 100% solid accent color for text (`#2D6A4F`).
- Font: 10-11px, Bold / SemiBold.

### 4. Diagram Over Text (Visual Rules & Information)
When communicating mechanics (who beats whom, status pipelines, process flows):
- **Do not write paragraphs of text**.
- Create a visual cyclical diagram or compact flowchart (e.g., circular curved arrows between 3 nodes).
- Make secondary telemetry or complex diagrams **collapsible with a toggle (`[-]` / `[+]`)** so the interface stays clean.

---

## 4. Cross-Platform Implementation Guide

### Web (HTML, Tailwind CSS, React, Vue)
```html
<!-- Base Canvas -->
<div class="min-h-screen bg-[#F4F3EE] text-[#1A1A1B] p-8 md:p-12 font-sans antialiased">
  <!-- Top Navigation -->
  <header class="flex items-center justify-between max-w-5xl mx-auto mb-12">
    <div class="flex items-center gap-3">
      <span class="text-xl font-bold tracking-tight text-[#2D6A4F]">APP TITLE</span>
      <span class="text-xs font-bold uppercase tracking-wider px-2.5 py-1 rounded-md bg-[#E8F2EC] text-[#2D6A4F]">PRO</span>
    </div>
    <div class="flex items-center gap-3">
      <button class="px-4 py-2 text-sm font-semibold bg-white border border-[#DDD7CC] rounded-xl hover:bg-[#F2F3EF] transition-colors">Documentation</button>
      <button class="px-4 py-2 text-sm font-semibold bg-[#FBEAE8] border border-[#F1BEB7] text-[#C84630] rounded-xl hover:bg-[#F8D7D3] transition-colors">Exit</button>
    </div>
  </header>

  <!-- Hero Row: 2 Primary Cards -->
  <main class="max-w-5xl mx-auto space-y-6">
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <!-- Card 1 -->
      <div class="group relative bg-white border border-[#DDD7CC] hover:border-[#2D6A4F] rounded-2xl p-7 transition-all cursor-pointer shadow-sm">
        <span class="inline-block text-xs font-bold uppercase px-2.5 py-1 rounded bg-[#E8F2EC] text-[#2D6A4F] mb-3">PRIMARY MODE</span>
        <h2 class="text-2xl font-bold text-[#1A1A1B] mb-6">Interactive Workspace</h2>
        <button class="px-5 py-2.5 text-sm font-bold bg-[#2D6A4F] text-white rounded-xl group-hover:bg-[#20503B] transition-colors">Get Started</button>
      </div>

      <!-- Card 2 -->
      <div class="group relative bg-white border border-[#DDD7CC] hover:border-[#8C5E3C] rounded-2xl p-7 transition-all cursor-pointer shadow-sm">
        <span class="inline-block text-xs font-bold uppercase px-2.5 py-1 rounded bg-[#F5ECE3] text-[#8C5E3C] mb-3">CHALLENGE</span>
        <h2 class="text-2xl font-bold text-[#1A1A1B] mb-6">Tactical Sandbox</h2>
        <button class="px-5 py-2.5 text-sm font-bold bg-[#8C5E3C] text-white rounded-xl group-hover:bg-[#6E482D] transition-colors">Explore</button>
      </div>
    </div>
  </main>
</div>
```

### Desktop (Tkinter + Pillow, Flutter, Qt, Electron)
1. **Enable High-DPI Awareness**:
   Always initialize Windows `SetProcessDpiAwareness(2)` or platform equivalents on app launch so borders and fonts don't blur.
2. **Supersample Canvas & Custom Graphics**:
   In lightweight desktop toolkits (like Tkinter/PyQt), native vector rendering can be pixelated. Render curves, arrows, and custom badges at $3\times$ scale in Pillow/Skia and resize down with `LANCZOS` / antialiasing into an `@lru_cache`.
3. **Card Event Propagation**:
   When building card containers, bind `<Button-1>` and `<Enter>`/`<Leave>` to all child labels and frames so clicking anywhere on the card triggers the action.

---

## 5. UI Quality Audit Checklist

Before considering an interface complete, evaluate it against this 8-point checklist:

- [ ] **1. Emoji Check**: Are there 0 emojis and 0 non-standard Unicode characters?
- [ ] **2. Copy Economy**: Has all verbose, fluffy AI copy been stripped out? Are labels verb-first and punchy?
- [ ] **3. Palette Authenticity**: Is the background warm linen/parchment rather than pure `#000000` or stark `#FFFFFF`?
- [ ] **4. Hairline Elevation**: Are card boundaries defined by subtle 1px hairline borders instead of heavy black shadows?
- [ ] **5. Unified Radius**: Is there exactly one primary corner radius applied across cards and primary buttons?
- [ ] **6. Spatial Rhythm**: Is every padding and gap value a multiple of the 8pt grid (`8, 16, 24, 32, 40`)?
- [ ] **7. Interactive Hit-Boxes**: Is the entire card clickable, with clear hover state transitions?
- [ ] **8. Visual Explanation**: Are complex relationships conveyed via visual diagrams or badges instead of walls of text?

# Design system — pdf-baomu-tutorial

The visual language behind the "baomu" (保姆, _hand-holding_) tutorial PDF
style, written down. This file is the rationale behind `templates/styles.css`,
so the stylesheet stays stable across edits and contributors can change one
thing without breaking three others.

If you are tempted to introduce a new color, a new font size, or a new callout
variant, read the matching section here first. If the answer is not in this
file, that is itself a signal to stop and reconsider.

## 1. What this design is for

Baomu PDFs exist to **teach a complete beginner how to do a thing, step by
step, without leaving them stuck**. Everything in the visual system serves
that single brief:

- **Executable, not just readable** — the reader does not need to understand
  every line. They follow the steps, paste the Claude Code prompts, and arrive
  at a working result.
- **Layered** — cover, table of contents, chapter, step, code, prompt block,
  warning box. Each layer has one job and one look.
- **Restrained** — five colors total, generous whitespace, no decoration for
  decoration's sake.

This is **not** a generic document design system. It is opinionated for one
content shape: hands-on, sequenced, instructional. For business one-pagers,
investment reports, or editorial long-form, this language is the wrong tool —
use something quieter (e.g. an editorial system like `tw93/kami`).

## 2. Color tokens

Five role-bearing colors, plus a neutral ramp. Hex values are duplicated in
`styles.css` directly; this table is the agreed meaning of each.

| Token             | Hex       | Role                                                         |
| ----------------- | --------- | ------------------------------------------------------------ |
| `--ink-primary`   | `#1a1a1a` | Body text                                                    |
| `--ink-strong`    | `#111`    | Cover title, headline emphasis                               |
| `--ink-soft`      | `#333`    | Step titles, structural labels                               |
| `--ink-muted`     | `#555`    | Secondary copy, end-card body                                |
| `--ink-faint`     | `#999`    | Footer page numbers, tertiary captions                       |
| `--accent-tip`    | `#1976d2` | Tip callout border + heading (blue)                          |
| `--accent-warn`   | `#ffa000` | Warning callout border + heading (yellow / amber)            |
| `--accent-stop`   | `#c92a2a` | Stop / forbidden callout border + heading (red)              |
| `--accent-cc`     | `#7b1fa2` | Claude Code prompt block border + heading (purple)           |
| `--accent-chap`   | `#d63384` | Chapter numeral (零壹贰) tag, magenta-leaning pink           |
| `--surface-tip`   | `#e3f2fd` | Tip callout background                                       |
| `--surface-warn`  | `#fff8e1` | Warning callout background                                   |
| `--surface-stop`  | `#ffebee` | Stop callout background                                      |
| `--surface-cc`    | `#f3e5f5` | Claude Code block background                                 |
| `--surface-cover` | gradient  | Cover full-bleed `#f8f9fa → #e9ecef`, 135°                   |
| `--surface-end`   | `#fafafa` | End-card box                                                 |
| `--code-bg`       | `#1e1e1e` | Code block background (paired with Shiki dark theme output)  |

The five role colors (tip / warn / stop / cc / chap) form a deliberate
**semantic palette**. Do not introduce a sixth — if a new callout type seems
necessary, ask first whether it can fold into one of the four existing ones.
"Note" → tip. "Heads-up" → warn. "Don't do this" → stop. "Run this through
Claude Code" → cc.

## 3. Typography

### 3.1 Type scale

| Role             | Size     | Weight  | Line-height |
| ---------------- | -------- | ------- | ----------- |
| Cover title      | 32 pt    | 900     | 1.3         |
| Cover subtitle   | 14 pt    | normal  | 1.5         |
| Chapter title    | 22 pt    | 700     | 1.3         |
| Section h2       | 15 pt    | 700     | 1.5         |
| Body             | 11 pt    | normal  | 1.75        |
| Callout body     | 10.5 pt  | normal  | 1.7         |
| Code block       | 10 pt    | normal  | 1.6         |
| Step title       | 12 pt    | 700     | inherit     |
| Footer / page #  | 9 pt     | normal  | inherit     |
| Cover tag pill   | 9.5 pt   | 700     | inherit     |

The body line-height of **1.75** is wider than most Western book typography
suggests. This is intentional: dense Chinese text needs more vertical air
than English to stay readable at 11pt on A4. Do not reduce.

### 3.2 Font stack

- **Sans (default):** `"Noto Sans CJK SC", "Noto Sans", sans-serif`
- **Mono (code, prompts, chapter numerals):** `"SF Mono", "Monaco", "Menlo",
  "Consolas", "Courier New", monospace`

The whole system uses a **single sans-serif family for body and headlines**.
There is no serif. This is the opposite choice from editorial systems like
Kami — and it is correct here, because hands-on tutorials read as utility
copy, not as composed pages.

Why Noto Sans CJK SC specifically: it is the only major free Chinese font
that ships uniform glyph weights across the entire CJK range, including
rare characters that show up in command-line output, file paths, and
error messages. Substitutes (Source Han Sans Adobe build, system PingFang
on macOS) work, but Noto is the one we test against.

### 3.3 Mixed CJK / Latin

`styles.css` does **not** insert pixel-width spaces between CJK and Latin
runs. That work is done upstream by `scripts/lint_html.py`, which applies
the *中文文案排版指北* rules during the build. Keep this division: the
stylesheet is for layout, not punctuation.

## 4. Layout

- **Page:** A4 (210 × 297 mm), margin `2cm 2cm 2.5cm 2cm`. The wider bottom
  margin gives breathing room for the page-number footer.
- **Cover:** Full-bleed, no margins, gradient background, content vertically
  centered.
- **Table of contents:** Single page, max 9 entries. If a tutorial has more
  than 9 chapters, the structure is probably wrong — split into two PDFs.
- **Chapter break:** `<h1 class="chapter-break">` starts a new page; plain
  `<h1>` flows inline. Use chapter-break for major shifts (setup → usage),
  inline h1 only when the previous section ended with substantial whitespace.
- **Bottom-of-page footer:** Page number `n / total` centered, custom
  footer-left label left-aligned. Suppressed on the cover.

## 5. Callout taxonomy

Four variants, in priority order:

| Variant         | When to use                                                |
| --------------- | ---------------------------------------------------------- |
| `callout-tip`   | "Here is something useful to know." Optional context.      |
| `callout-warn`  | "Read this before continuing, or you will hit a snag."     |
| `callout-stop`  | "Do not do this. It will break things / leak credentials." |
| `callout-cc`    | "Paste this prompt into Claude Code and continue."         |

The `callout-cc` block is the **single most distinctive element** of this
design system. It carries the brand promise: *you do not need to type
commands; you just need to talk to Claude Code in Chinese, like this*.
Every baomu tutorial should use at least one `callout-cc`. A tutorial with
none of these signals that the workflow is not actually Claude-Code-friendly,
and the manuscript should be revisited rather than the design changed.

## 6. Step component

Numbered steps use a black filled circle (`background: #1a1a1a`, white
numeral, 32px diameter) followed by a step title in 12pt bold and a body in
11pt regular. The circle anchors the eye on scan; the inline two-column
layout (number + content) keeps a long tutorial from feeling like a wall.

Steps **inside a callout-cc are forbidden**: a Claude Code prompt is one
indivisible action, not a sequence. If you find yourself wanting steps
inside a prompt, split into multiple `callout-cc` blocks.

## 7. Don'ts

These are the most common ways this style gets diluted. Refuse them.

- **Do not add a brand-color band, sidebar, or filled banner at the top of
  the cover.** The cover is monochrome by intent. Color belongs to callouts.
- **Do not bold every other word in body text.** Bold is for term
  introductions only (the first time a concept appears).
- **Do not introduce a fifth callout variant.** See §5.
- **Do not switch the chapter numeral from CJK (零壹贰) to Arabic.**
  The CJK numeral is the cheapest visual reminder that this is a
  Chinese-first document.
- **Do not collapse body line-height below 1.75.** See §3.1.
- **Do not use `rgba()` for solid backgrounds.** WeasyPrint has a known
  double-rectangle rendering bug with `rgba()` on `background-color`.
  Use 6-digit hex instead. (This bug exists in current WeasyPrint releases
  as of v66; revisit when fixed upstream.)
- **Do not commit code into a tutorial that uses placeholder credentials
  like `password123`.** Use clearly-impossible values
  (`<your-password>`, `xxxxxxxx`) so a copy-paste reader is forced to edit.

## 8. Evolving the system

When you genuinely need to add something:

1. **Confirm the existing system can't do it.** Re-read sections 3, 5, and 6.
2. **Add the token to this file first**, with role and rationale.
3. **Then add the CSS rule** in the matching section of `styles.css`.
4. **Render a smoke test** — the same `<callout-cc>`-bearing snippet used by
   `scripts/preview_all.py` — and confirm no other component shifted.
5. **Update `references/quality-checklist.md`** if the change introduces a
   new failure mode authors should check before shipping.

The order matters. CSS-first edits drift; tokens-first edits accumulate into
a system.

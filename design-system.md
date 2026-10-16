# WOKA — Design System & Visual Specification

## 1. Brand Philosophy & Aesthetic Direction
Woka is built for creators, influencers, and modern brands. It balances **high-energy creative vibrance** with **institutional enterprise trust**. It avoids the tired purple-gradient SaaS clichés by pairing crisp, airy neutral backgrounds with a signature **Violet-to-Coral** accent spectrum used with restraint.

### Aesthetic Principles:
1. **Content First, Accent Second:** Interfaces prioritize creator media, campaign metrics, and engagement graphs. Colorful gradients are reserved for primary action hero banners, verified badges, and interactive state triggers.
2. **High-Contrast Legibility:** Deep slate typography (`#0F172A`) over clean porcelain (`#F8FAFC` / `#FFFFFF`) ensures effortless reading during high-velocity campaign reviews.
3. **Intentional Feedback:** Every button, toggle, and trigger responds with micro-animations, loading states, and explicit tooltips. No dead or purely decorative controls.

---

## 2. Color Palette & Tokens

### 2.1 Primary Brand Gradient & Accents
| Token Name | Hex Code | Tailwind Equivalent | Role & Application |
|---|---|---|---|
| `--color-violet-primary` | `#7C3AED` | `violet-600` | Primary buttons, active tabs, brand anchor |
| `--color-violet-light` | `#8B5CF6` | `violet-500` | Hover states, active borders, glow accents |
| `--color-coral-primary` | `#F43F5E` | `rose-500` | Gradient terminus, urgent alerts, high-impact CTA |
| `--color-coral-light` | `#FB7185` | `rose-400` | Secondary badge highlights, energetic accents |
| `--gradient-woka` | `linear-gradient(135deg, #7C3AED 0%, #F43F5E 100%)` | `bg-gradient-to-r from-violet-600 to-rose-500` | Hero banners, Pro plan badges, Logo mark |

### 2.2 Neutrals & Surface Foundation
| Token Name | Hex Code | Role |
|---|---|---|
| `--surface-bg` | `#F8FAFC` (`slate-50`) | Primary canvas background |
| `--surface-card` | `#FFFFFF` | Card backgrounds, modals, elevated surfaces |
| `--surface-subtle` | `#F1F5F9` (`slate-100`) | Input fields, table header background, inactive tabs |
| `--border-default` | `#E2E8F0` (`slate-200`) | Standard card and container borders |
| `--border-focus` | `#8B5CF6` (`violet-500`) | Focused inputs and active card rings |
| `--text-primary` | `#0F172A` (`slate-900`) | Page headers, primary values, body headings |
| `--text-secondary` | `#475569` (`slate-600`) | Subtitles, helper text, table column labels |
| `--text-muted` | `#94A3B8` (`slate-400`) | Timestamps, inactive icons, placeholder text |

### 2.3 Semantic & Status Colors
| Status | Background | Text / Border | Purpose |
|---|---|---|---|
| **Success** | `#ECFDF5` (`emerald-50`) | `#059669` (`emerald-600`) | Active automations, approved deliverables, paid invoices |
| **Warning** | `#FFFBEB` (`amber-50`) | `#D97706` (`amber-600`) | Sandbox demo mode, approaching usage limits, revision needed |
| **Error** | `#FEF2F2` (`red-50`) | `#DC2626` (`red-600`) | Failed DM delivery, expired Meta token, overdue invoices |
| **Info / Sandbox**| `#EFF6FF` (`blue-50`) | `#2563EB` (`blue-600`) | Demo simulator active, official Meta compliance notices |

---

## 3. Typography Scale

Font Family: **Plus Jakarta Sans**, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif.

| Level | Size / Line-Height | Weight | Tracking | Usage |
|---|---|---|---|---|
| **Display 1** | 2.5rem (40px) / 1.15 | Bold (700) | `-0.025em` | Landing page hero, big creator stats |
| **Heading 1** | 1.875rem (30px) / 1.25 | SemiBold (600) | `-0.02em` | Section headers, Dashboard overview title |
| **Heading 2** | 1.5rem (24px) / 1.3 | SemiBold (600) | `-0.015em` | Card group titles, modal headers |
| **Heading 3** | 1.125rem (18px) / 1.4 | Medium (500) | `-0.01em` | Widget titles, deliverable names |
| **Body Large** | 1rem (16px) / 1.5 | Regular (400) | Normal | Primary body text, descriptions |
| **Body Normal**| 0.875rem (14px) / 1.5 | Regular (400) | Normal | Standard UI inputs, table cells, form labels |
| **Caption** | 0.75rem (12px) / 1.4 | Medium (500) | `+0.01em` | Badges, timestamps, rate limit meters |

---

## 4. Spacing, Elevation & Radii

### 4.1 Spacing Scale
- `space-1`: 4px | Micro badges, compact tag spacing
- `space-2`: 8px | Button icon gap, list item vertical padding
- `space-3`: 12px | Input inner padding, compact cards
- `space-4`: 16px | Standard component padding, grid gaps
- `space-6`: 24px | Card container inner padding
- `space-8`: 32px | Section gutters, dashboard layout margin

### 4.2 Border Radii
- `rounded-sm`: 6px (`0.375rem`) — Badges, tooltip chips
- `rounded-md`: 8px (`0.5rem`) — Form inputs, select dropdowns
- `rounded-lg`: 12px (`0.75rem`) — Interactive buttons, small widgets
- `rounded-xl`: 16px (`1.0rem`) — Primary cards, modals, preview containers
- `rounded-2xl`: 24px (`1.5rem`) — Hero callout panels, rate card highlights
- `rounded-full`: 9999px — Pill badges, user avatars

### 4.3 Controlled Shadows
- **Card Base (`shadow-sm`):** `0 1px 2px 0 rgb(15 23 42 / 0.05)`
- **Card Hover (`shadow-md`):** `0 4px 12px -2px rgb(15 23 42 / 0.08), 0 2px 4px -2px rgb(15 23 42 / 0.04)`
- **Modal / Floating Menu (`shadow-xl`):** `0 20px 25px -5px rgb(15 23 42 / 0.1), 0 8px 10px -6px rgb(15 23 42 / 0.1)`
- **Woka Accent Glow:** `0 8px 24px -4px rgba(124, 58, 237, 0.25)`

---

## 5. Core Component Specifications

### 5.1 Buttons
- **Primary Action:** Solid violet (`bg-violet-600 hover:bg-violet-700 text-white font-medium shadow-sm hover:shadow-md transition-all active:scale-[0.98]`).
- **Brand Hero / Special CTA:** Signature gradient (`bg-gradient-to-r from-violet-600 to-rose-500 hover:from-violet-700 hover:to-rose-600 text-white shadow-md hover:shadow-lg`).
- **Secondary / Outline:** White surface with subtle border (`bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 shadow-sm`).
- **Ghost:** Borderless (`text-slate-600 hover:text-slate-900 hover:bg-slate-100`).
- **Destructive:** Subtle red alert (`bg-red-50 hover:bg-red-100 text-red-600 border border-red-200`).

### 5.2 Badges & Status Indicators
- **Verified Creator:** Violet background chip with checkmark icon (`bg-violet-100 text-violet-700 border border-violet-200`).
- **Sandbox / Demo Data:** Amber pill with flask icon (`bg-amber-100 text-amber-800 border border-amber-300 font-semibold`).
- **Live Meta API:** Emerald pill with green pulsing dot (`bg-emerald-100 text-emerald-800 border border-emerald-300`).

### 5.3 Interactive Cards
- White background, 1px slate-200 border, 16px radius, subtle transition on hover (`hover:border-violet-300 hover:shadow-md`).
- Header with title, subtitle, and optional right-aligned action icon.

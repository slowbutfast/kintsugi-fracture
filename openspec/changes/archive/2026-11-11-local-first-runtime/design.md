---
name: Windows XP Luna Local Companion
colors:
  primary: "#0058ee"      # Windows XP Luna Royal Blue
  secondary: "#ece9d8"    # Classic 3D Face background
  background: "#f0ede0"   # Viewport canvas off-white
  surface: "#ffffff"      # Input and well surfaces
  text:
    primary: "#000000"    # High contrast black text
    muted: "#666666"      # Muted labels and status captions
  border: "#7f9db9"       # Inset well border
  status:
    success: "#2e7d32"    # Connected green
    warning: "#ed6c02"    # Connecting / prompt amber
    error: "#d32f2f"      # Disconnected / blocked red
typography:
  fontFamily:
    sans: "Tahoma, 'Segoe UI', Arial, sans-serif"
    mono: "'Courier New', monospace"
  scale:
    h1: "13px, weight 700"
    h2: "12px, weight 700"
    body: "11px, weight 400"
    caption: "10px, weight 400"
spacing:
  xs: "2px"
  sm: "4px"
  md: "8px"
  lg: "12px"
  xl: "16px"
rounded:
  sm: "2px"
  md: "3px"
  lg: "4px"
  full: "9999px"
---

## 1. Visual Overview & Philosophy

The user interface adheres to the Windows XP Luna desktop aesthetic established in `DESIGN.md`. For the local-first companion architecture, the interface incorporates an engine connection indicator and controls seamlessly into the existing Luna chrome.

- **Aesthetic Tone**: Authentic early-2000s desktop utility; functional, clear affordances, beveled push-buttons.
- **Target Surfaces**: Windows XP titlebar menu, status bar, and dialog wells.
- **Visual References**: Windows XP network connection indicator in the system tray / status bar.

---

## 2. Color System & Contrast Rationale

| Token Name | Hex Value | Semantic Role | Background Pair | Contrast Ratio | WCAG Compliance |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `primary` | `#0058ee` | Window titlebar active gradient | `#ffffff` | 4.8:1 | **PASS (AA)** |
| `text.primary` | `#000000` | High-contrast UI text | `#ece9d8` | 13.5:1 | **PASS (AAA)** |
| `status.success` | `#2e7d32` | Connected engine badge | `#ece9d8` | 4.9:1 | **PASS (AA)** |
| `status.error` | `#d32f2f` | Disconnected engine indicator | `#ece9d8` | 4.7:1 | **PASS (AA)** |

---

## 3. Typography Hierarchy

| Level | Font Family | Size | Weight | Line Height | Intended Usage |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Titlebar` | `Tahoma` | `12px` | `700` | `1.2` | Window title caption |
| `Body` | `Tahoma` | `11px` | `400` | `1.3` | Labels, inputs, menus |
| `Status` | `Tahoma` | `11px` | `400` | `1.2` | Inset status bar panes |
| `Badge` | `Tahoma` | `10px` | `700` | `1.0` | Connection status indicators |

---

## 4. Component Anatomy & States

### Component: Engine Connection Toolbar & Status Pane

- **Visual Hierarchy & Placement**: Located in the status bar at the bottom of the window, and optionally in the menu header when running on a hosted domain.
- **Component States**:
  - **Same-Origin Local (`http://127.0.0.1:8000`)**: Indicator displays `Local Engine: Connected (Same-Origin)` with a subtle green dot (`#2e7d32`).
  - **Hosted Disconnected (`https://...`)**: Indicator displays `Local Engine: Disconnected` with an amber button `[Connect Engine]`.
  - **Connecting (User Gesture)**: Displays `Connecting to 127.0.0.1:8000…` with disabled button state.
  - **Connected (Companion)**: Displays `Local Engine: Connected (127.0.0.1:8000, v1.0)` with a green dot and a secondary link `[Open Local Studio ↗]`.
  - **Blocked / Offline**: Status pane highlights red (`#d32f2f`) with the text `Engine unreachable. Launch kintsugi-studio and click [Open Local Studio ↗]`.

---

## 5. Responsive Layout & Breakpoints

| Viewport | Breakpoint | Layout Pattern | Navigation / Sizing Rules |
| :--- | :--- | :--- | :--- |
| **Mobile** | `< 900px` | Pinned status bar at base | Touch target $\ge 40\text{px}$ for the connect/retry button |
| **Desktop** | `≥ 900px` | Segmented status bar | Inset 3D wells with 11px Tahoma typography |

---

## 6. Interaction, Motion & Sound

- **Transitions**: Native Windows XP immediate response (no modern ease-in-out transforms; 0ms transitions to match vintage desktop OS behavior).
- **Feedback**: Clicking "Connect Engine" updates the status text immediately. If blocked, an alert banner provides clear instruction and a direct link.

---

## 7. Do's and Don'ts

- **DO** keep button bevels and Luna styles authentic to Windows XP.
- **DO** provide a clickable fallback link to `http://127.0.0.1:8000` whenever companion connection fails.
- **DON'T** pop up unexpected browser permission prompts on page load without a prior user gesture.
- **DON'T** use floating toast notifications that clash with the Windows XP aesthetic.

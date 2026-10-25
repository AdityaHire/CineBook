# Cenebook — Wireframes and UI Design

Version 1.1 · Apple-inspired UI revision · Companion to the Cenebook PRD v1.2

## 1. Purpose and Approach

This document defines the layout and behavior of every page in the Cenebook MVP. Version 1.1 applies Apple's interface design principles, translated for the web: instant response, direct manipulation, interruptible spring motion, translucent materials, and restrained typography. Wireframes are low-fidelity text sketches: they show structure, content, and interaction, not final colors or imagery. Pages are rendered by Django templates and styled with Bootstrap 5; the seat map, live total, hold countdown, and sheets use plain JavaScript (with a small spring library for gesture-driven motion).

## 2. Design Principles (Apple-Inspired)

- **Respond instantly.** Feedback appears on pointer-down, never on release. No artificial delay sits between input and a visible change.
- **Stay attached to the finger.** Dragged content (seat map, sheets) tracks 1:1 from the point where it was grabbed.
- **Never block input.** Every animation can be interrupted and reversed at any moment, and motion starts from what is currently on screen.
- **Use springs, not timelines.** Critically damped by default; bounce only after a flick or throw.
- **Keep space consistent.** Things leave along the path they arrived and grow from the element that triggered them.
- **Say it once, clearly.** One primary action per page; hierarchy comes from spacing, weight, and contrast, not decoration.
- **Respect the person.** Honor reduced motion, reduced transparency, high contrast, text size, and light or dark mode.
- **Mobile first.** Every page works at 360 px width and scales up with Bootstrap's grid. Seat states and statuses are always labeled in text, not only color.

Apple's eight design principles, and how Cenebook applies each:

| Principle | How Cenebook applies it |
| --- | --- |
| Purpose | Only the booking path: browse, pick, pay, ticket. Anything in the PRD's exclusion list stays out. |
| Agency | "Change seats" and "Back" are available at every step; holds can be released at any time. Confirmation dialogs appear only for destructive actions (cancel booking, cancel show), never for routine steps. |
| Responsibility | The payment screen states plainly that payment is simulated. Cancellation rules and the refund amount are shown before the user confirms. The hold countdown is calm, not alarming. |
| Familiarity | Standard patterns: seat grid with the screen at the top, ticket cards, bottom sheets on mobile. The same component looks and behaves the same everywhere; the primary action is always in the same place. |
| Flexibility | Phones to desktops; light and dark; the user's text size; touch, mouse, keyboard, and screen reader. The seat map works by tap, arrow keys, and pinch. |
| Simplicity | The common path first, advanced admin filters one level deeper. Add context only where it simplifies (time left on a hold, seats left on a showtime). |
| Craft | A 4 px / 8 px spacing grid, defined motion values, no layout shifts, and every state designed: loading, empty, error. |
| Delight | A calm, confident booking, with one restrained moment of reward on the confirmation page. |

## 3. Site Map

```
Home (/)
├── Login / Register
├── Movie Details
│     └── Seat Selection (login required)
│            └── Booking Summary
│                   └── Booking Confirmation
├── My Bookings
│     └── Ticket Details / Cancel
└── Admin (admin role only)
      ├── Dashboard
      ├── Movies
      ├── Theatres and Screens
      ├── Shows
      └── Bookings
```

## 4. Global Components

### 4.1 Navigation bar (all pages)

```
+--------------------------------------------------------------+
| CENEBOOK     [ Search movies...        ] [Q]   My Bookings   |
|                                              Hi, Asha  Logout|
+--------------------------------------------------------------+
```

- The bar is a translucent material (see Section 12), sticky at the top, with content scrolling underneath it. There is no hard divider line; a soft fade appears only while content is scrolled beneath the bar.
- Logged out: shows **Login** and **Register** instead of the user menu. Admin users also see an **Admin** link.
- On mobile, the bar compacts to the logo, a search icon, and a menu button. The menu opens as a sheet that grows from the button and closes back along the same path.

### 4.2 Footer

```
+--------------------------------------------------------------+
|  (c) 2026 Cenebook · Simulated payments (demo project)       |
+--------------------------------------------------------------+
```

### 4.3 Messages

Success, warning, and error messages appear as Bootstrap alerts directly under the navigation bar (green, yellow, red) and are dismissible. Form errors appear under the relevant field.

### 4.4 Seat state legend (used on Seat Selection)

| State | Appearance | Symbol | Clickable |
| --- | --- | --- | --- |
| Available | White with grey border | `[ ]` | Yes |
| Selected (by you) | Solid blue with a tick | `[✓]` | Yes (to deselect) |
| Held by someone else | Yellow, striped | `[~]` | No |
| Booked | Dark grey with an X | `[X]` | No |

## 5. Public Pages

### 5.1 Home

**Purpose:** browse and search currently showing movies.

```
+--------------------------------------------------------------+
| [Navbar]                                                     |
+--------------------------------------------------------------+
| Now Showing                                                  |
| [ Search by title...                       ] [Search]        |
|                                                              |
| +--------+  +--------+  +--------+  +--------+               |
| | poster |  | poster |  | poster |  | poster |               |
| |        |  |        |  |        |  |        |               |
| +--------+  +--------+  +--------+  +--------+               |
| Title       Title       Title       Title                    |
| Action·Eng  Drama·Hin   Comedy·Mar  Thriller·Eng             |
| [Book now]  [Book now]  [Book now]  [Book now]               |
|                                                              |
|                  « 1 2 3 »  (pagination)                     |
+--------------------------------------------------------------+
```

- Grid: 1 column on phones, 2 on tablets, 4 on desktop.
- Each card shows poster, title, genre, and language; the whole card links to Movie Details.
- Search filters by title (partial, case-insensitive). If nothing matches: "No movies found for 'xyz'. Try another title."
- Pagination after 12 movies.

### 5.2 Register

```
+--------------------------------------------------------------+
|                 Create your account                          |
|                                                              |
|   Name      [______________________]                         |
|   Email     [______________________]                         |
|   Password  [______________________]  (min 8 characters)     |
|   Confirm   [______________________]                         |
|                                                              |
|                  [ Register ]                                |
|          Already have an account? Login                      |
+--------------------------------------------------------------+
```

- Inline validation: invalid email, password too short, passwords do not match, email already registered.
- On success: user is logged in and sent to Home with a welcome message.

### 5.3 Login

```
+--------------------------------------------------------------+
|                       Login                                  |
|                                                              |
|   Email     [______________________]                         |
|   Password  [______________________]                         |
|                                                              |
|                  [ Login ]                                   |
|          New here? Create an account                         |
+--------------------------------------------------------------+
```

- Error message is generic: "Invalid email or password."
- After too many failed attempts: "Too many attempts. Try again in a few minutes."
- After login, user returns to the page they originally requested (`?next=`).

### 5.4 Movie Details (includes Show Selection)

**Purpose:** show movie information and let the user choose a theatre, date, and showtime.

```
+--------------------------------------------------------------+
| [Navbar]                                                     |
+--------------------------------------------------------------+
| +----------+   Movie Title                                   |
| |          |   Action · English · 2h 15m · Released 12 Oct   |
| |  poster  |                                                 |
| |          |   Description text goes here. It can run over   |
| +----------+   several lines...                              |
|                                                              |
| Select a date                                                |
| [Sat 24] [Sun 25] [Mon 26] [Tue 27] [Wed 28]  ->            |
|                                                              |
| PVR Pune - Kothrud                                           |
|   [10:00 AM  Rs 200] [01:30 PM  Rs 250] [07:00 PM  Rs 300]   |
|                                                              |
| INOX Pune - Camp                                             |
|   [09:45 AM  Rs 180] [06:15 PM  Rs 280] [10:00 PM  SOLD OUT] |
+--------------------------------------------------------------+
```

- Date chips show only dates that have upcoming shows; the first is selected by default.
- Each showtime button shows time and price. Availability hint: green (plenty), orange (filling fast, under 20% left), grey and disabled (sold out, started, or past the booking cut-off).
- Clicking an enabled showtime opens Seat Selection (login required).
- If there are no upcoming shows: "No shows are scheduled for this movie right now."

## 6. Booking Pages (login required)

### 6.1 Seat Selection

```
+--------------------------------------------------------------+
| Movie Title · PVR Pune - Kothrud · Screen 2                  |
| Sat 24 Oct · 07:00 PM · Rs 300 per seat                      |
+--------------------------------------------------------------+
|                  ________ SCREEN ________                    |
|                                                              |
|     A   [ ][ ][ ][X][X][ ][ ][ ][ ][ ]                       |
|     B   [ ][ ][✓][✓][ ][ ][~][~][ ][ ]                       |
|     C   [ ][ ][ ][ ][ ][ ][ ][ ][ ][ ]                       |
|     D   [X][X][ ][ ][ ][ ][ ][ ][ ][ ]                       |
|     E   [ ][ ][ ][ ][ ][ ][ ][ ][ ][ ]                       |
|                                                              |
|   [ ] Available  [✓] Selected  [~] Held  [X] Booked          |
+--------------------------------------------------------------+
| Selected: B3, B4   (2 seats)         Total: Rs 600           |
|                                  [ Continue to summary ]     |
+--------------------------------------------------------------+
```

- The seat map is drawn from `GET /api/shows/<id>/seats/` and refreshes every 10 seconds. Seats that change state fade between states over 200 ms.
- **Press feedback is instant:** a seat shrinks slightly on pointer-down and commits the selection on release. Each seat has a minimum 44 × 44 px touch target, using padding around the visible seat.
- Clicking an available seat selects it; clicking again deselects it. Maximum 8 seats; the 9th click shows "You can select up to 8 seats."
- The total in the bar updates immediately, with no count-up animation or delay.
- **Mobile pan and zoom:** the map starts zoomed to fit; the user drags to pan and pinches to zoom (1× to 2.5×). The map tracks the fingers 1:1, continues with the release velocity, and resists progressively past its edges (rubber-banding). The user can grab it again mid-motion. Double-tap zoom is not used, to avoid delaying single taps; **+** and **−** buttons are provided instead.
- **Selection bar:** the bottom bar is a translucent sheet with two snap points. Collapsed it shows the total and **Continue**; dragged up it lists the chosen seats. It follows the finger, and a flick projects to the nearer snap point.
- The Continue button is disabled until at least one seat is selected. It places a hold on the seats and then opens the summary.
- If a seat was taken meanwhile: "Seat B4 is no longer available. Please choose another." The affected seats pulse once, the map refreshes, and the selection is trimmed. The message is announced to screen readers.

### 6.2 Booking Summary

```
+--------------------------------------------------------------+
| Review your booking                     Seats held for 04:32 |
+--------------------------------------------------------------+
| Movie     Movie Title                                        |
| Theatre   PVR Pune - Kothrud, Screen 2                       |
| Date      Sat 24 Oct 2026                                    |
| Time      07:00 PM                                           |
| Seats     B3, B4                                             |
|--------------------------------------------------------------|
| 2 seats x Rs 300                                  Rs 600     |
| Total                                             Rs 600     |
+--------------------------------------------------------------+
| Payment (simulated): no real money will be charged.          |
|                                                              |
|     [ Change seats ]                [ Pay Rs 600 ]           |
+--------------------------------------------------------------+
```

- The countdown starts at 5:00. At 1:00 it turns red. At 0:00 a message appears ("Your hold expired") with a button back to seat selection.
- **Pay** disables itself after the first click to prevent duplicate submissions and shows a spinner.
- If payment fails (simulated failure): "Payment failed. Your seats are still held. Try again." while the hold lasts.

### 6.3 Booking Confirmation

```
+--------------------------------------------------------------+
|  ✓ Booking confirmed!                                        |
|  Booking ID: CNB-20261024-A7K2                               |
+--------------------------------------------------------------+
|  Movie Title                                                 |
|  PVR Pune - Kothrud · Screen 2                               |
|  Sat 24 Oct 2026 · 07:00 PM                                  |
|  Seats: B3, B4                                               |
|  Amount paid: Rs 600                                         |
|  Status: Confirmed · Payment: Paid                           |
+--------------------------------------------------------------+
|        [ View My Bookings ]      [ Back to Home ]            |
+--------------------------------------------------------------+
```

- The same layout is used for "Ticket Details" opened from My Bookings.
- A Print button uses the browser's print stylesheet.

### 6.4 My Bookings

```
+--------------------------------------------------------------+
| My Bookings                                                  |
| [ Upcoming (2) ]  [ Past (5) ]                               |
+--------------------------------------------------------------+
| CNB-20261024-A7K2                           [Confirmed]      |
| Movie Title · PVR Pune - Kothrud                             |
| Sat 24 Oct · 07:00 PM · Seats B3, B4 · Rs 600                |
|                           [ View ticket ]  [ Cancel ]        |
|--------------------------------------------------------------|
| CNB-20261020-K9M1                           [Cancelled]      |
| Another Movie · INOX Pune - Camp                             |
| Tue 20 Oct · 06:15 PM · Seats D5 · Rs 280 (refunded)         |
|                           [ View ticket ]                    |
+--------------------------------------------------------------+
```

- **Cancel** appears only if the show is more than 2 hours away. Clicking it opens a confirmation modal: "Cancel booking CNB-...? Rs 600 will be refunded (simulated). This cannot be undone."
- Status badges: Confirmed (green), Cancelled (grey).
- Empty state: "You have no upcoming bookings. Browse movies."

## 7. Admin Pages (admin role only)

Admin pages share a sidebar layout. Non-admin users who open these URLs see a 403 page.

```
+-----------+--------------------------------------------------+
| ADMIN     |  (page content)                                  |
|-----------|                                                  |
| Dashboard |                                                  |
| Movies    |                                                  |
| Theatres  |                                                  |
| Shows     |                                                  |
| Bookings  |                                                  |
+-----------+--------------------------------------------------+
```

On mobile the sidebar becomes a top drop-down.

### 7.1 Admin Dashboard

```
+--------------------------------------------------------------+
| Dashboard                                                    |
| +-----------+ +-----------+ +-----------+ +-----------+      |
| | Movies    | | Shows     | | Bookings  | | Revenue   |      |
| |   12      | | upcoming  | | today     | | today     |      |
| |           | |   48      | |   23      | | Rs 14,200 |      |
| +-----------+ +-----------+ +-----------+ +-----------+      |
|                                                              |
| Recent bookings                                              |
| ID               User        Show             Status         |
| CNB-...A7K2      Asha        Movie · 7 PM     Confirmed      |
| ...                                                          |
+--------------------------------------------------------------+
```

Simple counts only; no charts in the MVP.

### 7.2 Admin: Movies

```
+--------------------------------------------------------------+
| Movies                                        [ + Add movie ]|
| [ Search title... ]   Status: [All v]                        |
+--------------------------------------------------------------+
| Poster | Title        | Language | Status      | Actions     |
| [img]  | Movie One    | English  | Now showing | Edit Archive|
| [img]  | Movie Two    | Hindi    | Archived    | Edit Restore|
+--------------------------------------------------------------+
```

**Add / Edit form fields:** title, description, genre, language, duration (minutes), release date, poster URL (with preview), status. Archive asks for confirmation: "Archived movies are hidden from users. Existing bookings are kept."

### 7.3 Admin: Theatres and Screens

```
+--------------------------------------------------------------+
| Theatres                                    [ + Add theatre ]|
+--------------------------------------------------------------+
| PVR Pune - Kothrud   (Asia/Kolkata)   3 screens   [Edit]     |
|   Screen 1  8 rows x 12 seats                    [Edit]      |
|   Screen 2  6 rows x 10 seats                    [Edit]      |
|   [ + Add screen ]                                           |
+--------------------------------------------------------------+
```

**Theatre form:** name, location, time zone. **Screen form:** name, number of rows, seats per row; the system generates seats such as A1 to F10. Seat layout is locked once a show on that screen has bookings.

### 7.4 Admin: Shows

```
+--------------------------------------------------------------+
| Shows                                           [ + Add show]|
| Filter: Movie [All v] Theatre [All v] Date [____]            |
+--------------------------------------------------------------+
| Movie     | Theatre/Screen   | Start            | Price | ... |
| Movie One | PVR · Screen 2   | 24 Oct 07:00 PM  | 300   | Edit Cancel|
+--------------------------------------------------------------+
```

**Show form:** movie, theatre, screen, date, start time, price. The end time is calculated from the movie duration plus a cleaning buffer. Saving fails with a clear message if the show overlaps another on the same screen. **Cancel show** warns: "This will cancel N bookings and refund them (simulated)."

### 7.5 Admin: Bookings

```
+--------------------------------------------------------------+
| Bookings                                                     |
| Movie [All v] Theatre [All v] Date [____] Status [All v]     |
+--------------------------------------------------------------+
| Booking ID    | User  | Movie  | Show time | Seats | Amount | Status    |
| CNB-..A7K2    | Asha  | Movie  | 24 Oct 7PM| B3,B4 | 600    | Confirmed |
+--------------------------------------------------------------+
|                     « 1 2 3 »                               |
+--------------------------------------------------------------+
```

Read-only list in the MVP, with pagination at 25 rows.

## 8. Error and Empty States

| Page | Message | Action |
| --- | --- | --- |
| 404 | "We couldn't find that page." | Back to Home |
| 403 | "You don't have permission to view this page." | Back to Home |
| 500 | "Something went wrong. Please try again." | Back to Home |
| Hold expired | "Your seats were released." | Choose seats again |
| Show started or closed | "Booking for this show is closed." | Back to movie |
| Network error during booking | "Connection problem. Check My Bookings before retrying." | Open My Bookings |

## 9. Responsive Behavior

| Element | Phone (<576 px) | Tablet (576–991 px) | Desktop (≥992 px) |
| --- | --- | --- | --- |
| Movie grid | 1 column | 2 columns | 4 columns |
| Navigation | Hamburger menu | Hamburger menu | Full bar |
| Seat map | Horizontal scroll, fixed total bar | Fits width | Fits width |
| Showtimes | Wrapped buttons | Wrapped buttons | Single row per theatre |
| Admin sidebar | Top drop-down | Collapsible sidebar | Fixed sidebar |
| Tables | Horizontal scroll or card view | Table | Table |

## 10. Visual Style Guide (Starter)

- **Framework:** Bootstrap 5 for grid, forms, and components, restyled with CSS variables (radius, color, type) so it does not look like default Bootstrap. Avoid heavy borders and default shadows.
- **Color:** restrained, one accent color, with light and dark values for every token.

| Token | Light | Dark |
| --- | --- | --- |
| Accent (primary actions, selected seats) | `#0071E3` | `#2997FF` |
| Success | `#248A3D` | `#30D158` |
| Warning | `#B25000` | `#FF9F0A` |
| Danger | `#D70015` | `#FF453A` |
| Text | `#1D1D1F` | `#F5F5F7` |
| Secondary text | `#6E6E73` | `#A1A1A6` |
| Background | `#FFFFFF` | `#000000` |
| Grouped surface (cards) | `#F5F5F7` | `#1C1C1E` |

- **Contrast:** verify every text and background pair reaches at least 4.5:1 (3:1 for large text).
- **Typography:** the platform system font, with size-specific tracking and leading (Section 13).
- **Shape:** 12 px radius on cards, 10 px on buttons and inputs, 20 px on top corners of sheets.
- **Elevation:** soft, layered shadows; larger surfaces get deeper shadows and stronger blur.
- **Spacing:** 4 px base unit; use steps of 8 px (`p-2`, `p-3`, `mb-4` mapped to the scale).
- **Buttons:** one filled primary button per page; secondary actions are tinted or plain. All buttons give pressed feedback instantly.
- **Icons:** one consistent line-icon set (Bootstrap Icons).

## 11. Motion and Interaction

Motion in Cenebook is behavior, not decoration. It confirms input, explains where things go, and never makes the user wait.

### 11.1 Rules

1. **Respond on pointer-down.** Show the pressed state the moment a finger or mouse goes down; commit on release. Remove debounces and artificial timers from the input path.
2. **Track 1:1 while dragging.** Content follows the pointer from where it was grabbed, using Pointer Events with `setPointerCapture`. Keep the last few positions with timestamps to compute release velocity.
3. **Everything is interruptible.** Never lock input during a transition. When the user grabs a moving element, read its current on-screen position and animate from there, never from the logical target.
4. **Use springs for anything touchable.** Do not use CSS transitions or keyframes for gesture-driven elements, since they cannot be grabbed and reversed smoothly. CSS transitions remain fine for non-gesture changes such as color and opacity.
5. **Hand off velocity.** When a gesture ends, start the spring with the release velocity so there is no seam between dragging and animating.
6. **Project momentum.** Choose the snap target from where the gesture is heading, not where it stopped.
7. **Soft boundaries.** Resist progressively at edges instead of stopping hard.
8. **Animate only `transform` and `opacity`**, and add `will-change` only just before motion begins.
9. **Decide direction after about 10 px of movement**, then track 1:1. Run candidate gestures (pan, pinch, sheet drag, tap) in parallel and cancel the losers once intent is clear.

### 11.2 Spring values

Two parameters describe every spring: **damping ratio** (1.0 = no overshoot; below 1.0 overshoots) and **response** (seconds to reach the target; lower is snappier).

| Use | Damping | Response | Motion library setting |
| --- | --- | --- | --- |
| Move or reposition (map snap-back, sheet settling without a flick) | 1.0 | 0.4 s | `bounce: 0, duration: 0.4` |
| Sheet or drawer released after a flick | 0.8 | 0.3 s | `bounce: 0.2, duration: 0.3` |
| Modal, popover, or menu appearing | 1.0 | 0.3 s | `bounce: 0, duration: 0.3` |
| Press and release feedback | n/a | 100 ms | CSS `ease-out` on `transform` |
| Seat state change from a refresh | n/a | 200 ms | CSS opacity and color transition |

Default to damping 1.0. Add bounce only when the gesture itself carried momentum (a flick or throw); overshoot on something that merely appeared feels wrong.

### 11.3 Behavior by page

| Element | Behavior |
| --- | --- |
| Any button or card | Scales to 0.97 on press over 100 ms, restores on release; a drag away cancels the press |
| Movie card to Movie Details | The poster travels between pages (shared element transition, 11.4) |
| Date chips | Horizontal scroll with native momentum and edge bounce; `scroll-snap-type: x proximity` |
| Showtime button | Instant pressed state; navigation uses the page transition |
| Seat | Shrinks to 0.92 on pointer-down; fill changes on selection; total updates at once |
| Seat map (mobile) | Pan and pinch tracked 1:1; momentum projected on release; rubber-band at edges; interruptible |
| Selection sheet (mobile) | Snap points collapsed and expanded; follows the finger; flick projects to the nearest snap; spring 0.8 / 0.3 s |
| Hold countdown | Text updates each second with no motion; turns red at 1:00 over 300 ms; on expiry the message sheet springs in (1.0 / 0.4 s) |
| Pay button | Pressed state is instant; the spinner replaces the label without changing the button's width |
| Cancel booking (desktop) | Dialog grows from the Cancel button (`transform-origin` at the trigger), background dims; closes back to the same point |
| Cancel booking (mobile) | Bottom sheet; drag down to dismiss; exit retraces the entry |
| Confirmation | The check mark draws once in about 400 ms; no confetti or looping animation |
| Admin pages | Minimal motion: pressed states, dialogs, and a sidebar drawer on mobile that follows the finger |

### 11.4 Page transitions

Cenebook is a multi-page Django app, so page transitions use the browser's View Transitions API as progressive enhancement.

- Enable cross-document transitions with `@view-transition { navigation: auto; }`. Browsers without support navigate instantly, which is acceptable.
- **Symmetric paths:** moving forward in the booking flow (movie, seats, summary, confirmation) slides the new page in from the right; going back returns it to the right.
- **Shared element:** give the poster on the movie card and the poster on the details page the same `view-transition-name` (for example `poster-7`) so the poster appears to travel.
- With reduced motion, replace slides with a 200 ms cross-fade (Section 14).

### 11.5 Feedback beyond motion

Sound is not used. Haptics (the Vibration API, where supported) are reserved for meaningful moments and must fire on the same frame as the visual change:

| Moment | Haptic | Visual |
| --- | --- | --- |
| Booking confirmed | `navigator.vibrate(10)` | Check mark draws |
| Seat conflict or payment failure | `navigator.vibrate([10, 40, 10])` | Message appears, seats pulse |

No haptic on ordinary taps. Respect reduced motion by skipping haptics as well.

### 11.6 Reference code

```javascript
import { animate } from "motion";   // pin an exact version; ship it as a local static file

// Default: critically damped, no overshoot
animate(panel, { y: 0 }, { type: "spring", bounce: 0, duration: 0.4 });

// After a flick: a little bounce, with the release velocity handed off
animate(sheet, { y: target }, { type: "spring", bounce: 0.2, duration: 0.3, velocity: releaseVelocity });

// Where will this flick end up? (px/s in, px out)
function project(velocity, rate = 0.998) {
  return (velocity / 1000) * rate / (1 - rate);
}
const snap = nearest(snapPoints, y + project(releaseVelocity));

// Resist past an edge: the further out, the less the content follows
function rubberband(overshoot, dimension, c = 0.55) {
  return (overshoot * dimension * c) / (dimension + c * Math.abs(overshoot));
}
```

```css
/* Pressed feedback lives on the press, and it is instant */
.btn:active, .movie-card:active { transform: scale(0.97); transition: transform 100ms ease-out; }

@view-transition { navigation: auto; }
.poster { view-transition-name: var(--poster-name); }
```

## 12. Materials and Depth

Translucent materials give structure without taking attention. Content scrolls beneath floating bars instead of an opaque strip reserving space.

| Surface | Material | Notes |
| --- | --- | --- |
| Top navigation bar | Light translucent: background at 70% opacity, `blur(20px) saturate(180%)` | No divider line; soft edge fade while content scrolls beneath |
| Seat selection sheet | Thicker: stronger blur (30 px) and a deeper shadow than the nav bar | Bigger surfaces read as thicker |
| Modal dialogs | Solid surface with a dimming scrim (35% black) | The page behind scales to 0.98 and dims, signalling a task that needs focus |
| Admin sidebar | Heavier, darker material | Separates a structural region |
| Alerts and toasts | Solid tinted background | Legibility matters more than depth |
| Movie cards, ticket cards | Solid grouped surface | Content surfaces are not translucent |

**Rules**

- Never stack a translucent surface on another translucent surface.
- Text on a translucent surface uses full-contrast text color at weight 500 or higher, never flat gray. Put color on solid layers (badges, buttons), not on the translucent foreground.
- A modal task uses a scrim; a parallel, non-blocking panel does not.
- When a glass surface appears, animate blur and scale together so it reads as a material arriving, not a plain fade.

```css
.app-bar {
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(20px) saturate(180%);
  border-top: 1px solid rgba(255, 255, 255, 0.4);   /* light catching the edge */
}
@media (prefers-color-scheme: dark) { .app-bar { background: rgba(28, 28, 30, 0.7); border-top-color: rgba(255, 255, 255, 0.12); } }
@supports not (backdrop-filter: blur(1px)) { .app-bar { background: var(--surface); } }
```

## 13. Typography

Use the platform system font: `font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`. It already carries optical sizing and legibility tuning. Tracking and leading change with size: large text is tightened, small text is opened slightly.

| Role | Where | Size | Weight | Line height | Tracking |
| --- | --- | --- | --- | --- | --- |
| Display | Movie title on details | `clamp(2rem, 5vw, 3.25rem)` | 700 | 1.05 | -0.025em |
| Title | Page headings | `clamp(1.5rem, 3vw, 2rem)` | 600 | 1.15 | -0.015em |
| Headline | Card titles, section headings | 1.125rem | 600 | 1.25 | -0.01em |
| Body | Descriptions, forms | 1rem | 400 | 1.5 | 0 |
| Secondary | Helper text | 0.9375rem | 400 | 1.45 | 0 |
| Caption | Genre and language, seat labels, badges | 0.8125rem | 500 | 1.4 | +0.01em |

**Rules**

- Size in `rem` and spacing in `rem` or Bootstrap's scale, so the layout scales when the user raises their text size.
- Build hierarchy from weight, size, and leading together, not size alone.
- Set `font-optical-sizing: auto` on headings.
- Text over translucent surfaces follows the materials rules in Section 12.

## 14. Reduced Motion, Transparency, and Contrast

Reduced motion means gentler feedback, not no feedback. Respond to three independent settings.

| Setting | Behavior |
| --- | --- |
| `prefers-reduced-motion: reduce` | Replace slides, springs, and shared-element travel with a 200 ms cross-fade or an instant change. Drop bounce and overshoot. Keep color and opacity changes that aid comprehension. Skip haptics. |
| `prefers-reduced-transparency: reduce` | Make materials solid: raise opacity to 100% and remove blur. |
| `prefers-contrast: more` | Near-solid backgrounds with a defined, contrasting 1 px border; no gray secondary text. |

Also:

- No full-screen moving backgrounds, no looping animations, and no abrupt brightness jumps (ease light and dark theme changes over 300 ms).
- Seat states keep their text labels and patterns in every mode.
- Keyboard: arrow keys move between seats, Space or Enter toggles one, and focus is always visible.

```css
@media (prefers-reduced-motion: reduce) {
  .sheet, .dialog { transform: none !important; transition: opacity 200ms ease; }
  ::view-transition-old(root), ::view-transition-new(root) { animation-duration: 200ms; animation-name: fade; }
}
@media (prefers-reduced-transparency: reduce) { .app-bar, .sheet { background: var(--surface); backdrop-filter: none; } }
@media (prefers-contrast: more) { .app-bar, .sheet, .card { border: 1px solid var(--text); } }
```

## 15. UI Quality Checklist

Check each page against this list before it is considered done.

- [ ] Pressed feedback appears on pointer-down with no delay.
- [ ] Dragged content stays under the finger from the point it was grabbed.
- [ ] Any animation can be grabbed and reversed mid-flight without a jump.
- [ ] Release velocity carries into the settle animation; flicks land on the projected snap point.
- [ ] Elements leave along the path they arrived and grow from their trigger.
- [ ] Only `transform` and `opacity` are animated; no layout shift during motion.
- [ ] No translucent surface sits on another; text on materials is legible.
- [ ] Type uses the size-specific tracking and leading in Section 13 and scales with the user's text size.
- [ ] Reduced motion, reduced transparency, and high contrast each have a tested fallback.
- [ ] Every state is designed: loading, empty, error, expired hold, sold out.
- [ ] Haptics fire only for confirmation and failure, on the same frame as the visual.
- [ ] Works at 360 px width, in light and dark mode, and by keyboard.

## 16. Page-to-Template Mapping

| Page | Django template | Main script |
| --- | --- | --- |
| Home | `movies/home.html` | none |
| Register / Login | `accounts/register.html`, `accounts/login.html` | form validation |
| Movie Details | `movies/detail.html` | `showtimes.js` (date switching) |
| Seat Selection | `bookings/seats.html` | `seatmap.js` |
| Booking Summary | `bookings/summary.html` | `countdown.js`, `pay.js` |
| Confirmation / Ticket | `bookings/confirmation.html` | none |
| My Bookings | `bookings/my_bookings.html` | `cancel.js` |
| Admin pages | `manage/*.html` | minimal |

Templates extend `base.html` (navbar, messages, footer) and the admin templates extend `manage/base.html` (sidebar).

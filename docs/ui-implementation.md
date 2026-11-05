# UI implementation

## Visual system

The implementation follows the supplied responsive V2 design reference:

- Forest `#102C22`
- Secondary green `#214D39`
- Action green `#20734D`
- Leaf accent `#B8DB74`
- Canvas `#F6F9F4`
- Card `#FFFFFF`
- Primary text `#172B23`
- Muted text `#718479`
- Warning `#F0A347`
- Danger `#DC6464`

Lato is the preferred typeface with a system fallback. The interface uses an 8 px-derived spacing rhythm, 12-24 px radii, restrained shadows, 44 px minimum controls, visible focus outlines, and text/icon labels for semantic states.

## Public layout

The public shell keeps weather and history available without authentication. Desktop uses a horizontal navbar; mobile uses an accessible expandable menu. The homepage presents the exact product promise, transparent weather state, historical chart, feature cards, workflow, and data-trust messaging.

## Authenticated layout

Desktop at 1200 px and wider:

- fixed forest sidebar;
- page title and global actions in the top navbar;
- AI Assistant, notification bell, and profile avatar at top-right;
- POST Logout pinned to the bottom of the sidebar;
- no AI/Profile/Settings links in role sidebars.

Tablet from 768-1199 px:

- no permanent sidebar;
- Farmer dashboard shows a reusable three-column feature grid;
- top-right AI, notifications, and profile remain.

Mobile below 768 px:

- no permanent sidebar;
- all ten Farmer destinations appear in a two-column feature grid;
- feature pages stack in one column;
- compact top navbar and four-item bottom shortcut bar;
- Logout remains in the avatar menu.

The CSS keeps two Farmer feature columns at 375 px and 390 px without reducing text below readable sizes.

## Shared components

- brand and navigation
- messages and verification banner
- role sidebars
- Farmer feature grid
- metric and data-state cards
- tables and responsive wrappers
- form cards, filters, pagination, timelines, empty states
- notification and profile menus
- AI drawer, suggested questions, loading/error messages
- source/freshness/status labels

## Accessibility

- A skip link is the first focusable control.
- Landmarks and navigation labels identify page regions.
- Controls use native buttons/forms/details where practical.
- Focus outlines use the accent color and are never removed without replacement.
- Charts are accompanied by visible labels, values, units, and interpretation.
- Risk is communicated with text/badges, not color alone.
- Reduced-motion preferences disable nonessential transitions.
- Form inputs have labels, server-side errors, and touch-sized controls.
- Menus and the AI drawer close with Escape; profile menus use native disclosure behavior.

## JavaScript

Vanilla JavaScript only enhances navigation, active states, the AI drawer, and Chart.js rendering. Core workflows remain server-rendered forms and links. The AI fetch call uses the Django CSRF token and never includes an API credential.

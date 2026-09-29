"""Look and feel of the web app: a dark "terminal" theme with rounded controls.

`THEME`, `CSS` and `FORCE_DARK_JS` are passed to `demo.launch()` in app.py.
"""
import gradio as gr

# ---------- Palette ----------
BG = "#0a0e14"              # page background
SURFACE = "#0f141b"         # cards, sidebar
SURFACE_RAISED = "#151c26"  # table headers, inline code
INPUT_BG = "#080b10"        # text fields, terminal panel
BORDER = "#1e2835"
BORDER_STRONG = "#2c3a4d"
TEXT = "#d4dbe6"
MUTED = "#7d8a9e"
GREEN = "#3ee08f"           # main accent (phosphor green)
CYAN = "#56d4f0"
VIOLET = "#a78bfa"
AMBER = "#f5c451"


def dark_everywhere(**variables) -> dict:
    """Give each theme variable the same value in light and dark mode, so the app always looks dark.

    Some variables (like sizes and radii) have no separate dark version, so those are set once.
    """
    has_dark = set(vars(gr.themes.Base()))
    return {
        **variables,
        **{f"{name}_dark": value for name, value in variables.items() if f"{name}_dark" in has_dark},
    }


THEME = gr.themes.Base(
    primary_hue=gr.themes.colors.emerald,
    secondary_hue=gr.themes.colors.violet,
    neutral_hue=gr.themes.colors.slate,
    radius_size=gr.themes.sizes.radius_lg,
    font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "system-ui", "sans-serif"],
    font_mono=[gr.themes.GoogleFont("JetBrains Mono"), "ui-monospace", "Consolas", "monospace"],
).set(**dark_everywhere(
    # Page and text
    body_background_fill=(
        f"radial-gradient(900px 500px at 0% -10%, rgba(167,139,250,0.10), transparent 60%),"
        f" radial-gradient(900px 500px at 100% 0%, rgba(62,224,143,0.07), transparent 60%), {BG}"
    ),
    body_text_color=TEXT,
    body_text_color_subdued=MUTED,
    background_fill_primary=SURFACE,
    background_fill_secondary=BG,
    border_color_primary=BORDER,
    border_color_accent=GREEN,
    color_accent=GREEN,
    color_accent_soft="rgba(62,224,143,0.12)",
    link_text_color=CYAN,
    link_text_color_hover=GREEN,
    link_text_color_active=GREEN,
    link_text_color_visited=VIOLET,
    code_background_fill=SURFACE_RAISED,
    loader_color=GREEN,
    # Blocks and panels
    block_background_fill=SURFACE,
    block_border_color=BORDER,
    block_border_width="1px",
    block_radius="18px",
    block_shadow="none",
    block_label_background_fill="transparent",
    block_label_border_color="transparent",
    block_label_text_color=MUTED,
    block_title_text_color=TEXT,
    block_info_text_color=MUTED,
    panel_background_fill=SURFACE,
    panel_border_color=BORDER,
    # Text fields
    input_background_fill=INPUT_BG,
    input_background_fill_focus=INPUT_BG,
    input_background_fill_hover=INPUT_BG,
    input_border_color=BORDER_STRONG,
    input_border_color_hover=BORDER_STRONG,
    input_border_color_focus=GREEN,
    input_shadow="none",
    input_shadow_focus="0 0 0 3px rgba(62,224,143,0.18)",
    input_placeholder_color="#4f5b6d",
    input_radius="14px",
    # Buttons: pill shaped, green-to-cyan gradient for the main one
    button_large_radius="999px",
    button_medium_radius="999px",
    button_small_radius="999px",
    button_primary_background_fill=f"linear-gradient(135deg, {GREEN}, {CYAN})",
    button_primary_background_fill_hover=f"linear-gradient(135deg, #5ff0a6, #7ee0f5)",
    button_primary_border_color="transparent",
    button_primary_border_color_hover="transparent",
    button_primary_text_color="#04110b",
    button_primary_text_color_hover="#04110b",
    button_primary_shadow="0 6px 24px rgba(62,224,143,0.22)",
    button_primary_shadow_hover="0 8px 30px rgba(62,224,143,0.35)",
    button_secondary_background_fill=SURFACE_RAISED,
    button_secondary_background_fill_hover=BORDER_STRONG,
    button_secondary_border_color=BORDER_STRONG,
    button_secondary_text_color=TEXT,
    # Tables inside the result cards
    table_border_color=BORDER,
    table_even_background_fill=INPUT_BG,
    table_odd_background_fill=INPUT_BG,
    table_text_color=TEXT,
    table_radius="12px",
))

CSS = f"""
/* Fixed page width. Without `width: 100%` the page would size itself to its content, so it grew wider when
   results arrived and Gradio's room-for-the-sidebar calculation went stale, letting the sidebar cover the search bar. */
html {{ scrollbar-gutter: stable; }}  /* keep the page from shifting sideways when the scrollbar appears */
.gradio-container {{ width: 100% !important; max-width: 1040px !important; margin: 0 auto !important; }}

/* Headings in monospace for the developer look */
.gradio-container h1, .gradio-container h2, .gradio-container h3 {{
    font-family: var(--font-mono) !important;
    letter-spacing: -0.01em;
    color: {TEXT} !important;
}}

/* ---------- Header ---------- */
.hero {{ padding: 28px 4px 8px; }}
.hero-badge {{
    display: inline-flex; align-items: center; gap: 8px;
    padding: 5px 12px; border-radius: 999px;
    border: 1px solid {BORDER_STRONG}; background: {SURFACE};
    font-family: var(--font-mono); font-size: 12px; color: {MUTED};
}}
.hero-badge .dot {{
    width: 8px; height: 8px; border-radius: 50%; background: {GREEN};
    box-shadow: 0 0 10px {GREEN};
}}
.hero h1 {{ font-size: 2.1rem !important; margin: 18px 0 8px !important; }}
.hero h1 .prompt {{ color: {GREEN}; }}
.hero p {{ color: {MUTED}; font-size: 1.02rem; max-width: 680px; margin: 0; }}

/* ---------- Search bar ---------- */
.search-bar {{
    background: {SURFACE}; border: 1px solid {BORDER};
    border-radius: 24px; padding: 14px 16px !important;
    align-items: flex-end !important;
}}
.search-bar .form, .search-bar .block {{
    background: transparent !important; border: none !important; box-shadow: none !important;
}}
.search-bar .block {{ padding: 0 2px !important; }}
.search-bar textarea, .search-bar input {{ font-size: 15px !important; padding: 12px 16px !important; }}
.search-bar button {{ min-height: 48px; font-family: var(--font-mono); font-weight: 600; letter-spacing: 0.02em; }}
button {{ transition: transform 0.15s ease, box-shadow 0.2s ease, filter 0.2s ease !important; }}
button:hover:not(:disabled) {{ transform: translateY(-1px); }}
button:disabled {{ filter: grayscale(0.6) brightness(0.8); cursor: progress; }}

/* ---------- Progress log, styled like a terminal window ---------- */
.block.terminal {{
    background: {INPUT_BG} !important; border: 1px solid {BORDER} !important;
    border-radius: 18px !important; padding: 0 !important; overflow: hidden;
}}
.block.terminal::before {{
    content: "●  ●  ●     agent.log";
    display: block; padding: 10px 16px;
    background: {SURFACE}; border-bottom: 1px solid {BORDER};
    font-family: var(--font-mono); font-size: 12px; color: {MUTED}; letter-spacing: 0.04em;
}}
.prose.terminal {{ padding: 14px 20px 16px; }}
.terminal .prose, .terminal .prose * {{ font-family: var(--font-mono) !important; font-size: 13.5px !important; }}
.terminal .prose p {{ margin: 4px 0 !important; }}
.terminal strong {{ color: {GREEN}; }}

/* ---------- Results ---------- */
/* No padding or frame around the results, so each card is exactly as wide as the search bar and the log */
.block.results {{ padding: 0 !important; background: transparent !important; border: none !important; }}
.results h2 {{ font-size: 1.3rem !important; margin: 8px 0 16px !important; }}
.results h2 code {{ color: {GREEN}; background: rgba(62,224,143,0.1); padding: 2px 8px; border-radius: 8px; }}
.tool-card {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 20px;
    padding: 6px 24px 18px; margin: 0 0 16px;
    transition: border-color 0.2s ease;
}}
.tool-card:hover {{ border-color: {BORDER_STRONG}; }}
.tool-card.recommendation {{
    border-color: rgba(167,139,250,0.45);
    background: linear-gradient(180deg, rgba(167,139,250,0.08), {SURFACE} 60%);
}}
.tool-card.recommendation h3 {{ color: {VIOLET} !important; }}
.tool-card h3 {{ margin-top: 16px !important; }}
.tool-card table {{
    border-collapse: separate !important; border-spacing: 0; width: 100%;
    border: 1px solid {BORDER}; border-radius: 12px; overflow: hidden;
    display: table !important; padding: 0 !important; margin: 12px 0 !important;
}}
.tool-card th {{ background: {SURFACE_RAISED} !important; color: {MUTED} !important; font-weight: 500; font-size: 13px; }}
.tool-card th, .tool-card td {{ border: none !important; border-bottom: 1px solid {BORDER} !important; padding: 10px 14px !important; }}
.tool-card tr:last-child td {{ border-bottom: none !important; }}
.tool-card strong {{ color: {CYAN}; font-weight: 600; }}

/* ---------- Sidebar ---------- */
.key-sidebar {{ background: {SURFACE} !important; border-right: 1px solid {BORDER} !important; }}
.prose.key-status {{
    border: 1px dashed {BORDER_STRONG}; border-radius: 14px; padding: 10px 14px !important;
    font-family: var(--font-mono); font-size: 13px;
}}

/* ---------- Footer ---------- */
.app-footer {{ text-align: center; font-family: var(--font-mono); font-size: 12px; color: {MUTED}; padding: 24px 0 8px; }}
.app-footer p {{ color: {MUTED} !important; }}

/* ---------- Phones: stack the search bar and shrink the title ---------- */
@media (max-width: 640px) {{
    .hero h1 {{ font-size: 1.55rem !important; }}
    .search-bar {{ flex-direction: column !important; align-items: stretch !important; }}
    .search-bar button {{ width: 100%; }}
}}

/* Thin, rounded scrollbars */
::-webkit-scrollbar {{ width: 10px; height: 10px; }}
::-webkit-scrollbar-thumb {{ background: {BORDER_STRONG}; border-radius: 999px; border: 2px solid {BG}; }}
::-webkit-scrollbar-track {{ background: transparent; }}
"""

# Gradio switches to its dark variables when the page has the "dark" class.
# The theme above already looks dark in both modes; this makes Gradio's built-in parts match too.
FORCE_DARK_JS = "() => { document.body.classList.add('dark'); }"

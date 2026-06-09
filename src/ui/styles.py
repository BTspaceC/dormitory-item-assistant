import streamlit as st

def add_page_style() -> None:
    st.markdown(
        """
        <style>
        :root {
            --campus-ink: #223326;
            --campus-muted: #647064;
            --campus-green: #4f7d55;
            --campus-green-soft: #edf6ea;
            --campus-blue-soft: #edf7fb;
            --campus-amber-soft: #fff5dd;
            --campus-card: rgba(255, 255, 255, 0.94);
            --campus-line: rgba(80, 111, 83, 0.16);
            --campus-shadow: 0 12px 34px rgba(48, 70, 51, 0.08);
            --campus-page-bg: linear-gradient(180deg, #f7fbf4 0%, #eef7f6 46%, #fff8eb 100%);
            --campus-header-bg: rgba(247, 251, 244, 0.86);
            --campus-sidebar-bg: #fbf8ee;
            --campus-hero-bg: linear-gradient(135deg, #ffffff 0%, #f1f8ee 62%, #fff4dc 100%);
            --campus-hero-title: #1f3527;
            --campus-hero-text: #526255;
            --campus-kicker-bg: rgba(79, 125, 85, 0.09);
            --campus-kicker-border: rgba(79, 125, 85, 0.14);
            --campus-stat-bg: rgba(255, 255, 255, 0.70);
            --campus-soft-panel: #f8fbf6;
            --campus-input-bg: #ffffff;
            --campus-uploader-bg: rgba(255, 255, 255, 0.72);
            --campus-primary: #4f7d55;
            --campus-primary-hover: #416d48;
            --risk-normal-bg: #f2faf2;
            --risk-normal-text: #234a2c;
            --risk-watch-bg: #fff8e4;
            --risk-watch-text: #604811;
            --risk-restock-bg: #fff1e8;
            --risk-restock-text: #6d351c;
            --risk-danger-bg: #fff0ef;
            --risk-danger-text: #74302e;
        }
        html.dorm-theme-dark {
            --campus-ink: #edf5ee;
            --campus-muted: #aab8ad;
            --campus-green: #9bd38b;
            --campus-green-soft: #14271a;
            --campus-blue-soft: #142632;
            --campus-amber-soft: #2b2413;
            --campus-card: rgba(22, 30, 25, 0.94);
            --campus-line: rgba(186, 220, 178, 0.16);
            --campus-shadow: 0 16px 42px rgba(0, 0, 0, 0.34);
            --campus-page-bg: linear-gradient(180deg, #0f1713 0%, #12201e 48%, #201a12 100%);
            --campus-header-bg: rgba(15, 23, 19, 0.90);
            --campus-sidebar-bg: #101812;
            --campus-hero-bg: linear-gradient(135deg, #18231b 0%, #142820 58%, #2a2316 100%);
            --campus-hero-title: #f0f8ef;
            --campus-hero-text: #c0cfc2;
            --campus-kicker-bg: rgba(155, 211, 139, 0.12);
            --campus-kicker-border: rgba(155, 211, 139, 0.22);
            --campus-stat-bg: rgba(255, 255, 255, 0.055);
            --campus-soft-panel: rgba(255, 255, 255, 0.045);
            --campus-input-bg: #121b16;
            --campus-uploader-bg: rgba(255, 255, 255, 0.035);
            --campus-primary: #74a96c;
            --campus-primary-hover: #8fc481;
            --risk-normal-bg: rgba(45, 118, 68, 0.18);
            --risk-normal-text: #cdeecf;
            --risk-watch-bg: rgba(201, 148, 46, 0.18);
            --risk-watch-text: #f5d88c;
            --risk-restock-bg: rgba(210, 106, 53, 0.20);
            --risk-restock-text: #f4b28b;
            --risk-danger-bg: rgba(185, 74, 72, 0.22);
            --risk-danger-text: #f0aaa6;
        }
        html, body, [data-testid="stAppViewContainer"] {
            background: var(--campus-page-bg);
            color: var(--campus-ink);
        }
        [data-testid="stHeader"] {
            background: var(--campus-header-bg);
            backdrop-filter: blur(8px);
        }
        [data-testid="stSidebar"] {
            background: var(--campus-sidebar-bg);
            border-right: 1px solid rgba(79, 125, 85, 0.14);
        }
        [data-testid="stSidebar"] * {
            color: var(--campus-ink);
        }
        .block-container {
            max-width: 1280px;
            padding-top: 1.05rem;
            padding-bottom: 3rem;
        }
        h1, h2, h3, h4 {
            color: var(--campus-ink);
            letter-spacing: 0;
        }
        [data-testid="stMarkdownContainer"] a.anchor-link,
        [data-testid="stMarkdownContainer"] a[href^="#"] {
            display: none !important;
        }
        .small-note { color: var(--campus-muted); font-size: 0.92rem; }
        .result-caption { color: var(--campus-muted); font-size: 0.9rem; margin-top: -0.4rem; }
        .reason-box { background: var(--campus-soft-panel); border: 1px solid var(--campus-line); border-radius: 8px; padding: 0.8rem 1rem; }
        .app-hero {
            background: var(--campus-hero-bg);
            border: 1px solid rgba(79, 125, 85, 0.18);
            border-left: 6px solid #6f9f62;
            border-radius: 8px;
            color: var(--campus-ink);
            margin: 0 0 1.1rem 0;
            padding: 1.15rem 1.45rem 1.2rem 1.65rem;
            box-shadow: var(--campus-shadow);
        }
        .app-hero-main {
            display: grid;
            grid-template-columns: minmax(0, 1fr) minmax(220px, 300px);
            gap: 1rem;
            align-items: center;
        }
        .app-hero-kicker {
            background: var(--campus-kicker-bg);
            border: 1px solid var(--campus-kicker-border);
            border-radius: 8px;
            color: var(--campus-green);
            display: inline-flex;
            font-size: 0.86rem;
            font-weight: 700;
            letter-spacing: 0;
            margin-bottom: 0.55rem;
            padding: 0.18rem 0.5rem;
        }
        .app-hero h1 {
            color: var(--campus-hero-title);
            font-size: clamp(1.75rem, 2.6vw, 2.6rem);
            letter-spacing: 0;
            line-height: 1.15;
            margin: 0 0 0.45rem 0;
        }
        .app-hero p {
            color: var(--campus-hero-text);
            font-size: 1rem;
            line-height: 1.65;
            margin: 0;
            max-width: 72rem;
        }
        .app-hero-stats {
            display: grid;
            gap: 0.55rem;
        }
        .app-hero-stats div {
            background: var(--campus-stat-bg);
            border: none;
            border-radius: 10px;
            padding: 0.58rem 0.7rem;
            box-shadow: 0 2px 10px rgba(48, 70, 51, 0.06);
        }
        html.dorm-theme-dark .app-hero-stats div {
            box-shadow: 0 2px 12px rgba(0, 0, 0, 0.22);
        }
        .app-hero-stats strong {
            color: var(--campus-ink);
            display: block;
            font-size: 0.96rem;
            line-height: 1.25;
        }
        .app-hero-stats span {
            color: var(--campus-muted);
            font-size: 0.8rem;
        }
        .app-badges {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-top: 0.85rem;
        }
        .app-badge {
            background: #ffffff;
            border: 1px solid rgba(79, 125, 85, 0.18);
            border-radius: 8px;
            color: #2e4b36;
            font-size: 0.86rem;
            line-height: 1.2;
            padding: 0.28rem 0.58rem;
        }
        .app-badge:nth-child(2) {
            background: #fff7df;
            border-color: rgba(192, 151, 50, 0.22);
            color: #604b17;
        }
        .app-badge:nth-child(3) {
            background: #edf7fb;
            border-color: rgba(75, 132, 172, 0.20);
            color: #28506c;
        }
        .app-badge:nth-child(4) {
            background: #fff1ed;
            border-color: rgba(197, 112, 94, 0.20);
            color: #6a352b;
        }
        html.dorm-theme-dark .app-badge {
            background: rgba(255, 255, 255, 0.055);
            border-color: rgba(155, 211, 139, 0.18);
            color: #d9ead8;
        }
        html.dorm-theme-dark .app-badge:nth-child(2) {
            background: rgba(201, 148, 46, 0.12);
            border-color: rgba(201, 148, 46, 0.22);
            color: #f3d98d;
        }
        html.dorm-theme-dark .app-badge:nth-child(3) {
            background: rgba(75, 132, 172, 0.13);
            border-color: rgba(75, 132, 172, 0.24);
            color: #b8def3;
        }
        html.dorm-theme-dark .app-badge:nth-child(4) {
            background: rgba(197, 112, 94, 0.14);
            border-color: rgba(197, 112, 94, 0.24);
            color: #f1b8aa;
        }
        .flow-steps {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 1.2rem;
            margin: 0.2rem 0 0.95rem 0;
        }
        .flow-step {
            background: var(--campus-card);
            border: none;
            border-radius: 10px;
            padding: 0.72rem 0.85rem;
            box-shadow: 0 2px 12px rgba(48, 70, 51, 0.07), 0 0.5px 2px rgba(48, 70, 51, 0.04);
            position: relative;
        }
        html.dorm-theme-dark .flow-step {
            box-shadow: 0 2px 16px rgba(0, 0, 0, 0.28);
        }
        .flow-step:not(:last-child)::after {
            content: "→";
            position: absolute;
            right: -0.85rem;
            top: 50%;
            transform: translateY(-50%);
            color: var(--campus-muted);
            font-size: 1.15rem;
            font-weight: 300;
            z-index: 1;
        }
        .flow-step-num {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 1.35rem;
            height: 1.35rem;
            background: var(--campus-primary);
            color: #fff;
            border-radius: 50%;
            font-size: 0.76rem;
            font-weight: 700;
            margin-right: 0.35rem;
            vertical-align: middle;
            flex-shrink: 0;
        }
        .flow-step strong {
            color: var(--campus-ink);
            display: flex;
            align-items: center;
            font-size: 0.96rem;
            margin-bottom: 0.16rem;
        }
        .flow-step span {
            color: var(--campus-muted);
            font-size: 0.86rem;
        }
        .result-card-grid,
        .batch-summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 0.65rem;
            margin: 0.75rem 0 0.9rem 0;
        }
        .result-card,
        .batch-summary-card {
            background: var(--campus-card);
            border: none;
            border-radius: 10px;
            padding: 0.82rem 0.92rem;
            box-shadow: 0 2px 12px rgba(48, 70, 51, 0.07), 0 0.5px 2px rgba(48, 70, 51, 0.04);
        }
        html.dorm-theme-dark .result-card,
        html.dorm-theme-dark .batch-summary-card {
            box-shadow: 0 2px 16px rgba(0, 0, 0, 0.28), 0 0.5px 2px rgba(0, 0, 0, 0.18);
        }
        .result-card .label,
        .batch-summary-card .label {
            color: var(--campus-muted);
            font-size: 0.78rem;
            margin-bottom: 0.28rem;
        }
        .result-card .value,
        .batch-summary-card .value {
            color: var(--campus-ink);
            font-size: 1.04rem;
            font-weight: 700;
            line-height: 1.35;
            word-break: break-word;
        }
        .result-card .hint,
        .batch-summary-card .hint {
            color: var(--campus-muted);
            font-size: 0.78rem;
            margin-top: 0.25rem;
        }
        .result-card.risk-normal { border-left: 5px solid #4f8a5b; background: var(--risk-normal-bg); }
        .result-card.risk-watch { border-left: 5px solid #c9942e; background: var(--risk-watch-bg); }
        .result-card.risk-restock { border-left: 5px solid #d26a35; background: var(--risk-restock-bg); }
        .result-card.risk-danger { border-left: 5px solid #b94a48; background: var(--risk-danger-bg); }
        .risk-alert {
            border-radius: 8px;
            padding: 0.9rem 1rem;
            border: 1px solid var(--campus-line);
            margin: 0.65rem 0 0.8rem 0;
            line-height: 1.65;
        }
        .risk-alert strong { display: block; margin-bottom: 0.2rem; }
        .risk-alert.risk-normal { background: var(--risk-normal-bg); color: var(--risk-normal-text); border-color: rgba(79, 138, 91, 0.22); }
        .risk-alert.risk-watch { background: var(--risk-watch-bg); color: var(--risk-watch-text); border-color: rgba(201, 148, 46, 0.24); }
        .risk-alert.risk-restock { background: var(--risk-restock-bg); color: var(--risk-restock-text); border-color: rgba(210, 106, 53, 0.22); }
        .risk-alert.risk-danger { background: var(--risk-danger-bg); color: var(--risk-danger-text); border-color: rgba(185, 74, 72, 0.22); }
        .reason-list {
            display: grid;
            gap: 0.45rem;
            margin: 0.65rem 0 0.9rem 0;
        }
        .reason-item {
            background: var(--campus-card);
            border: none;
            border-left: 4px solid rgba(79, 125, 85, 0.52);
            border-radius: 10px;
            color: var(--campus-ink);
            line-height: 1.6;
            padding: 0.62rem 0.78rem;
            box-shadow: 0 2px 10px rgba(48, 70, 51, 0.06);
        }
        .docs-intro {
            background: var(--campus-soft-panel);
            border: none;
            border-radius: 10px;
            padding: 0.9rem 1rem;
            margin-bottom: 0.9rem;
            box-shadow: 0 1px 8px rgba(48, 70, 51, 0.05);
        }
        div[data-testid="stForm"],
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--campus-card);
            border: none;
            border-radius: 10px;
            box-shadow: 0 2px 14px rgba(48, 70, 51, 0.07), 0 0.5px 2px rgba(48, 70, 51, 0.04);
        }
        html.dorm-theme-dark div[data-testid="stForm"],
        html.dorm-theme-dark div[data-testid="stVerticalBlockBorderWrapper"] {
            box-shadow: 0 2px 18px rgba(0, 0, 0, 0.30);
        }
        div[data-testid="stForm"] {
            padding: 1rem;
        }
        /* 针对表单、边栏及独立区块容器内的输入控件进行美化，避免污染数据表格编辑器 */
        div[data-baseweb="input"]:not([data-testid*="DataEditor"] *):not([data-testid*="DataFrame"] *) > div,
        div[data-baseweb="textarea"]:not([data-testid*="DataEditor"] *):not([data-testid*="DataFrame"] *) textarea,
        div[data-baseweb="select"]:not([data-testid*="DataEditor"] *):not([data-testid*="DataFrame"] *) > div,
        div[data-baseweb="base-input"]:not([data-testid*="DataEditor"] *):not([data-testid*="DataFrame"] *) {
            border-radius: 8px !important;
            border-color: rgba(79, 125, 85, 0.22) !important;
            background-color: var(--campus-input-bg) !important;
        }
        div[data-baseweb="input"]:not([data-testid*="DataEditor"] *):not([data-testid*="DataFrame"] *) input,
        div[data-baseweb="textarea"]:not([data-testid*="DataEditor"] *):not([data-testid*="DataFrame"] *) textarea,
        div[data-baseweb="select"]:not([data-testid*="DataEditor"] *):not([data-testid*="DataFrame"] *) span,
        div[data-baseweb="base-input"]:not([data-testid*="DataEditor"] *):not([data-testid*="DataFrame"] *) input {
            color: var(--campus-ink) !important;
            caret-color: var(--campus-green) !important;
        }
        div[data-baseweb="input"]:not([data-testid*="DataEditor"] *):not([data-testid*="DataFrame"] *) input::placeholder,
        div[data-baseweb="textarea"]:not([data-testid*="DataEditor"] *):not([data-testid*="DataFrame"] *) textarea::placeholder {
            color: var(--campus-muted) !important;
            opacity: 0.72;
        }
        html.dorm-theme-dark div[data-baseweb="input"]:not([data-testid*="DataEditor"] *):not([data-testid*="DataFrame"] *) > div,
        html.dorm-theme-dark div[data-baseweb="textarea"]:not([data-testid*="DataEditor"] *):not([data-testid*="DataFrame"] *) textarea,
        html.dorm-theme-dark div[data-baseweb="select"]:not([data-testid*="DataEditor"] *):not([data-testid*="DataFrame"] *) > div,
        html.dorm-theme-dark div[data-baseweb="base-input"]:not([data-testid*="DataEditor"] *):not([data-testid*="DataFrame"] *) {
            border-color: rgba(155, 211, 139, 0.20) !important;
        }
        html.dorm-theme-dark div[role="listbox"],
        html.dorm-theme-dark div[data-baseweb="popover"] {
            background: #121b16 !important;
            color: var(--campus-ink) !important;
        }
        html.dorm-theme-dark div[data-baseweb="popover"] [role="option"],
        html.dorm-theme-dark div[role="listbox"] [role="option"] {
            color: var(--campus-ink) !important;
        }
        div[data-testid="stFileUploader"] section {
            background: var(--campus-uploader-bg);
            border: 1px dashed rgba(79, 125, 85, 0.34);
            border-radius: 8px;
        }
        html.dorm-theme-dark div[data-testid="stFileUploader"] section {
            border-color: rgba(155, 211, 139, 0.24);
        }
        div[data-testid="stTabs"] button {
            border-radius: 8px 8px 0 0;
            color: var(--campus-muted);
            font-weight: 650;
            padding: 0.65rem 1rem;
        }
        div[data-testid="stTabs"] button[aria-selected="true"] {
            color: var(--campus-green);
            border-bottom-color: var(--campus-green) !important;
        }
        div[data-testid="stTabs"] button:hover {
            color: var(--campus-green);
            border-bottom-color: var(--campus-green) !important;
        }
        div[data-testid="stButton"] button,
        div[data-testid="stDownloadButton"] button {
            border-radius: 8px;
            font-weight: 650;
        }
        div[data-testid="stButton"] button[kind="primary"],
        div[data-testid="stFormSubmitButton"] button {
            background: var(--campus-primary);
            border-color: var(--campus-primary);
            color: #ffffff;
        }
        div[data-testid="stButton"] button[kind="primary"]:hover,
        div[data-testid="stFormSubmitButton"] button:hover {
            background: var(--campus-primary-hover);
            border-color: var(--campus-primary-hover);
        }
        div[data-testid="stDataFrame"],
        div[data-testid="stDataEditor"] {
            border-radius: 8px;
            overflow: hidden;
        }
        @media (max-width: 640px) {
            .app-hero { padding: 0.9rem 1rem; }
            .app-hero-main { grid-template-columns: 1fr; }
            .app-hero-stats { grid-template-columns: 1fr; }
            .app-hero h1 { font-size: 1.65rem; }
            .flow-steps { grid-template-columns: 1fr; }
            .result-card-grid,
            .batch-summary-grid { grid-template-columns: 1fr; }
        }
        div[data-baseweb="select"] > div {
            cursor: default !important;
        }
        /* Baseline: strip outline/ring from data-editor buttons;
           the real fix is the JS auto-blur in render_theme_bridge. */
        div[data-testid*="DataFrame"] button,
        div[data-testid*="DataEditor"] button {
            outline: none !important;
            box-shadow: none !important;
        }
        /* Sidebar metric dashboard cards */
        [data-testid="stSidebar"] [data-testid="stMetric"] {
            background: var(--campus-stat-bg);
            border-radius: 10px;
            padding: 0.65rem 0.85rem;
            margin-bottom: 0.35rem;
            box-shadow: 0 1px 6px rgba(48, 70, 51, 0.05);
        }
        [data-testid="stSidebar"] [data-testid="stMetricValue"] {
            color: var(--campus-green);
        }
        /* Expander visual enhancement */
        details[data-testid="stExpander"] {
            border: none !important;
            border-radius: 10px !important;
            box-shadow: 0 2px 10px rgba(48, 70, 51, 0.06);
            overflow: hidden;
        }
        html.dorm-theme-dark details[data-testid="stExpander"] {
            box-shadow: 0 2px 14px rgba(0, 0, 0, 0.25);
        }
        details[data-testid="stExpander"] summary:hover {
            background: var(--campus-green-soft);
        }
        details[data-testid="stExpander"] summary svg {
            color: var(--campus-green) !important;
            transition: transform 0.2s ease;
        }
        /* Image polish: rounded corners + float shadow */
        [data-testid="stImage"] img {
            border-radius: 10px;
            box-shadow: 0 4px 20px rgba(48, 70, 51, 0.10);
            transition: box-shadow 0.2s ease;
        }
        [data-testid="stImage"] img:hover {
            box-shadow: 0 8px 32px rgba(48, 70, 51, 0.16);
        }
        html.dorm-theme-dark [data-testid="stImage"] img {
            box-shadow: 0 4px 24px rgba(0, 0, 0, 0.35);
        }
        html.dorm-theme-dark [data-testid="stImage"] img:hover {
            box-shadow: 0 8px 36px rgba(0, 0, 0, 0.45);
        }
        /* Unify regular button hover to brand green instead of red */
        div[data-testid="stButton"] button:hover,
        div[data-testid="stDownloadButton"] button:hover {
            border-color: var(--campus-primary) !important;
            color: var(--campus-primary);
        }
        </style>
        """,
        unsafe_allow_html=True
    )


def render_theme_bridge() -> None:
    """Sync our custom CSS theme class with Streamlit's active theme.

    Uses st.components.v1.html (iframe) — the only reliable way to execute
    JavaScript inside a Streamlit app.  The script reads the computed
    backgroundColor of the **.stApp** element in the parent window.  Because
    our custom CSS targets ``html``, ``body`` and ``[data-testid="stAppViewContainer"]``
    but **not** ``.stApp`` itself, the value reflects Streamlit's own Emotion-CSS
    theme color and is never polluted by our overrides.

    Falls back to localStorage key containing ``stActiveTheme-`` and finally
    to the system ``prefers-color-scheme`` media query.
    """
    import streamlit as st
    st.iframe(
        '''
        <script>
        (function () {
            var pw = window.parent;
            if (!pw || !pw.document) return;
            var root = pw.document.documentElement;

            /* ---- clear any previous polling interval ---- */
            if (pw.__themeSyncId) { pw.clearInterval(pw.__themeSyncId); }

            function detectDark() {
                /* --- Method 1: read .stApp background (Streamlit Emotion CSS) --- */
                try {
                    var el = pw.document.querySelector('[data-testid="stApp"]')
                          || pw.document.querySelector('.stApp');
                    if (el) {
                        var bg = pw.getComputedStyle(el).backgroundColor;
                        if (bg && bg !== "rgba(0, 0, 0, 0)" && bg !== "transparent") {
                            var m = bg.match(/\\d+/g);
                            if (m && m.length >= 3) {
                                var lum = (0.299*parseInt(m[0]) + 0.587*parseInt(m[1]) + 0.114*parseInt(m[2])) / 255;
                                return lum < 0.5;
                            }
                        }
                    }
                } catch (_) {}

                /* --- Method 2: localStorage  stActiveTheme- key --- */
                try {
                    var keys = Object.keys(pw.localStorage);
                    for (var i = 0; i < keys.length; i++) {
                        if (keys[i].indexOf("stActiveTheme") !== -1) {
                            var raw = pw.localStorage.getItem(keys[i]);
                            if (raw) {
                                try {
                                    var obj = JSON.parse(raw);
                                    var n = (obj.name || obj.base || "").toLowerCase();
                                    if (n === "dark") return true;
                                    if (n === "light") return false;
                                    if (n === "system" || n === "") {
                                        return pw.matchMedia("(prefers-color-scheme: dark)").matches;
                                    }
                                } catch (_) {}
                            }
                            break;
                        }
                    }
                } catch (_) {}

                /* --- Method 3: system preference --- */
                return pw.matchMedia("(prefers-color-scheme: dark)").matches;
            }

            function sync() {
                var dark = detectDark();
                root.classList.toggle("dorm-theme-dark", dark);
                root.classList.toggle("dorm-theme-light", !dark);
            }

            sync();
            pw.__themeSyncId = pw.setInterval(sync, 500);

            function sendEscape(target) {
                try {
                    var event = new pw.KeyboardEvent("keydown", {
                        key: "Escape",
                        code: "Escape",
                        keyCode: 27,
                        which: 27,
                        bubbles: true,
                        cancelable: true
                    });
                    (target || pw.document).dispatchEvent(event);
                } catch (_) {}
            }

            function hasOpenFloatingLayer() {
                return !!pw.document.querySelector(
                    '[data-baseweb="popover"], [role="listbox"], [data-baseweb="menu"]'
                );
            }

            function isEditableElement(el) {
                if (!el || !el.tagName) return false;
                var tag = el.tagName.toUpperCase();
                if (el.classList && el.classList.contains("gdg-input")) return true;
                if (el.isContentEditable) return true;
                if (tag === "TEXTAREA") return true;
                if (tag !== "INPUT") return false;
                var type = (el.getAttribute("type") || "text").toLowerCase();
                return ["checkbox", "radio", "file", "button", "submit", "reset", "hidden"].indexOf(type) === -1;
            }

            function closeScrollSensitiveFocus(reason) {
                var active = pw.document.activeElement;
                var isGridEditor = !!(active && active.classList && active.classList.contains("gdg-input"));
                if (isGridEditor) {
                    sendEscape(active);
                }
                if (hasOpenFloatingLayer()) {
                    sendEscape(active);
                    sendEscape(pw.document);
                }
                if (isEditableElement(active)) {
                    active.blur();
                }
            }

            function isInsideFloatingLayer(target) {
                return !!(
                    target &&
                    target.closest &&
                    target.closest('[data-baseweb="popover"], [role="listbox"], [data-baseweb="menu"]')
                );
            }

            function isMainPageScrollTarget(target) {
                if (!target || target === pw || target === pw.document) return true;
                if (target === pw.document.body || target === pw.document.documentElement) return true;
                return !!(target.getAttribute && target.getAttribute("data-testid") === "stMain");
            }

            if (!pw.__themeBlurSet) {
                pw.__themeBlurSet = true;
                pw.addEventListener("click", function (e) {
                    if (e.target && e.target.closest("button")) {
                        pw.setTimeout(function () {
                            var a = pw.document.activeElement;
                            if (a && a.tagName === "BUTTON") a.blur();
                        }, 100);
                    }
                }, {capture: true});
            }

            if (!pw.__dormScrollFocusGuardSet) {
                pw.__dormScrollFocusGuardSet = true;
                pw.addEventListener("wheel", function (e) {
                    if (!isInsideFloatingLayer(e.target)) {
                        closeScrollSensitiveFocus("wheel");
                    }
                }, {capture: true, passive: true});
                pw.document.addEventListener("scroll", function (e) {
                    var active = pw.document.activeElement;
                    var isGridEditor = !!(active && active.classList && active.classList.contains("gdg-input"));
                    if (isGridEditor || isMainPageScrollTarget(e.target)) {
                        closeScrollSensitiveFocus("scroll");
                    }
                }, true);
            }
        })();
        </script>
        ''',
        height=1,
        width=1,
    )

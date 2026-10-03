from typing import Any, Dict, List, Optional
import streamlit as st


# ==============================================================================
# VETRA CENTRALIZED AI THEME & COLOR SYSTEM
# ==============================================================================
THEME = {
    # Backgrounds
    "bg": "#050816",                 # Primary dark AI navy foundation
    "bg_secondary": "#0A1020",       # Secondary background / sidebar base
    "surface": "#111827",            # Solid surface
    "surface_glass": "rgba(15, 23, 42, 0.72)", # Translucent glass surface
    "surface_elevated": "#172033",   # Elevated surface

    # Cards & Containers
    "card": "rgba(15, 23, 42, 0.75)",
    "card_elevated": "rgba(23, 32, 51, 0.85)",
    "border": "rgba(148, 163, 184, 0.15)",
    "border_focus": "#22D3EE",
    "border_light": "rgba(148, 163, 184, 0.22)",

    # Typography
    "text_primary": "#F8FAFC",       # High contrast bright white
    "text_secondary": "#CBD5E1",     # Crisp readable body text
    "text_muted": "#94A3B8",         # Muted but visible labels & captions

    # AI Visual Accents
    "ai_cyan": "#22D3EE",            # AI Cyan primary accent
    "ai_blue": "#38BDF8",            # AI Sky Blue secondary accent
    "ai_purple": "#8B5CF6",          # AI Neural Purple accent
    "ai_glow": "rgba(34, 211, 238, 0.12)",
    "purple_glow": "rgba(139, 92, 246, 0.10)",

    # Semantic Status
    "success": "#22C55E",            # Green status / healthy
    "warning": "#F59E0B",            # Amber warning / monitoring
    "danger": "#EF4444",             # Red alert / at risk
    "critical": "#DC2626",           # Deep red critical alert
}


def apply_custom_styles():
    """
    Inject professional, high-contrast AI-themed dark CSS styling for VETRA.
    Features:
    - Multi-layered AI background: #050816 base, radial cyan & purple glows,
      fine 40px digital grid, and neural node intersections.
    - Glassmorphism content surfaces with backdrop-filter blur.
    - AI-themed control-panel sidebar with cyan active indicators.
    - Subtle ambient glow and high-contrast typography hierarchy.
    """
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

        /* -------------------------------------------------------------
           GLOBAL RESETS & MULTI-LAYER AI BACKGROUND
           ------------------------------------------------------------- */
        html, body, [class*="css"], .stApp {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
            color: #CBD5E1 !important;
        }

        /* Root Application Multi-Layered AI Background */
        .stApp {
            background-color: #050816 !important;
            background-image: 
                /* Layer 6: Neural network node dots at 40px grid intersections */
                radial-gradient(circle at 20px 20px, rgba(34, 211, 238, 0.055) 1.2px, transparent 1.2px),
                /* Layer 5: Fine digital grid lines (40px x 40px) */
                linear-gradient(rgba(148, 163, 184, 0.024) 1px, transparent 1px),
                linear-gradient(90deg, rgba(148, 163, 184, 0.024) 1px, transparent 1px),
                /* Layer 2: Soft radial cyan glow near upper-right */
                radial-gradient(circle at 82% 14%, rgba(34, 211, 238, 0.075) 0%, transparent 45%),
                /* Layer 3: Soft blue glow near lower-left */
                radial-gradient(circle at 14% 86%, rgba(56, 189, 248, 0.065) 0%, transparent 42%),
                /* Layer 4: Very subtle purple AI intelligence glow */
                radial-gradient(circle at 50% 45%, rgba(139, 92, 246, 0.045) 0%, transparent 55%),
                /* Layer 1: Base depth gradient */
                linear-gradient(180deg, #050816 0%, #080E22 50%, #050816 100%) !important;
            background-size: 
                40px 40px, 
                40px 40px, 
                40px 40px, 
                100% 100%, 
                100% 100%, 
                100% 100%, 
                100% 100% !important;
            background-position: 
                0 0,
                0 0,
                0 0,
                center top,
                center bottom,
                center center,
                center center !important;
            background-attachment: fixed !important;
            animation: ambientGlowDrift 30s ease-in-out infinite alternate;
        }

        @keyframes ambientGlowDrift {
            0% {
                background-position: 0 0, 0 0, 0 0, 80% 12%, 15% 88%, 50% 42%, center center;
            }
            50% {
                background-position: 0 0, 0 0, 0 0, 85% 16%, 12% 82%, 52% 48%, center center;
            }
            100% {
                background-position: 0 0, 0 0, 0 0, 80% 12%, 15% 88%, 50% 42%, center center;
            }
        }

        /* Ensure Streamlit view containers allow background transparency */
        [data-testid="stAppViewContainer"],
        [data-testid="stAppViewBlockContainer"],
        .main,
        [data-testid="stMain"] {
            background: transparent !important;
        }

        /* Hide default Streamlit multipage navigation to use custom VETRA menu */
        [data-testid="stSidebarNav"] {
            display: none !important;
        }

        /* Streamlit Top Header Bar */
        header[data-testid="stHeader"] {
            background: rgba(5, 8, 22, 0.8) !important;
            backdrop-filter: blur(12px) !important;
            -webkit-backdrop-filter: blur(12px) !important;
            border-bottom: 1px solid rgba(148, 163, 184, 0.12) !important;
        }

        /* -------------------------------------------------------------
           HEADINGS HIERARCHY
           ------------------------------------------------------------- */
        h1 {
            color: #F8FAFC !important;
            font-size: 1.85rem !important;
            font-weight: 800 !important;
            letter-spacing: -0.025em !important;
            margin-bottom: 0.35rem !important;
        }

        h2 {
            color: #F8FAFC !important;
            font-size: 1.45rem !important;
            font-weight: 700 !important;
            letter-spacing: -0.02em !important;
            margin-top: 1rem !important;
            margin-bottom: 0.5rem !important;
        }

        h3 {
            color: #F8FAFC !important;
            font-size: 1.2rem !important;
            font-weight: 700 !important;
            margin-top: 0.75rem !important;
            margin-bottom: 0.35rem !important;
        }

        h4, h5, h6 {
            color: #F8FAFC !important;
            font-size: 1.05rem !important;
            font-weight: 600 !important;
        }

        p, div, span {
            color: #CBD5E1;
        }

        strong, b {
            color: #F8FAFC !important;
            font-weight: 700;
        }

        small, .stCaption, [data-testid="stCaptionContainer"] {
            color: #94A3B8 !important;
            font-size: 0.82rem !important;
        }

        /* Inline code snippets */
        code {
            font-family: 'JetBrains Mono', monospace !important;
            background-color: rgba(23, 32, 51, 0.85) !important;
            color: #22D3EE !important;
            border: 1px solid rgba(148, 163, 184, 0.2) !important;
            border-radius: 4px !important;
            padding: 0.15rem 0.4rem !important;
            font-size: 0.85em !important;
        }

        /* Horizontal dividers */
        hr {
            border: 0;
            border-top: 1px solid rgba(148, 163, 184, 0.15) !important;
            margin: 1.25rem 0 !important;
        }

        /* -------------------------------------------------------------
           STREAMLIT SIDEBAR (AI CONTROL PANEL)
           ------------------------------------------------------------- */
        [data-testid="stSidebar"] {
            background: rgba(8, 14, 28, 0.92) !important;
            backdrop-filter: blur(16px) !important;
            -webkit-backdrop-filter: blur(16px) !important;
            border-right: 1px solid rgba(34, 211, 238, 0.16) !important;
            box-shadow: 4px 0 24px rgba(0, 0, 0, 0.45) !important;
        }

        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] label {
            color: #CBD5E1 !important;
        }

        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {
            color: #F8FAFC !important;
        }

        /* Active Navigation Button in Sidebar */
        [data-testid="stSidebar"] button[kind="primary"] {
            background: linear-gradient(90deg, rgba(34, 211, 238, 0.2) 0%, rgba(56, 189, 248, 0.08) 100%) !important;
            color: #F8FAFC !important;
            border: 1px solid rgba(34, 211, 238, 0.5) !important;
            border-left: 4px solid #22D3EE !important;
            font-weight: 700 !important;
            border-radius: 6px !important;
            box-shadow: 0 0 16px rgba(34, 211, 238, 0.12) !important;
            text-align: left !important;
            justify-content: flex-start !important;
        }

        /* Inactive Navigation Button in Sidebar */
        [data-testid="stSidebar"] button[kind="secondary"] {
            background: rgba(17, 24, 39, 0.55) !important;
            color: #CBD5E1 !important;
            border: 1px solid rgba(148, 163, 184, 0.12) !important;
            border-radius: 6px !important;
            font-weight: 500 !important;
            text-align: left !important;
            justify-content: flex-start !important;
            transition: all 0.15s ease !important;
        }

        [data-testid="stSidebar"] button[kind="secondary"]:hover {
            background: rgba(23, 32, 51, 0.85) !important;
            border-color: rgba(34, 211, 238, 0.35) !important;
            color: #22D3EE !important;
            transform: translateX(2px);
        }

        /* -------------------------------------------------------------
           STREAMLIT METRICS (st.metric) - GLASS KPI CARDS
           ------------------------------------------------------------- */
        [data-testid="stMetric"] {
            background: rgba(15, 23, 42, 0.75) !important;
            backdrop-filter: blur(12px) !important;
            -webkit-backdrop-filter: blur(12px) !important;
            border: 1px solid rgba(148, 163, 184, 0.15) !important;
            border-radius: 12px !important;
            padding: 1rem 1.15rem !important;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3) !important;
            transition: all 0.2s ease !important;
        }

        [data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            border-color: rgba(34, 211, 238, 0.4) !important;
            box-shadow: 0 0 22px rgba(34, 211, 238, 0.08) !important;
        }

        [data-testid="stMetricLabel"] p {
            color: #94A3B8 !important;
            font-size: 0.78rem !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.06em !important;
        }

        [data-testid="stMetricValue"] div {
            color: #F8FAFC !important;
            font-size: 1.85rem !important;
            font-weight: 800 !important;
            letter-spacing: -0.02em !important;
        }

        [data-testid="stMetricDelta"] {
            font-size: 0.8rem !important;
            font-weight: 600 !important;
        }

        /* -------------------------------------------------------------
           BUTTONS (st.button)
           ------------------------------------------------------------- */
        button[kind="primary"] {
            background: linear-gradient(135deg, #0284C7 0%, #22D3EE 100%) !important;
            color: #050816 !important;
            font-weight: 700 !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 0.5rem 1.25rem !important;
            box-shadow: 0 2px 10px rgba(34, 211, 238, 0.3) !important;
            transition: all 0.18s ease !important;
        }

        button[kind="primary"]:hover {
            background: linear-gradient(135deg, #22D3EE 0%, #38BDF8 100%) !important;
            box-shadow: 0 0 22px rgba(34, 211, 238, 0.45) !important;
            transform: translateY(-1px);
        }

        button[kind="secondary"] {
            background: rgba(17, 24, 39, 0.7) !important;
            backdrop-filter: blur(8px) !important;
            color: #F8FAFC !important;
            border: 1px solid rgba(148, 163, 184, 0.18) !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            padding: 0.5rem 1.15rem !important;
            transition: all 0.18s ease !important;
        }

        button[kind="secondary"]:hover {
            background: rgba(23, 32, 51, 0.9) !important;
            border-color: #22D3EE !important;
            color: #22D3EE !important;
            box-shadow: 0 0 16px rgba(34, 211, 238, 0.12) !important;
            transform: translateY(-1px);
        }

        /* -------------------------------------------------------------
           INPUTS & SELECTBOXES
           ------------------------------------------------------------- */
        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input,
        [data-testid="stTextArea"] textarea {
            background: rgba(17, 24, 39, 0.85) !important;
            color: #F8FAFC !important;
            border: 1px solid rgba(148, 163, 184, 0.18) !important;
            border-radius: 8px !important;
        }

        [data-testid="stTextInput"] input::placeholder,
        [data-testid="stNumberInput"] input::placeholder,
        [data-testid="stTextArea"] textarea::placeholder {
            color: #94A3B8 !important;
            opacity: 1 !important;
        }

        [data-testid="stTextInput"] input:focus,
        [data-testid="stNumberInput"] input:focus,
        [data-testid="stTextArea"] textarea:focus {
            border-color: #22D3EE !important;
            box-shadow: 0 0 12px rgba(34, 211, 238, 0.25) !important;
        }

        [data-baseweb="select"] > div {
            background: rgba(17, 24, 39, 0.85) !important;
            color: #F8FAFC !important;
            border: 1px solid rgba(148, 163, 184, 0.18) !important;
            border-radius: 8px !important;
        }

        [data-baseweb="popover"], [data-baseweb="menu"] {
            background-color: #111827 !important;
            border: 1px solid rgba(148, 163, 184, 0.2) !important;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5) !important;
        }

        [data-baseweb="menu"] li {
            color: #CBD5E1 !important;
        }

        [data-baseweb="menu"] li:hover {
            background-color: #172033 !important;
            color: #22D3EE !important;
        }

        label[data-testid="stWidgetLabel"] p {
            color: #CBD5E1 !important;
            font-size: 0.85rem !important;
            font-weight: 600 !important;
        }

        /* -------------------------------------------------------------
           EXPANDERS & TABS
           ------------------------------------------------------------- */
        [data-testid="stExpander"] {
            background: rgba(15, 23, 42, 0.72) !important;
            backdrop-filter: blur(12px) !important;
            border: 1px solid rgba(148, 163, 184, 0.15) !important;
            border-radius: 10px !important;
            margin-bottom: 0.75rem !important;
        }

        [data-testid="stExpander"] summary {
            color: #F8FAFC !important;
            font-weight: 600 !important;
        }

        [data-testid="stExpander"] summary:hover {
            color: #22D3EE !important;
        }

        /* Tabs */
        [data-testid="stTabs"] button[data-baseweb="tab"] {
            color: #94A3B8 !important;
            font-weight: 600 !important;
            font-size: 0.9rem !important;
            padding: 0.65rem 1.2rem !important;
            transition: all 0.15s ease;
        }

        [data-testid="stTabs"] button[data-baseweb="tab"]:hover {
            color: #22D3EE !important;
        }

        [data-testid="stTabs"] button[aria-selected="true"] {
            color: #22D3EE !important;
            font-weight: 700 !important;
            border-bottom: 2px solid #22D3EE !important;
        }

        /* -------------------------------------------------------------
           DATAFRAMES & TABLES - OPAQUE CONTENT SURFACES
           ------------------------------------------------------------- */
        [data-testid="stDataFrame"], [data-testid="stTable"] {
            background: rgba(17, 24, 39, 0.94) !important;
            border: 1px solid rgba(148, 163, 184, 0.18) !important;
            border-radius: 10px !important;
            overflow: hidden !important;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25) !important;
        }

        /* -------------------------------------------------------------
           CUSTOM VETRA UI COMPONENTS (CLASSES)
           ------------------------------------------------------------- */

        /* Top Bar Breadcrumb with AI Glass */
        .vetra-top-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: rgba(15, 23, 42, 0.75) !important;
            backdrop-filter: blur(12px) !important;
            -webkit-backdrop-filter: blur(12px) !important;
            border: 1px solid rgba(34, 211, 238, 0.22) !important;
            border-radius: 10px !important;
            padding: 0.6rem 1.15rem !important;
            margin-bottom: 1.25rem !important;
            font-size: 0.85rem !important;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3), 0 0 20px rgba(34, 211, 238, 0.05) !important;
        }

        .vetra-breadcrumb {
            display: flex;
            align-items: center;
            gap: 0.45rem;
            color: #94A3B8;
            font-weight: 500;
        }

        .vetra-breadcrumb strong {
            color: #F8FAFC;
        }

        .vetra-top-meta {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        /* Page Header Container */
        .page-header-box, .vetra-header {
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid rgba(148, 163, 184, 0.14);
        }

        .page-header-title, .vetra-brand {
            font-size: 1.85rem;
            font-weight: 800;
            color: #F8FAFC !important;
            letter-spacing: -0.025em;
            display: flex;
            align-items: center;
            gap: 0.6rem;
            margin: 0;
        }

        .page-header-subtitle, .vetra-tagline {
            font-size: 0.92rem;
            color: #CBD5E1 !important;
            font-weight: 400;
            margin-top: 0.35rem;
        }

        /* Section Header */
        .section-header-box {
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            margin-top: 1.5rem;
            margin-bottom: 0.85rem;
            padding-bottom: 0.45rem;
            border-bottom: 1px solid rgba(148, 163, 184, 0.14);
        }

        .section-header-title {
            font-size: 1.25rem;
            font-weight: 700;
            color: #F8FAFC;
            letter-spacing: -0.015em;
            margin: 0;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .section-header-subtitle {
            font-size: 0.82rem;
            color: #94A3B8;
            margin-top: 0.2rem;
        }

        /* Universal Container Panel (Glass Surface) */
        .vetra-panel {
            background: rgba(15, 23, 42, 0.72) !important;
            backdrop-filter: blur(12px) !important;
            -webkit-backdrop-filter: blur(12px) !important;
            border: 1px solid rgba(148, 163, 184, 0.14) !important;
            border-radius: 12px !important;
            padding: 1.25rem !important;
            margin-bottom: 1.25rem !important;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.32) !important;
            transition: border-color 0.2s ease, box-shadow 0.2s ease;
        }

        .vetra-panel:hover {
            border-color: rgba(34, 211, 238, 0.28) !important;
            box-shadow: 0 0 25px rgba(34, 211, 238, 0.06), 0 6px 24px rgba(0, 0, 0, 0.35) !important;
        }

        /* VETRA Command Center Hero Box */
        .vetra-hero-box {
            background: radial-gradient(circle at 18% 25%, rgba(34, 211, 238, 0.08) 0%, rgba(139, 92, 246, 0.05) 55%, rgba(15, 23, 42, 0.75) 100%) !important;
            backdrop-filter: blur(14px) !important;
            -webkit-backdrop-filter: blur(14px) !important;
            border: 1px solid rgba(34, 211, 238, 0.28) !important;
            border-radius: 14px !important;
            padding: 1.35rem 1.75rem !important;
            margin-bottom: 1.25rem !important;
            box-shadow: 0 0 35px rgba(34, 211, 238, 0.07), 0 8px 24px rgba(0, 0, 0, 0.35) !important;
        }

        .hero-tag {
            background: rgba(34, 211, 238, 0.09);
            color: #22D3EE;
            border: 1px solid rgba(34, 211, 238, 0.28);
            font-size: 0.72rem;
            font-weight: 700;
            padding: 0.25rem 0.65rem;
            border-radius: 6px;
            letter-spacing: 0.05em;
        }

        /* Premium KPI Card (Floating Glass Surface) */
        .kpi-card {
            background: rgba(15, 23, 42, 0.75) !important;
            backdrop-filter: blur(12px) !important;
            -webkit-backdrop-filter: blur(12px) !important;
            border: 1px solid rgba(148, 163, 184, 0.15) !important;
            border-radius: 12px !important;
            padding: 1.15rem 1.15rem !important;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3) !important;
            transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
        }

        .kpi-card:hover {
            transform: translateY(-2px);
            border-color: #22D3EE !important;
            box-shadow: 0 0 20px rgba(34, 211, 238, 0.1) !important;
        }

        .kpi-label {
            font-size: 0.78rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: #94A3B8;
            margin-bottom: 0.4rem;
        }

        .kpi-value {
            font-size: 1.85rem;
            font-weight: 800;
            color: #F8FAFC;
            line-height: 1.15;
            letter-spacing: -0.02em;
        }

        .kpi-sub {
            font-size: 0.78rem;
            color: #94A3B8;
            margin-top: 0.4rem;
        }

        /* AI Dedicated Highlight Panel */
        .ai-panel {
            background: linear-gradient(145deg, rgba(15, 23, 42, 0.85) 0%, rgba(26, 30, 56, 0.75) 100%) !important;
            backdrop-filter: blur(12px) !important;
            border: 1px solid rgba(139, 92, 246, 0.35) !important;
            border-radius: 12px !important;
            padding: 1.25rem 1.5rem !important;
            margin-bottom: 1.25rem !important;
            box-shadow: 0 0 30px rgba(139, 92, 246, 0.08) !important;
        }

        .ai-kpi-card {
            border-color: rgba(139, 92, 246, 0.35) !important;
        }

        .ai-kpi-card:hover {
            border-color: #A78BFA !important;
            box-shadow: 0 0 22px rgba(167, 139, 250, 0.14) !important;
        }

        .ai-badge {
            background: rgba(139, 92, 246, 0.18);
            color: #C4B5FD;
            border: 1px solid rgba(139, 92, 246, 0.4);
            font-size: 0.72rem;
            font-weight: 700;
            padding: 0.2rem 0.55rem;
            border-radius: 9999px;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }

        /* Semantic Badges */
        .badge {
            display: inline-block;
            padding: 0.22rem 0.65rem;
            border-radius: 9999px;
            font-size: 0.76rem;
            font-weight: 700;
            letter-spacing: 0.03em;
            text-transform: uppercase;
            white-space: nowrap;
        }

        .badge-healthy {
            background-color: rgba(34, 197, 94, 0.15);
            color: #4ADE80;
            border: 1px solid rgba(34, 197, 94, 0.35);
        }

        .badge-monitoring {
            background-color: rgba(245, 158, 11, 0.15);
            color: #FBBF24;
            border: 1px solid rgba(245, 158, 11, 0.35);
        }

        .badge-at-risk, .badge-high {
            background-color: rgba(239, 68, 68, 0.15);
            color: #F87171;
            border: 1px solid rgba(239, 68, 68, 0.35);
        }

        .badge-critical {
            background-color: rgba(220, 38, 38, 0.25);
            color: #FCA5A5;
            border: 1px solid #DC2626;
            animation: pulse-danger 2s infinite ease-in-out;
        }

        .badge-medium {
            background-color: rgba(245, 158, 11, 0.15);
            color: #FBBF24;
            border: 1px solid rgba(245, 158, 11, 0.35);
        }

        .badge-low {
            background-color: rgba(34, 197, 94, 0.12);
            color: #4ADE80;
            border: 1px solid rgba(34, 197, 94, 0.25);
        }

        .badge-active {
            background-color: rgba(239, 68, 68, 0.2);
            color: #F87171;
            border: 1px solid rgba(239, 68, 68, 0.4);
        }

        .badge-acknowledged {
            background-color: rgba(245, 158, 11, 0.2);
            color: #FBBF24;
            border: 1px solid rgba(245, 158, 11, 0.4);
        }

        .badge-resolved {
            background-color: rgba(34, 197, 94, 0.15);
            color: #4ADE80;
            border: 1px solid rgba(34, 197, 94, 0.35);
        }

        .badge-online {
            background-color: rgba(34, 197, 94, 0.15);
            color: #4ADE80;
            border: 1px solid rgba(34, 197, 94, 0.35);
        }

        .badge-offline {
            background-color: rgba(148, 163, 184, 0.12);
            color: #94A3B8;
            border: 1px solid rgba(148, 163, 184, 0.25);
        }

        .badge-ai {
            background-color: rgba(139, 92, 246, 0.18);
            color: #C4B5FD;
            border: 1px solid rgba(139, 92, 246, 0.4);
        }

        .badge-default {
            background-color: rgba(23, 32, 51, 0.8);
            color: #CBD5E1;
            border: 1px solid rgba(148, 163, 184, 0.15);
        }

        /* Prioritized Alert Cards with Subtle Severity Glow */
        .alert-card {
            background: rgba(15, 23, 42, 0.8) !important;
            backdrop-filter: blur(12px) !important;
            border: 1px solid rgba(148, 163, 184, 0.15) !important;
            border-left: 4px solid #EF4444 !important;
            border-radius: 10px !important;
            padding: 1rem 1.15rem !important;
            margin-bottom: 0.85rem !important;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3) !important;
        }

        .alert-card-critical {
            border-left-color: #DC2626 !important;
            background: linear-gradient(90deg, rgba(220, 38, 38, 0.12) 0%, rgba(15, 23, 42, 0.82) 100%) !important;
            box-shadow: 0 0 25px rgba(220, 38, 38, 0.08), 0 4px 16px rgba(0, 0, 0, 0.3) !important;
        }

        .alert-card-high {
            border-left-color: #F97316 !important;
            background: linear-gradient(90deg, rgba(249, 115, 22, 0.1) 0%, rgba(15, 23, 42, 0.82) 100%) !important;
        }

        .alert-card-medium {
            border-left-color: #F59E0B !important;
            background: linear-gradient(90deg, rgba(245, 158, 11, 0.08) 0%, rgba(15, 23, 42, 0.82) 100%) !important;
        }

        .alert-card-low {
            border-left-color: #22C55E !important;
            background: linear-gradient(90deg, rgba(34, 197, 94, 0.06) 0%, rgba(15, 23, 42, 0.82) 100%) !important;
        }

        /* Empty States */
        .empty-state-box {
            background: rgba(15, 23, 42, 0.72) !important;
            backdrop-filter: blur(12px) !important;
            border: 1px dashed rgba(148, 163, 184, 0.25) !important;
            border-radius: 12px !important;
            padding: 2.5rem 1.5rem !important;
            text-align: center !important;
            margin: 1rem 0 !important;
        }

        .empty-state-icon {
            font-size: 2.2rem;
            margin-bottom: 0.5rem;
        }

        .empty-state-title {
            font-size: 1.1rem;
            font-weight: 700;
            color: #F8FAFC !important;
            margin-bottom: 0.35rem;
        }

        .empty-state-desc {
            font-size: 0.88rem;
            color: #94A3B8 !important;
            max-width: 480px;
            margin: 0 auto;
        }

        /* Sidebar Branding Box */
        .sidebar-brand-box {
            background: linear-gradient(135deg, rgba(34, 211, 238, 0.12) 0%, rgba(139, 92, 246, 0.08) 100%) !important;
            border: 1px solid rgba(34, 211, 238, 0.28) !important;
            border-radius: 10px !important;
            padding: 0.85rem 1rem !important;
            margin-bottom: 1.25rem !important;
            box-shadow: 0 0 22px rgba(34, 211, 238, 0.07) !important;
        }

        .sidebar-brand-title {
            font-size: 1.35rem;
            font-weight: 800;
            color: #F8FAFC !important;
            letter-spacing: -0.02em;
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }

        .sidebar-brand-tagline {
            font-size: 0.72rem;
            color: #22D3EE !important;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-top: 0.25rem;
        }

        .sidebar-user-box {
            background: rgba(15, 23, 42, 0.75) !important;
            border: 1px solid rgba(148, 163, 184, 0.15) !important;
            border-radius: 10px !important;
            padding: 0.85rem 1rem !important;
            margin-top: 1.25rem !important;
            margin-bottom: 0.75rem !important;
        }

        .sidebar-user-name {
            font-size: 0.92rem;
            font-weight: 700;
            color: #F8FAFC;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .sidebar-user-role {
            font-size: 0.76rem;
            font-weight: 700;
            color: #22D3EE;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-top: 0.25rem;
        }

        .sidebar-category-header {
            font-size: 0.72rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: #94A3B8;
            padding: 0.5rem 0.5rem 0.25rem 0.5rem;
            margin-top: 0.75rem;
        }

        @keyframes pulse-danger {
            0% { box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.4); }
            70% { box-shadow: 0 0 0 6px rgba(220, 38, 38, 0); }
            100% { box-shadow: 0 0 0 0 rgba(220, 38, 38, 0); }
        }
        </style>
        """,
        unsafe_allow_html=True
    )


# ==============================================================================
# REUSABLE UI HELPER FUNCTIONS
# ==============================================================================

def render_top_bar(current_page: str, current_section: str = "OPERATIONS", role: str = "Farmer"):
    """
    Renders a unified mission-control top bar across the main dashboard area.
    Shows breadcrumbs on the left and live system status + role pill on the right.
    """
    st.markdown(
        f"""
        <div class="vetra-top-bar">
            <div class="vetra-breadcrumb">
                <span style="color: #22D3EE; font-weight: 700;">VETRA</span>
                <span style="color: #64748B;">/</span>
                <span>{current_section.upper()}</span>
                <span style="color: #64748B;">/</span>
                <strong>{current_page}</strong>
            </div>
            <div class="vetra-top-meta">
                <span class="badge badge-online">● SYSTEM ONLINE</span>
                <span style="font-size: 0.8rem; color: #94A3B8;">Role: <strong style="color: #22D3EE;">{role.upper()}</strong></span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_dashboard_hero():
    """
    Renders the premium VETRA AI Livestock Health Command Center hero area.
    """
    st.markdown(
        """
        <div class="vetra-hero-box">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
                <div>
                    <div style="font-size: 0.72rem; font-weight: 800; color: #22D3EE; text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 0.25rem;">
                        ◈ AI-POWERED LIVESTOCK HEALTH INTELLIGENCE PLATFORM
                    </div>
                    <div style="font-size: 1.95rem; font-weight: 800; color: #F8FAFC; letter-spacing: -0.025em; line-height: 1.15;">
                        VETRA COMMAND CENTER
                    </div>
                    <div style="font-size: 0.9rem; color: #CBD5E1; margin-top: 0.35rem; font-weight: 400;">
                        Real-time biometric telemetry, predictive disease warning, multimodal vision & clinical surveillance
                    </div>
                </div>
                <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                    <span class="hero-tag">● REAL-TIME MONITORING</span>
                    <span class="hero-tag" style="color: #A78BFA; border-color: rgba(167, 139, 250, 0.3); background: rgba(167, 139, 250, 0.1);">◈ PREDICTIVE HEALTH</span>
                    <span class="hero-tag" style="color: #FBBF24; border-color: rgba(251, 191, 36, 0.3); background: rgba(251, 191, 36, 0.1);">⚠️ EARLY WARNING</span>
                    <span class="hero-tag" style="color: #4ADE80; border-color: rgba(74, 222, 128, 0.3); background: rgba(74, 222, 128, 0.1);">🩺 VETERINARY INTELLIGENCE</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def page_header(title: str, subtitle: str, badge: Optional[str] = None, badge_color: str = "#22D3EE"):
    """
    Renders a standardized, high-contrast page header with an optional pill badge.
    """
    badge_html = f'<span style="background: {badge_color}18; color: {badge_color}; border: 1px solid {badge_color}45; font-size: 0.75rem; font-weight: 700; padding: 0.2rem 0.65rem; border-radius: 9999px;">{badge}</span>' if badge else ""
    st.markdown(
        f"""
        <div class="page-header-box">
            <div style="display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap;">
                <h1 class="page-header-title">{title}</h1>
                {badge_html}
            </div>
            <div class="page-header-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def section_header(title: str, subtitle: Optional[str] = None, badge: Optional[str] = None):
    """
    Renders a consistent, high-contrast section heading with optional subtitle and badge.
    """
    badge_html = f'<span class="badge badge-default">{badge}</span>' if badge else ""
    sub_html = f'<div class="section-header-subtitle">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f"""
        <div class="section-header-box">
            <div>
                <div class="section-header-title">{title}</div>
                {sub_html}
            </div>
            {badge_html}
        </div>
        """,
        unsafe_allow_html=True
    )


def render_ai_section_header(title: str, subtitle: Optional[str] = None, badge: Optional[str] = "AI INTELLIGENCE"):
    """
    Renders an AI intelligence section header with cyan/purple indicator.
    """
    badge_html = f'<span class="ai-badge">{badge}</span>' if badge else ""
    sub_html = f'<div class="section-header-subtitle">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f"""
        <div class="section-header-box" style="border-bottom-color: rgba(139, 92, 246, 0.25);">
            <div>
                <div class="section-header-title" style="color: #F8FAFC;">
                    <span style="color: #22D3EE; margin-right: 0.4rem;">◈</span> {title}
                </div>
                {sub_html}
            </div>
            {badge_html}
        </div>
        """,
        unsafe_allow_html=True
    )


def kpi_card(label: str, value: Any, subtext: Optional[str] = None, trend: Optional[str] = None, border_color: Optional[str] = None):
    """
    Renders a premium high-contrast dark KPI card floating on the AI background.
    """
    border_style = f"border-color: {border_color};" if border_color else ""
    trend_html = f'<div style="font-size: 0.78rem; font-weight: 600; color: #22D3EE; margin-top: 0.25rem;">{trend}</div>' if trend else ""
    sub_html = f'<div class="kpi-sub">{subtext}</div>' if subtext else ""
    st.markdown(
        f"""
        <div class="kpi-card" style="{border_style}">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            {trend_html}
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True
    )


def render_ai_kpi_card(label: str, value: Any, subtext: Optional[str] = None, badge: str = "◈ PREDICTIVE AI", trend: Optional[str] = None):
    """
    Renders an AI-specific KPI card with cyan/purple accents.
    """
    trend_html = f'<div style="font-size: 0.78rem; font-weight: 600; color: #22D3EE; margin-top: 0.25rem;">{trend}</div>' if trend else ""
    sub_html = f'<div class="kpi-sub">{subtext}</div>' if subtext else ""
    st.markdown(
        f"""
        <div class="kpi-card ai-kpi-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
                <span class="kpi-label" style="margin-bottom: 0;">{label}</span>
                <span class="ai-badge" style="font-size: 0.65rem; padding: 0.15rem 0.45rem;">{badge}</span>
            </div>
            <div class="kpi-value" style="color: #F8FAFC;">{value}</div>
            {trend_html}
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True
    )


def status_badge(text: str, variant: str = "default") -> str:
    """
    Returns an HTML string for a semantic status badge.
    Available variants: healthy, monitoring, at-risk, critical, active, resolved, online, offline, ai, default.
    """
    variant_norm = variant.lower().replace(" ", "-").replace("_", "-")
    cls_name = f"badge-{variant_norm}" if f"badge-{variant_norm}" in [
        "badge-healthy", "badge-monitoring", "badge-at-risk", "badge-critical",
        "badge-medium", "badge-low", "badge-active", "badge-acknowledged",
        "badge-resolved", "badge-online", "badge-offline", "badge-ai"
    ] else "badge-default"
    return f'<span class="badge {cls_name}">{text}</span>'


def empty_state(title: str, message: str, icon: str = "📡"):
    """
    Renders a modern, professional dark empty state container.
    """
    st.markdown(
        f"""
        <div class="empty-state-box">
            <div class="empty-state-icon">{icon}</div>
            <div class="empty-state-title">{title}</div>
            <div class="empty-state-desc">{message}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def ai_banner(title: str, description: str, badge: str = "AI CLINICAL INTELLIGENCE"):
    """
    Renders an AI intelligence card with a subtle purple accent.
    """
    st.markdown(
        f"""
        <div class="ai-panel">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                <div style="font-size: 1.15rem; font-weight: 700; color: #F8FAFC;">{title}</div>
                <span class="ai-badge">{badge}</span>
            </div>
            <div style="font-size: 0.9rem; color: #CBD5E1; line-height: 1.5;">{description}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def apply_plotly_theme(fig, height: int = 350, title: Optional[str] = None):
    """
    Applies unified high-contrast dark AI theme styling to any Plotly figure.
    """
    layout_update = {
        "template": "plotly_dark",
        "paper_bgcolor": "rgba(15, 23, 42, 0.75)",
        "plot_bgcolor": "rgba(10, 16, 32, 0.85)",
        "font": {"family": "Inter, sans-serif", "color": "#CBD5E1", "size": 12},
        "margin": {"l": 40, "r": 25, "t": 45 if title else 25, "b": 40},
        "height": height,
    }
    if title:
        layout_update["title"] = {
            "text": title,
            "font": {"color": "#F8FAFC", "size": 14, "family": "Inter, sans-serif"}
        }
    fig.update_layout(**layout_update)
    fig.update_xaxes(
        gridcolor="rgba(148, 163, 184, 0.08)",
        zerolinecolor="rgba(148, 163, 184, 0.12)",
        tickfont={"color": "#94A3B8"},
        title_font={"color": "#CBD5E1"}
    )
    fig.update_yaxes(
        gridcolor="rgba(148, 163, 184, 0.08)",
        zerolinecolor="rgba(148, 163, 184, 0.12)",
        tickfont={"color": "#94A3B8"},
        title_font={"color": "#CBD5E1"}
    )
    return fig

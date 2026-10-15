"""WhatsApp Chat Analyzer — Authentic WhatsApp Native UI/UX Web Application.

Matches the exact pixel layout from the reference image (media_1792003835526.png):
- Full-bleed Top Dark Teal Banner (#075E54) with Outline Chat Bubble & exact typography
- Full-bleed Warm Cream Canvas (#ECE5DD)
- Centered Dashed Upload Card with Green Tray Icon, Upload WhatsApp Chat, Drag & Drop text,
  and Green Gradient "Browse Files" button (#21C36B -> #128C7E)
- Full-bleed Bottom Dark Teal Banner (#075E54) with Instant Insights summary text
- Full WhatsApp Dashboard with Overview, Participants, Sentiments & Words, Activity, Chat Breakdown
"""
import os
import sys
import zipfile

# Ensure current repository root is in Python sys.path on Streamlit Cloud & remote servers
import os
import sys
import tempfile
import zipfile

# 1. Add current directory to sys.path
_CUR_DIR = os.path.dirname(os.path.abspath(__file__))
if _CUR_DIR not in sys.path:
    sys.path.insert(0, _CUR_DIR)
if os.getcwd() not in sys.path:
    sys.path.insert(0, os.getcwd())

# 2. In-Memory Direct ZipImport (No disk permissions needed on Streamlit Cloud)
_ZIP_CANDIDATES = [
    os.path.join(_CUR_DIR, "whatsapp_chat_analyzer_deploy.zip"),
    os.path.join(os.getcwd(), "whatsapp_chat_analyzer_deploy.zip"),
    "whatsapp_chat_analyzer_deploy.zip"
]
for _cand in _ZIP_CANDIDATES:
    if os.path.exists(_cand):
        _abs_cand = os.path.abspath(_cand)
        if _abs_cand not in sys.path:
            sys.path.insert(0, _abs_cand)
        try:
            _tmp_dir = os.path.join(tempfile.gettempdir(), "wa_extracted")
            os.makedirs(_tmp_dir, exist_ok=True)
            with zipfile.ZipFile(_cand, "r") as _z:
                _z.extractall(_tmp_dir)
            if _tmp_dir not in sys.path:
                sys.path.insert(0, _tmp_dir)
        except Exception:
            pass
import streamlit as st

# Automatically invalidate stale subpackage cache on re-runs
for mod_name in list(sys.modules.keys()):
    if mod_name.startswith("whatsapp_analyzer"):
        del sys.modules[mod_name]

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from wordcloud import WordCloud
import matplotlib.pyplot as plt

from whatsapp_analyzer.models import Message, ParseResult
from whatsapp_analyzer.parser import parse_chat_file
from whatsapp_analyzer.analyzers import (
    analyze_chat,
    SearchAnalyzer,
    UserAnalyzer,
    TimelineAnalyzer,
    MediaAnalyzer,
    SentimentAnalyzer,
    ComparisonAnalyzer
)

# Page configuration
st.set_page_config(
    page_title="Analyze your WhatsApp Chat in Seconds",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Exact colors sampled from media_1792003835526.png & WhatsApp Design System
COLOR_TOP_BANNER     = "#075E54"   # Exact (7, 94, 84)
COLOR_FOOTER_BANNER  = "#075E54"   # Exact (7, 94, 84)
COLOR_CANVAS_BG      = "#ECE5DD"   # Exact (236, 229, 221)
COLOR_BUTTON_GREEN   = "#21C36B"   # Exact (33, 195, 107)
COLOR_ACCENT_TEAL    = "#128C7E"
COLOR_OUTGOING_BUBBLE= "#DCF8C6"
COLOR_INCOMING_BUBBLE= "#FFFFFF"
COLOR_TEXT_PRIMARY   = "#111B21"
COLOR_TEXT_SECONDARY = "#54656F"   # WCAG AA Compliant (>4.5:1 ratio)
COLOR_BORDER_DASHED  = "#B8C5BD"

# Precise CSS styling matching reference image & desktop HCI ergonomics
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;500;600;700&display=swap');

    :root {{
        --wa-teal: {COLOR_TOP_BANNER};
        --wa-teal-light: {COLOR_ACCENT_TEAL};
        --wa-btn-green: {COLOR_BUTTON_GREEN};
        --wa-canvas: {COLOR_CANVAS_BG};
        --wa-surface: #FFFFFF;
        --wa-border: #E9EDEF;
        --wa-text-primary: {COLOR_TEXT_PRIMARY};
        --wa-text-secondary: {COLOR_TEXT_SECONDARY};
        --wa-dashed: {COLOR_BORDER_DASHED};
    }}

    /* Hide Streamlit default header, toolbar, and footer for seamless full-bleed look */
    header[data-testid="stHeader"] {{
        display: none !important;
    }}
    #MainMenu {{
        visibility: hidden !important;
    }}
    footer {{
        visibility: hidden !important;
    }}

    html, body {{
        font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif !important;
        color: {COLOR_TEXT_PRIMARY};
        margin: 0 !important;
        padding: 0 !important;
        overflow-x: hidden !important;
    }}

    /* Full canvas background */
    .stApp {{
        background-color: {COLOR_CANVAS_BG} !important;
    }}

    /* Remove Streamlit default container paddings */
    .block-container {{
        padding: 0 !important;
        margin: 0 !important;
        max-width: 100% !important;
    }}

    /* TOP BANNER — Exact match to reference */
    .top-header-banner {{
        background-color: {COLOR_TOP_BANNER};
        color: #FFFFFF;
        padding: 1.1rem 3.5rem 1rem 3.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.12);
        width: 100%;
        box-sizing: border-box;
    }}
    .top-header-row {{
        display: flex;
        align-items: center;
        gap: 1.2rem;
        max-width: 1200px;
        margin: 0 auto;
    }}
    .top-header-icon {{
        width: 36px;
        height: 36px;
        flex-shrink: 0;
    }}
    .top-header-icon svg {{
        width: 100%;
        height: 100%;
        fill: none;
        stroke: #FFFFFF;
        stroke-width: 2.2;
    }}
    .top-header-text {{
        display: flex;
        flex-direction: column;
    }}
    .top-header-title {{
        font-size: 1.55rem;
        font-weight: 700;
        letter-spacing: -0.01em;
        line-height: 1.2;
        color: #FFFFFF;
        margin: 0;
    }}
    .top-header-subtitle {{
        font-size: 0.92rem;
        color: #D1E7DD;
        margin-top: 0.2rem;
        font-weight: 400;
    }}

    /* DASHED UPLOAD CARD CONTAINER (Desktop HCI Single-Viewport Fit) */
    [data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"]:has([data-testid="stFileUploader"]) {{
        border: 2px dashed {COLOR_BORDER_DASHED} !important;
        background-color: transparent !important;
        border-radius: 18px !important;
        padding: 2.2rem 2.2rem 1.8rem 2.2rem !important;
        text-align: center !important;
        box-shadow: none !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
    }}
    [data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"]:has([data-testid="stFileUploader"]):hover {{
        border-color: {COLOR_BUTTON_GREEN} !important;
        box-shadow: 0 4px 20px rgba(33, 195, 107, 0.08) !important;
    }}

    .upload-tray-icon {{
        width: 44px;
        height: 44px;
        margin: 0 auto 0.6rem auto;
    }}
    .upload-tray-icon svg {{
        width: 100%;
        height: 100%;
    }}
    .upload-card-title {{
        font-size: 1.35rem;
        font-weight: 700;
        color: {COLOR_TEXT_PRIMARY};
        margin-bottom: 0.35rem;
        text-align: center;
    }}
    .upload-card-subtitle {{
        font-size: 0.92rem;
        color: {COLOR_TEXT_SECONDARY};
        margin-bottom: 1.1rem;
        text-align: center;
    }}
    .upload-card-instructions {{
        font-size: 0.82rem;
        color: {COLOR_TEXT_SECONDARY};
        margin-top: 1.1rem;
        margin-bottom: 0.5rem;
        text-align: center;
        line-height: 1.4;
    }}
    .upload-card-instructions strong {{
        color: {COLOR_TEXT_PRIMARY};
        font-weight: 700;
    }}

    /* STREAMLIT FILE UPLOADER RESHAPING */
    [data-testid="stFileUploader"] {{
        background: transparent !important;
        margin: 0.5rem auto !important;
        display: flex !important;
        justify-content: center !important;
    }}
    [data-testid="stFileUploaderDropzone"] {{
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
        min-height: auto !important;
        display: flex !important;
        justify-content: center !important;
    }}
    [data-testid="stFileUploaderDropzoneInstructions"] {{
        display: none !important;
    }}
    /* Green pill Browse Files button matching WhatsApp CTA */
    [data-testid="stFileUploaderDropzone"] button {{
        background: linear-gradient(180deg, {COLOR_BUTTON_GREEN} 0%, #16A34A 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.65rem 1.6rem !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        box-shadow: 0 4px 12px rgba(33, 195, 107, 0.35) !important;
        cursor: pointer !important;
        transition: transform 0.15s ease, box-shadow 0.15s ease !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        margin: 0 auto !important;
    }}
    [data-testid="stFileUploaderDropzone"] button:hover {{
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 16px rgba(33, 195, 107, 0.5) !important;
    }}
    [data-testid="stFileUploaderDropzone"] button > div {{
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: auto !important;
        margin: 0 auto !important;
    }}
    [data-testid="stFileUploaderDropzone"] button span[data-has-shortcut] {{
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 8px !important;
    }}
    /* Ensure icon is vertically aligned and crisp */
    [data-testid="stFileUploaderDropzone"] button span[data-testid="stIconMaterial"] {{
        font-size: 1.15rem !important;
        line-height: 1 !important;
        vertical-align: middle !important;
    }}
    /* Hide the original Upload text by setting font-size to 0 */
    [data-testid="stFileUploaderDropzone"] button [data-testid="stMarkdownContainer"] {{
        display: inline-flex !important;
        align-items: center !important;
    }}
    [data-testid="stFileUploaderDropzone"] button [data-testid="stMarkdownContainer"] p {{
        font-size: 0 !important;
        line-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        display: inline-flex !important;
        align-items: center !important;
    }}
    /* In-flow replacement with authentic true width so it perfectly centers */
    [data-testid="stFileUploaderDropzone"] button [data-testid="stMarkdownContainer"] p::after {{
        content: "Browse Files" !important;
        font-size: 0.95rem !important;
        line-height: 1.2 !important;
        font-weight: 600 !important;
        color: #FFFFFF !important;
        display: inline-block !important;
        white-space: nowrap !important;
        visibility: visible !important;
    }}

    .demo-row-header {{
        text-align: center;
        font-size: 0.8rem;
        font-weight: 600;
        color: {COLOR_TEXT_SECONDARY};
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin: 1.2rem 0 0.5rem 0;
    }}

    /* Styled Demo Test Buttons */
    div.st-key-landing_demo_android button,
    div.st-key-landing_demo_ios button {{
        background-color: #FFFFFF !important;
        color: {COLOR_TOP_BANNER} !important;
        border: 1.5px solid #C4D3CC !important;
        border-radius: 24px !important;
        padding: 0.6rem 1.4rem !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.04) !important;
        transition: all 0.15s ease !important;
    }}
    div.st-key-landing_demo_android button:hover,
    div.st-key-landing_demo_ios button:hover {{
        background-color: #F0FDF4 !important;
        border-color: {COLOR_BUTTON_GREEN} !important;
        color: #0B6644 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 10px rgba(33, 195, 107, 0.15) !important;
    }}

    /* Control bar upload reset button */
    div.st-key-dash_reset_btn button {{
        background-color: #FFFFFF !important;
        color: {COLOR_TOP_BANNER} !important;
        border: 1.5px solid #C4D3CC !important;
        border-radius: 8px !important;
        height: 42px !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        transition: all 0.15s ease !important;
    }}
    div.st-key-dash_reset_btn button:hover {{
        background-color: #F0FDF4 !important;
        border-color: {COLOR_BUTTON_GREEN} !important;
        color: #0B6644 !important;
    }}

    /* Selectbox in control bar */
    div.st-key-dash_user_select [data-baseweb="select"] > div {{
        border-radius: 8px !important;
        border: 1px solid #E9EDEF !important;
        height: 42px !important;
        background-color: #FFFFFF !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
    }}

    /* BOTTOM BANNER — Exact match to reference */
    .bottom-footer-banner {{
        background-color: {COLOR_FOOTER_BANNER};
        color: #FFFFFF;
        padding: 0.9rem 2.5rem;
        text-align: center;
        font-size: 0.88rem;
        line-height: 1.45;
        width: 100%;
        box-sizing: border-box;
        margin-top: 1.5rem;
    }}
    .bottom-footer-banner strong {{
        font-weight: 700;
        color: #FFFFFF;
    }}

    /* Responsive Grid Layouts */
    .summary-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
        gap: 16px;
    }}

    /* Quick Insights 4-Card Responsive Grid */
    .quick-insights-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 12px;
        margin-bottom: 16px;
    }}
    .quick-insight-card {{
        background: #FFFFFF;
        border: 1px solid #E9EDEF;
        border-radius: 10px;
        padding: 12px 16px;
        display: flex;
        align-items: center;
        gap: 12px;
        box-shadow: 0 1px 2px rgba(11,20,26,0.04);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }}
    .quick-insight-card:hover {{
        transform: translateY(-1px);
        box-shadow: 0 3px 8px rgba(11,20,26,0.08);
    }}
    .quick-insight-icon {{
        font-size: 1.4rem;
        width: 38px;
        height: 38px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #F0FDF4;
        border-radius: 50%;
        flex-shrink: 0;
    }}
    .quick-insight-label {{
        font-size: 0.76rem;
        color: {COLOR_TEXT_SECONDARY};
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }}
    .quick-insight-val {{
        font-size: 1.05rem;
        font-weight: 700;
        color: {COLOR_TEXT_PRIMARY};
        margin-top: 2px;
    }}

    /* Mobile Responsive Media Queries */
    @media (max-width: 768px) {{
        .top-header-banner {{
            padding: 0.85rem 1rem !important;
        }}
        .top-header-title {{
            font-size: 1.25rem !important;
        }}
        .top-header-subtitle {{
            font-size: 0.82rem !important;
        }}
        [data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"]:has([data-testid="stFileUploader"]) {{
            padding: 1.5rem 1rem !important;
            margin: 0 0.5rem !important;
        }}
        .bottom-footer-banner {{
            padding: 0.75rem 1rem !important;
            font-size: 0.8rem !important;
        }}
        .stTabs [data-baseweb="tab-list"] {{
            overflow-x: auto !important;
            flex-wrap: nowrap !important;
            gap: 6px !important;
            padding-bottom: 4px !important;
        }}
        .stTabs [data-baseweb="tab"] {{
            padding: 8px 12px !important;
            font-size: 0.82rem !important;
            white-space: nowrap !important;
        }}
        .status-ring-container {{
            flex-wrap: wrap !important;
            gap: 1rem !important;
        }}
    }}

    /* DASHBOARD ELEMENTS (HCI Ergonomics & Desktop Screen Fit) */
    .stTabs, [data-testid="stHorizontalBlock"] {{
        max-width: 1200px !important;
        margin-left: auto !important;
        margin-right: auto !important;
    }}
    .stTabs {{
        padding: 0 24px !important;
        box-sizing: border-box !important;
    }}
    .wa-card {{
        background: #FFFFFF;
        border: 1px solid #E9EDEF;
        border-radius: 12px;
        padding: 1.2rem;
        box-shadow: 0 1px 3px rgba(11,20,26,0.06);
        margin-bottom: 1rem;
    }}
    .summary-banner {{
        background: linear-gradient(135deg, {COLOR_TOP_BANNER} 0%, {COLOR_ACCENT_TEAL} 100%);
        color: #FFFFFF;
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 4px 10px rgba(7,94,84,0.18);
    }}
    .summary-stat-box {{
        text-align: center;
        padding: 0.5rem;
    }}
    .summary-stat-val {{
        font-size: 1.85rem;
        font-weight: 700;
        line-height: 1.1;
    }}
    .summary-stat-lbl {{
        font-size: 0.78rem;
        opacity: 0.88;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-top: 0.3rem;
    }}

    /* Contact List */
    .contact-item {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.75rem 0.9rem;
        border-bottom: 1px solid #E9EDEF;
        background: #FFFFFF;
        border-radius: 8px;
        margin-bottom: 0.4rem;
    }}
    .contact-left {{
        display: flex;
        align-items: center;
        gap: 0.85rem;
    }}
    .contact-avatar {{
        width: 44px;
        height: 44px;
        border-radius: 50%;
        background: #DFE5E7;
        color: {COLOR_TOP_BANNER};
        font-weight: 700;
        font-size: 1.1rem;
        display: flex;
        align-items: center;
        justify-content: center;
    }}
    .contact-name {{
        font-size: 0.98rem;
        font-weight: 600;
        color: {COLOR_TEXT_PRIMARY};
    }}
    .contact-sub {{
        font-size: 0.8rem;
        color: {COLOR_TEXT_SECONDARY};
    }}
    .contact-badge {{
        background: {COLOR_BUTTON_GREEN};
        color: #FFFFFF;
        font-weight: 700;
        font-size: 0.76rem;
        padding: 0.25rem 0.65rem;
        border-radius: 12px;
    }}

    /* Sentiment Rings */
    .status-ring-container {{
        display: flex;
        align-items: center;
        gap: 1.5rem;
        justify-content: space-around;
        padding: 1rem 0;
    }}
    .status-circle {{
        width: 86px;
        height: 86px;
        border-radius: 50%;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
    }}
    .status-circle.pos {{
        border: 4px solid {COLOR_BUTTON_GREEN};
        background: #F0FDF4;
        color: #166534;
    }}
    .status-circle.neu {{
        border: 4px solid #94A3B8;
        background: #F8FAFC;
        color: #475569;
    }}
    .status-circle.neg {{
        border: 4px solid #EF4444;
        background: #FEF2F2;
        color: #991B1B;
    }}

    /* Word Chips */
    .word-chip {{
        display: inline-block;
        background: {COLOR_OUTGOING_BUBBLE};
        color: {COLOR_TOP_BANNER};
        font-weight: 600;
        font-size: 0.85rem;
        padding: 0.35rem 0.75rem;
        border-radius: 16px;
        margin: 0.25rem;
        border: 1px solid #C8E6C9;
    }}

    /* Emoji Cards */
    .emoji-pill-box {{
        background: #FFFFFF;
        border: 1px solid #E9EDEF;
        border-radius: 10px;
        padding: 0.75rem;
        text-align: center;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
        margin-bottom: 0.5rem;
    }}

    /* Chat Breakdown & Window Styles */
    .chat-breakdown-container {{
        padding: 8px 0 24px 0;
        display: flex;
        flex-direction: column;
        gap: 16px;
    }}
    .chat-breakdown-heading-row {{
        margin-bottom: 4px;
    }}
    .chat-breakdown-title {{
        color: {COLOR_TOP_BANNER};
        font-size: 1.3rem;
        font-weight: 700;
        margin: 0 0 4px 0;
        letter-spacing: -0.01em;
    }}
    .chat-breakdown-sub {{
        color: {COLOR_TEXT_SECONDARY};
        font-size: 0.88rem;
        margin: 0;
        line-height: 1.4;
    }}

    /* Search & Count Controls */
    div.st-key-chat_search_kw [data-baseweb="input"] {{
        border-radius: 8px !important;
        border: 1px solid #D1D7DB !important;
        height: 42px !important;
        background-color: #FFFFFF !important;
        box-shadow: 0 1px 2px rgba(11,20,26,0.04) !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
    }}
    div.st-key-chat_search_kw [data-baseweb="input"]:focus-within {{
        border-color: {COLOR_BUTTON_GREEN} !important;
        box-shadow: 0 0 0 2px rgba(33, 195, 107, 0.25) !important;
    }}
    div.st-key-chat_search_kw input {{
        font-size: 0.92rem !important;
        color: {COLOR_TEXT_PRIMARY} !important;
        padding-left: 12px !important;
    }}
    .chat-count-pill {{
        display: flex;
        align-items: center;
        justify-content: center;
        background: #FFFFFF;
        border: 1px solid #D1D7DB;
        border-radius: 8px;
        height: 42px;
        padding: 0 16px;
        font-size: 0.85rem;
        color: {COLOR_TEXT_SECONDARY};
        box-sizing: border-box;
        white-space: nowrap;
        box-shadow: 0 1px 2px rgba(11,20,26,0.04);
    }}
    .chat-count-pill strong {{
        color: {COLOR_TOP_BANNER};
        margin: 0 4px;
        font-weight: 700;
    }}
    .chat-count-pill.highlight {{
        background: #F0FDF4;
        border-color: {COLOR_BUTTON_GREEN};
        color: #0B6644;
    }}
    .chat-count-pill.highlight strong {{
        color: #0B6644;
    }}

    /* Authentic WhatsApp Chat Container */
    .wa-chat-window {{
        background-color: #EFEAE2;
        border-radius: 12px;
        padding: 24px;
        max-height: 580px;
        overflow-y: auto;
        border: 1px solid #D1D7DB;
        box-shadow: inset 0 1px 3px rgba(11,20,26,0.06);
        margin: 16px 0;
        box-sizing: border-box;
    }}
    .wa-chat-stream {{
        display: flex;
        flex-direction: column;
        width: 100%;
    }}

    /* Clean subtle Date Divider (replaces dotted strip) */
    .chat-date-divider {{
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 20px 0 14px 0;
        position: relative;
        width: 100%;
    }}
    .chat-date-divider::before {{
        content: "";
        position: absolute;
        top: 50%;
        left: 4%;
        right: 4%;
        height: 1px;
        background: #D1D7DB;
        z-index: 1;
    }}
    .chat-date-chip {{
        position: relative;
        z-index: 2;
        background: #FFFFFF;
        color: {COLOR_TEXT_SECONDARY};
        font-size: 0.75rem;
        font-weight: 600;
        padding: 4px 14px;
        border-radius: 8px;
        box-shadow: 0 1px 2px rgba(11,20,26,0.12);
        border: 1px solid #E9EDEF;
        letter-spacing: 0.02em;
        user-select: none;
    }}

    /* Message Rows & Natural Group Spacing */
    .msg-row {{
        display: flex;
        width: 100%;
        box-sizing: border-box;
    }}
    .msg-row.out {{
        justify-content: flex-end;
    }}
    .msg-row.in {{
        justify-content: flex-start;
    }}
    .msg-row.consecutive {{
        margin-top: 3px;
    }}
    .msg-row.new-sender {{
        margin-top: 12px;
    }}

    /* Chat Bubbles */
    .msg-bubble {{
        max-width: 68%;
        min-width: 90px;
        padding: 8px 12px 6px 12px;
        border-radius: 8px;
        position: relative;
        font-size: 14.5px;
        line-height: 1.45;
        box-shadow: 0 1px 1.5px rgba(11,20,26,0.13);
        word-break: break-word;
        overflow-wrap: break-word;
        transition: box-shadow 0.15s ease;
    }}
    .msg-bubble:hover {{
        box-shadow: 0 2px 5px rgba(11,20,26,0.18);
    }}
    .msg-bubble.out {{
        background-color: {COLOR_OUTGOING_BUBBLE};
        border-top-right-radius: 2px;
        color: {COLOR_TEXT_PRIMARY};
    }}
    .msg-bubble.in {{
        background-color: {COLOR_INCOMING_BUBBLE};
        border-top-left-radius: 2px;
        color: {COLOR_TEXT_PRIMARY};
    }}

    .msg-sender {{
        font-size: 0.78rem;
        font-weight: 700;
        margin-bottom: 3px;
        letter-spacing: -0.01em;
        user-select: none;
    }}
    .msg-media-box {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(17,27,33,0.05);
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.82rem;
        font-style: italic;
        color: {COLOR_TEXT_SECONDARY};
        margin-bottom: 4px;
    }}
    .msg-media-icon {{
        font-style: normal;
        font-size: 0.95rem;
    }}
    .msg-text-content {{
        display: inline;
        font-size: 14.5px;
        color: {COLOR_TEXT_PRIMARY};
    }}
    .msg-footer {{
        display: flex;
        justify-content: flex-end;
        align-items: center;
        gap: 4px;
        font-size: 11px;
        color: {COLOR_TEXT_SECONDARY};
        margin-top: 4px;
        margin-left: 14px;
        float: right;
        user-select: none;
    }}
    .blue-ticks {{
        color: #53BDEB;
        font-weight: 700;
        font-size: 12px;
        letter-spacing: -1.5px;
        margin-left: 2px;
        line-height: 1;
    }}

    /* Empty Search State */
    .chat-empty-state {{
        text-align: center;
        padding: 48px 24px;
        color: {COLOR_TEXT_SECONDARY};
    }}
    .chat-empty-icon {{
        font-size: 2.5rem;
        margin-bottom: 12px;
        opacity: 0.8;
    }}
    .chat-empty-title {{
        font-size: 1.15rem;
        font-weight: 700;
        color: {COLOR_TEXT_PRIMARY};
        margin-bottom: 6px;
    }}
    .chat-empty-desc {{
        font-size: 0.9rem;
        color: {COLOR_TEXT_SECONDARY};
        max-width: 440px;
        margin: 0 auto;
        line-height: 1.45;
    }}

    /* Download Analysis Report CTA */
    div.st-key-dl_analysis_report button {{
        background-color: #FFFFFF !important;
        color: {COLOR_TOP_BANNER} !important;
        border: 1.5px solid {COLOR_BUTTON_GREEN} !important;
        border-radius: 8px !important;
        height: 42px !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        box-shadow: 0 1px 3px rgba(11,20,26,0.06) !important;
        transition: all 0.2s ease !important;
    }}
    div.st-key-dl_analysis_report button:hover {{
        background-color: #F0FDF4 !important;
        border-color: {COLOR_ACCENT_TEAL} !important;
        color: {COLOR_TOP_BANNER} !important;
        box-shadow: 0 3px 8px rgba(33, 195, 107, 0.2) !important;
        transform: translateY(-1px) !important;
    }}

    /* Sentiment Legend Cards */
    .sentiment-legend-box {{
        background: #F8FAF9;
        border: 1px solid #E2E8E4;
        border-radius: 10px;
        padding: 16px 20px;
        margin-top: 16px;
    }}
    .sentiment-legend-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
        gap: 12px;
        margin-top: 10px;
    }}
    .sentiment-item-card {{
        background: #FFFFFF;
        border: 1px solid #E9EDEF;
        border-radius: 8px;
        padding: 12px 14px;
        font-size: 0.85rem;
        line-height: 1.45;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }}
    .sentiment-badge-pos {{
        color: #166534;
        background: #DCFCE7;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.78rem;
        display: inline-block;
        margin-bottom: 6px;
    }}
    .sentiment-badge-neu {{
        color: #475569;
        background: #F1F5F9;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.78rem;
        display: inline-block;
        margin-bottom: 6px;
    }}
    .sentiment-badge-neg {{
        color: #991B1B;
        background: #FEE2E2;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.78rem;
        display: inline-block;
        margin-bottom: 6px;
    }}

    /* Assistant Quick Prompt Buttons */
    div[class*="st-key-bot_btn_"] button {{
        background-color: #FFFFFF !important;
        color: {COLOR_TOP_BANNER} !important;
        border: 1px solid #D1D7DB !important;
        border-radius: 20px !important;
        font-size: 0.8rem !important;
        font-weight: 600 !important;
        padding: 6px 12px !important;
        transition: all 0.15s ease !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03) !important;
    }}
    div[class*="st-key-bot_btn_"] button:hover {{
        background-color: #F0FDF4 !important;
        border-color: {COLOR_BUTTON_GREEN} !important;
        color: #0B6644 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 3px 8px rgba(33, 195, 107, 0.15) !important;
    }}

    /* Tab bar indicator */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 12px;
        border-bottom: 2px solid #D1D7DB !important;
        margin-bottom: 1.2rem;
    }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 6px 6px 0 0;
        padding: 10px 18px;
        font-weight: 600;
        font-size: 0.95rem;
        color: {COLOR_TEXT_SECONDARY};
    }}
    .stTabs [aria-selected="true"] {{
        border-bottom: 3px solid {COLOR_TOP_BANNER} !important;
        color: {COLOR_TOP_BANNER} !important;
        font-weight: 700 !important;
    }}

    /* WhatsApp Green Progress Bar */
    div[data-testid="stProgress"] > div > div > div {{
        background-color: {COLOR_BUTTON_GREEN} !important;
    }}
</style>
""", unsafe_allow_html=True)

# Session state initialization
if "parse_result" not in st.session_state:
    st.session_state.parse_result = None
if "chat_filename" not in st.session_state:
    st.session_state.chat_filename = None
if "is_demo" not in st.session_state:
    st.session_state.is_demo = False
if "selected_user" not in st.session_state:
    st.session_state.selected_user = "Overall"
if "bot_messages" not in st.session_state:
    st.session_state.bot_messages = [
        {
            "role": "assistant",
            "content": "Assalam o Alaikum! 👋 Main aapka **WhatsApp Analyzer Assistant** hoon.\n\nAap mujh se is application ke kisi bhi function ya feature ki wazahat (explanation) pooch sakte hain:\n- **Sentiments:** Positive, Neutral aur Negative sentiments kya define karte hain?\n- **Reply Speed:** Average response latency kaise measure hoti hai?\n- **Participants Comparison:** Do members ka aamnay-saamnay muqabla kaise hota hai?\n- **Peak Hours:** Sab se masroof tareen ghantay (active times) kaise calculate hotay hain?\n- **Privacy & Export:** Data security aur chat export karne ka tareeqa.\n\nNiche diye gaye **Quick Topics** par click karein ya apna sawal type karein!"
        }
    ]

def reset_bot_messages():
    st.session_state.bot_messages = [
        {
            "role": "assistant",
            "content": "Assalam o Alaikum! 👋 Chat reset ho chuki hai. Aap mujh se is analyzer ke kisi bhi function ki wazahat pooch sakte hain!"
        }
    ]

def render_bot_markdown(text: str) -> str:
    lines = text.split("\n")
    out_lines = []
    for line in lines:
        line_s = line.strip()
        if line_s.startswith("### "):
            title = html.escape(line_s[4:])
            out_lines.append(f"<div style='font-weight:700; font-size:1.02rem; color:#075E54; margin:6px 0 4px 0;'>{title}</div>")
        elif line_s.startswith("- "):
            item = html.escape(line_s[2:])
            item = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', item)
            item = re.sub(r'\*(.*?)\*', r'<em>\1</em>', item)
            out_lines.append(f"<div style='margin-left:10px; margin-bottom:3px;'>&bull; {item}</div>")
        elif re.match(r'^\d+\.\s', line_s):
            num = line_s.split('.', 1)[0]
            rest = html.escape(line_s.split('.', 1)[1].strip())
            rest = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', rest)
            rest = re.sub(r'\*(.*?)\*', r'<em>\1</em>', rest)
            out_lines.append(f"<div style='margin-left:10px; margin-bottom:3px;'><strong>{num}.</strong> {rest}</div>")
        elif line_s == "":
            out_lines.append("<div style='height:6px;'></div>")
        else:
            esc = html.escape(line_s)
            esc = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', esc)
            esc = re.sub(r'\*(.*?)\*', r'<em>\1</em>', esc)
            out_lines.append(f"<div>{esc}</div>")
    return "".join(out_lines)

def get_assistant_explanation(query: str) -> str:
    q = query.lower().strip()
    
    # 1. Sentiment Analysis
    if any(k in q for k in ["sentiment", "positive", "negative", "neutral", "jazbaat", "mood", "feeling"]):
        return (
            "### 🔤 Sentiment Analysis (Positive, Neutral, Negative) Kya Hai?\n\n"
            "Sentiment Analysis aapki chat ke **lahjay (tone)** aur jazbaat ka andaza lagata hai:\n\n"
            "- 🟢 **Positive (Khushgawar Mood):**\n"
            "  - Yeh un messages ko count karta hai jin mein khushi, tareef, razamandi, ya appreciation ho.\n"
            "  - **Keywords:** *zabardast, behtareen, shukriya, thanks, awesome, good, mubarak, acha, sahi, super, congratulations*.\n"
            "  - **Emojis:** ❤️, 😊, 👍, 🎉, 🔥, ✨, 🥳, 🙌.\n\n"
            "- ⚪ **Neutral (Mamool / Factual Data):**\n"
            "  - Yeh normal baat-cheet hoti hai jismein koi emotional polarity nahi hoti (maslan links share karna, sawalat poochna, meeting time set karna, routine status updates).\n"
            "  - **Example:** *'Maine requirements doc share kar diya hai'*, *'Meeting 3:00 PM pe rakhein?'*.\n\n"
            "- 🔴 **Negative (Shikayat, Uljhan, ya Afsos):**\n"
            "  - Yeh un messages ko count karta hai jin mein shikayat, masla, maazrat (apology), ya pareshani ho.\n"
            "  - **Keywords:** *sorry, late, problem, issue, ghalat, kharab, masla, pareshan, bekaar, afsos, hate, fail*.\n"
            "  - **Emojis:** 😢, 😭, 💔, 😡, 😞, 👎.\n\n"
            "📌 **Calculation Rule:** Har message mein Positive aur Negative words/emojis ka score compare hota hai. Agar positive zyada ho toh Positive, agar negative zyada ho toh Negative, aur agar barabar ho toh Neutral!"
        )
        
    # 2. Reply Speed / Response Time
    elif any(k in q for k in ["reply", "speed", "response", "latency", "der", "late", "leaderboard", "interchange"]):
        return (
            "### ⏱️ Average Reply Speed (Response Latency) Kaise Calculate Hoti Hai?\n\n"
            "Yeh feature batata hai ke jab ek shakhs message karta hai, toh doosra shakhs aam taur par **kitne minutes mein jawab (reply)** deta hai:\n\n"
            "1. **Interchange Track:** System un do consecutive messages ko dekhta hai jahan **Sender badal gaya ho** (maslan Ali ke message ke baad Bilal ka message).\n"
            "2. **Time Difference:** Dono messages ke timestamps ka farq (difference in minutes) calculate hota hai.\n"
            "3. **Threshold Filter:** Agar do messages ke darmiyan 12 ghantay se zyada ka gap ho, toh use reply nahi balkay nayi conversation maana jata hai aur exclude kar diya jata hai.\n"
            "4. **Average & Leaderboard:** Har user ke tamam reply minutes ka average nikaal kar 🥇 Gold, 🥈 Silver, aur 🥉 Bronze medals diye jaate hain:\n"
            "   - ⚡ **Fast:** < 5 minutes\n"
            "   - 🕒 **Steady:** 5 - 20 minutes\n"
            "   - ⏳ **Relaxed:** > 20 minutes"
        )
        
    # 3. Participant Rankings & 2-User Head-to-Head Comparison
    elif any(k in q for k in ["participant", "member", "ranking", "comparison", "compare", "head to head", "vs"]):
        return (
            "### 👥 Participants & Comparison Feature Kya Karta Hai?\n\n"
            "- **Participant Rankings:** Chat mein mojood har shakhs ke total messages, total words, media count, aur **Share of Total (%)** dikhata hai taake pata chale sab se zyada active kaun hai.\n"
            "- **⚡ 2-User Head-to-Head Comparison:**\n"
            "  - Aap kisi bhi do doston ya group members ko select kar sakte hain.\n"
            "  - Yeh ek comparative progress bar aur table banata hai jismein **Messages Share**, **Average Words per Message**, aur **Reply Speed** ka aamnay-saamnay muqabla hota hai!"
        )
        
    # 4. Activity & Timeline (Peak Hours & Busiest Day)
    elif any(k in q for k in ["activity", "timeline", "peak", "hour", "busiest", "waqt", "time", "day", "weekly", "hafta"]):
        return (
            "### 📈 Activity & Timeline Analytics Kaise Kaam Karti Hai?\n\n"
            "- ⏰ **Most Active Time (Peak Hours):** Har message ke timestamp se ghantay (00:00 se 23:00) extract kiye jaate hain. Bar chart dikhata hai ke din ke kis hissay (maslan Subah 9 baje ya Raat 10 baje) chat sab se tez hoti hai.\n"
            "- 📅 **Weekly Pattern (Day of Week):** Peer (Monday) se Itwaar (Sunday) tak har din ka message volume dikhata hai, jis se pata chalta hai ke **Busiest Day** kaun sa hai."
        )
        
    # 5. Word Cloud, Top Words & Emojis
    elif any(k in q for k in ["word", "emoji", "stopword", "cloud", "alfaz", "chip"]):
        return (
            "### 🔤 Top Words, Word Cloud aur Emojis Analytics\n\n"
            "- **Stopwords Filtering:** Baat-cheet mein jo aam lafz baar baar aate hain lekin koi khaas matlab nahi rakhte (maslan English ke: *the, is, and, to* aur Roman Urdu ke: *hai, ka, ki, ke, yeh, wo, tha, ko*) unko automatically filter kar diya jata hai.\n"
            "- **Word Chips & Cloud:** Filter hone ke baad jo ahem aur meaningful lafz sab se zyada istemal hue hain, unki frequency dikhayi jaati hai.\n"
            "- **Top Emojis Grid:** Chat mein istemal hone wale tamam emojis ko count karke rank karta hai."
        )
        
    # 6. Chat Breakdown & Search & Export Report
    elif any(k in q for k in ["breakdown", "chat breakdown", "search", "ticks", "report", "download", "filter"]):
        return (
            "### 📱 Chat Breakdown, Search aur Export Report\n\n"
            "- **Authentic WhatsApp Bubbles:** Outgoing messages mint-green (`#DCF8C6`) mein right-aligned aur double blue ticks (`✓✓`) ke saath aate hain; incoming messages white (`#FFFFFF`) mein left-aligned hotay hain.\n"
            "- **Keyword Search:** Aap kisi bhi lafz, link ya sender ka naam likh kar messages ko instantly filter kar sakte hain.\n"
            "- **Date Dividers:** Mukhtalif tareekhon ke darmiyan WhatsApp style ka date chip ban jata hai.\n"
            "- **📥 Download Analysis Report:** Ek click par summary statistics aur key metrics ki `.txt` report download kar sakte hain."
        )
        
    # 7. Privacy & Security
    elif any(k in q for k in ["privacy", "safe", "security", "data", "mehfooz", "hifazat", "store"]):
        return (
            "### 🔒 Privacy aur Data Security Ki Wazahat\n\n"
            "Aapka chat data **100% Mehfooz aur Private** hai:\n\n"
            "1. **Zero External Upload:** Aapka export file kisi teesri party ya cloud server par nahi bheja jata.\n"
            "2. **Local Browser Memory:** Data sirf aapke apne computer/session ki temporary memory mein parse hota hai.\n"
            "3. **No Database Storage:** App band karne par ya 'Upload New Chat' karne par saara data session se foran khatam ho jata hai."
        )
        
    # 8. How to Export WhatsApp Chat
    elif any(k in q for k in ["export", "kaise", "how to", "file", "upload", "android", "iphone", "ios", "txt"]):
        return (
            "### 📲 WhatsApp Chat Export Karne Ka Tareeqa:\n\n"
            "**Android Users:**\n"
            "1. WhatsApp chat kholein > Top right 3-dots **(⋮)** par click karein.\n"
            "2. **More** > **Export Chat** select karein.\n"
            "3. **'Without Media'** choose karein.\n"
            "4. File save karke is analyzer me drag & drop karein.\n\n"
            "**iPhone (iOS) Users:**\n"
            "1. Chat kholein aur top par contact/group name par tap karein.\n"
            "2. Scroll down karke **Export Chat** par click karein.\n"
            "3. **'Without Media'** choose karein aur `.txt` ya `.zip` file upload karein."
        )
        
    # 9. Greeting / General
    elif any(k in q for k in ["hi", "hello", "salam", "assalam", "hey", "help", "madad"]):
        return (
            "Assalam o Alaikum! 😊 Main aapki kya madad kar sakta hoon? Aap mujh se pooch sakte hain:\n\n"
            "- *'Positive, Neutral aur Negative sentiments kya hain?'*\n"
            "- *'Reply Speed kaise calculate hoti hai?'*\n"
            "- *'Peak Hours aur Busiest Day ka matlab?'*\n"
            "- *'WhatsApp chat export kaise karein?'*\n"
            "- *'Kya mera data safe hai?'*"
        )
        
    # Default Fallback
    else:
        return (
            f"Aapne poocha: **'{html.escape(query)}'**\n\n"
            "Main is WhatsApp Chat Analyzer ke tamam features explain kar sakta hoon:\n\n"
            "1. **📊 Overview Tab:** Total messages, words, active days, links aur media summary.\n"
            "2. **👥 Participants Tab:** User rankings aur 2-members ka Head-to-Head comparison.\n"
            "3. **🔤 Words & Sentiments:** Positive/Neutral/Negative classification, word chips aur top emojis.\n"
            "4. **📈 Activity & Timeline:** 24-hours peak time graph aur Average Reply Speed leaderboard.\n"
            "5. **📱 Chat Breakdown:** Live search, authentic chat bubbles aur `.txt` report export.\n\n"
            "💡 Mazeed wazahat ke liye upar diye gaye buttons mein se kisi par click karein ya specific topic ka naam likhein!"
        )

def add_bot_turn(query: str):
    st.session_state.bot_messages.append({"role": "user", "content": query})
    answer = get_assistant_explanation(query)
    st.session_state.bot_messages.append({"role": "assistant", "content": answer})

def reset_chat_data():
    st.session_state.parse_result = None
    st.session_state.chat_filename = None
    st.session_state.is_demo = False
    st.session_state.selected_user = "Overall"
    reset_bot_messages()
    st.rerun()

def load_sample(filepath: str, name: str):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    st.session_state.chat_filename = name
    st.session_state.is_demo = True
    st.session_state.parse_result = parse_chat_file(content, filename=name)
    st.session_state.selected_user = "Overall"
    st.rerun()

# Outline Chat Bubble SVG matching the screenshot exactly
chat_bubble_svg = '<svg viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="width:100%;height:100%;"><path d="M21 12c0 4.418-4.03 8-9 8-1.55 0-3-.35-4.28-.97L3 20l1.1-3.64C3.4 15.08 3 13.58 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/></svg>'

# Upload Tray with upward arrow SVG matching screenshot
upload_tray_svg = '<svg viewBox="0 0 24 24" fill="none" stroke="#075E54" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="width:100%;height:100%;"><path d="M12 3v11m0-11l-3.5 3.5M12 3l3.5 3.5M5 16v2.5a1.5 1.5 0 001.5 1.5h11a1.5 1.5 0 001.5-1.5V16"/></svg>'

# TOP HERO BANNER (Pixel match to media_1792003835526.png)
top_banner_html = f'''<div class="top-header-banner">
<div class="top-header-row">
<div class="top-header-icon">{chat_bubble_svg}</div>
<div class="top-header-text">
<div class="top-header-title">Analyze your WhatsApp Chat in Seconds</div>
<div class="top-header-subtitle">Upload your WhatsApp chat export and discover insights about your conversations</div>
</div>
</div>
</div>'''
st.markdown(top_banner_html, unsafe_allow_html=True)

res: ParseResult = st.session_state.parse_result

# ==============================================================================
# VIEW 1: LANDING & UPLOAD SCREEN (WHEN NO CHAT IS LOADED)
# Exact, 1-to-1 pixel match to reference image media_1792003835526.png
# ==============================================================================
if res is None:
    st.markdown('<div style="height: 3vh;"></div>', unsafe_allow_html=True)
    _, col_landing, _ = st.columns([1, 2.3, 1])
    with col_landing:
        # Unified container with border - styled as the dashed upload card
        with st.container(border=True):
            card_top_html = f'''<div class="upload-tray-icon">{upload_tray_svg}</div>
<div class="upload-card-title">Upload WhatsApp Chat</div>
<div class="upload-card-subtitle">Drag & drop your exported .txt file here</div>'''
            st.markdown(card_top_html, unsafe_allow_html=True)

            uploaded_file = st.file_uploader(
                "Upload WhatsApp Chat",
                type=["txt", "zip"],
                label_visibility="collapsed",
                key="landing_file_uploader"
            )

            inst_html = '''<div class="upload-card-instructions">Export from WhatsApp → More → Export Chat → <strong>Without Media</strong></div>'''
            st.markdown(inst_html, unsafe_allow_html=True)

        if uploaded_file is not None:
            with st.spinner("Analyzing conversation in local memory..."):
                file_bytes = uploaded_file.read()
                parsed = parse_chat_file(file_bytes, filename=uploaded_file.name)
                if parsed.status == "error":
                    st.error(f"❌ {parsed.error_message}")
                else:
                    st.session_state.parse_result = parsed
                    st.session_state.chat_filename = uploaded_file.name
                    st.session_state.is_demo = False
                    st.rerun()

        demo_label = '''<div class="demo-row-header">— Or explore instantly with demo data —</div>'''
        st.markdown(demo_label, unsafe_allow_html=True)
        c_d1, c_d2 = st.columns(2)
        with c_d1:
            if st.button("📱 Test Android Demo Chat", use_container_width=True, key="landing_demo_android"):
                load_sample("sample_chat_android.txt", "sample_android_chat.txt")
        with c_d2:
            if st.button("🍏 Test iPhone Demo Chat", use_container_width=True, key="landing_demo_ios"):
                load_sample("sample_chat_ios.txt", "sample_ios_chat.txt")

    st.markdown('<div style="height: 3vh;"></div>', unsafe_allow_html=True)
    # BOTTOM FOOTER BANNER (Exact match to media_1792003835526.png)
    footer_html = '''<div class="bottom-footer-banner"><strong>Instant Insights:</strong> Discover who\'s texting the most messages, see peak activity times, and uncover hidden patterns in your friends\' conversation</div>'''
    st.markdown(footer_html, unsafe_allow_html=True)

# ==============================================================================
# VIEW 2: DASHBOARD (WHEN CHAT IS LOADED)
# ==============================================================================
else:
    messages = res.messages
    participants = res.participants
    analysis = analyze_chat(
        messages,
        user=st.session_state.selected_user,
        remove_stopwords=True
    )
    stats = analysis["stats"]
    user_ranks = analysis["user_ranks"]
    most_active_user = user_ranks.iloc[0]["User"] if not user_ranks.empty else "N/A"
    weekday_dist = analysis["weekday_dist"]
    busiest_day_row = weekday_dist.sort_values(by="Messages", ascending=False).iloc[0] if not weekday_dist.empty else None
    busiest_day_name = busiest_day_row["Weekday"] if busiest_day_row is not None and busiest_day_row["Messages"] > 0 else "N/A"

    date_range_label = "Dates unavailable"
    if stats.start_date and stats.end_date:
        date_range_label = f"{stats.start_date.strftime('%d %b %Y')} – {stats.end_date.strftime('%d %b %Y')}"

    # Context Header bar with Participant selector and Clear data
    st.markdown("<div style='height: 0.8rem;'></div>", unsafe_allow_html=True)
    c_bar1, c_bar2, c_bar3 = st.columns([1.8, 1.2, 0.9])
    with c_bar1:
        st.markdown(f"""
        <div style="background:#FFFFFF; border:1px solid #E9EDEF; border-radius:8px; padding:0.48rem 0.85rem; font-size:0.88rem; box-shadow:0 1px 2px rgba(0,0,0,0.04); display:flex; align-items:center;">
            📁 &nbsp;<strong>File:</strong>&nbsp;<code>{st.session_state.chat_filename}</code> &nbsp;•&nbsp; 📅&nbsp;{date_range_label}
        </div>
        """, unsafe_allow_html=True)
    with c_bar2:
        p_opts = ["Overall"] + participants
        selected_p = st.selectbox(
            "Filter Contact:",
            options=p_opts,
            index=p_opts.index(st.session_state.selected_user) if st.session_state.selected_user in p_opts else 0,
            label_visibility="collapsed",
            key="dash_user_select"
        )
        if selected_p != st.session_state.selected_user:
            st.session_state.selected_user = selected_p
            st.rerun()
    with c_bar3:
        if st.button("🔄 Upload New Chat", use_container_width=True, key="dash_reset_btn"):
            reset_chat_data()

    st.markdown("<div style='height: 0.6rem;'></div>", unsafe_allow_html=True)

    # Native WhatsApp Tabs
    tab_overview, tab_participants, tab_words, tab_activity, tab_chat, tab_bot = st.tabs([
        "💬 OVERVIEW",
        "👥 PARTICIPANTS",
        "🔤 WORDS & SENTIMENTS",
        "📈 ACTIVITY & TIMELINE",
        "📱 CHAT BREAKDOWN",
        "🤖 CHATBOT ASSISTANT"
    ])

    # --- TAB 1: OVERVIEW ---
    with tab_overview:
        st.markdown(f"""
        <div class="summary-banner">
            <div style="font-size:0.85rem; font-weight:700; opacity:0.92; margin-bottom:12px; letter-spacing:0.04em;">
                📊 CONVERSATION SUMMARY ({st.session_state.selected_user})
            </div>
            <div class="summary-grid">
                <div class="summary-stat-box">
                    <div class="summary-stat-val">{stats.total_messages:,}</div>
                    <div class="summary-stat-lbl">Messages</div>
                </div>
                <div class="summary-stat-box">
                    <div class="summary-stat-val">{stats.total_words:,}</div>
                    <div class="summary-stat-lbl">Words</div>
                </div>
                <div class="summary-stat-box">
                    <div class="summary-stat-val">{stats.total_days}</div>
                    <div class="summary-stat-lbl">Active Days</div>
                </div>
                <div class="summary-stat-box">
                    <div class="summary-stat-val">{stats.media_count}</div>
                    <div class="summary-stat-lbl">Media Files</div>
                </div>
                <div class="summary-stat-box">
                    <div class="summary-stat-val">{stats.link_count}</div>
                    <div class="summary-stat-lbl">Shared Links</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        hourly_df = analysis["hourly_timeline"]
        peak_hour_val = hourly_df.sort_values(by="Messages", ascending=False).iloc[0]["Hour"] if not hourly_df.empty else "N/A"
        avg_w = round(stats.total_words / stats.total_messages, 1) if stats.total_messages > 0 else 0

        # Quick Insights 4-Card Responsive Grid
        st.markdown(f"""
        <div class="quick-insights-grid">
            <div class="quick-insight-card">
                <div class="quick-insight-icon">📅</div>
                <div>
                    <div class="quick-insight-label">Busiest Day</div>
                    <div class="quick-insight-val">{busiest_day_name}</div>
                </div>
            </div>
            <div class="quick-insight-card">
                <div class="quick-insight-icon">⏰</div>
                <div>
                    <div class="quick-insight-label">Peak Hour</div>
                    <div class="quick-insight-val">{peak_hour_val}</div>
                </div>
            </div>
            <div class="quick-insight-card">
                <div class="quick-insight-icon">💬</div>
                <div>
                    <div class="quick-insight-label">Avg Words / Msg</div>
                    <div class="quick-insight-val">{avg_w} words</div>
                </div>
            </div>
            <div class="quick-insight-card">
                <div class="quick-insight-icon">📈</div>
                <div>
                    <div class="quick-insight-label">Daily Avg Messages</div>
                    <div class="quick-insight-val">{stats.avg_messages_per_day:.1f} / day</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        col_comm, col_active = st.columns([1, 1.3])
        with col_comm:
            st.markdown(f"<div class='wa-card'><h4 style='color:{COLOR_TOP_BANNER}; margin-top:0;'>Top Communicator</h4>", unsafe_allow_html=True)
            if not user_ranks.empty:
                top_row = user_ranks.iloc[0]
                initials = "".join([part[0] for part in top_row["User"].split()[:2]]).upper()
                st.markdown(f"""
                <div style="display:flex; align-items:center; gap:1rem; margin-bottom:1rem;">
                    <div class="contact-avatar" style="width:56px; height:56px; font-size:1.35rem;">
                        {initials}
                    </div>
                    <div>
                        <div style="font-size:1.15rem; font-weight:700; color:{COLOR_TEXT_PRIMARY};">{top_row['User']}</div>
                        <div style="font-size:0.85rem; color:{COLOR_TEXT_SECONDARY};">{top_row['Messages']:,} messages sent</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                st.markdown(f"**Share of Total:** {top_row['Percentage']}%")
                st.progress(float(top_row['Percentage']) / 100.0)
                st.caption(f"Average Words per Message: **{top_row['Avg Words/Msg']}** words")
            st.markdown("</div>", unsafe_allow_html=True)

        with col_active:
            st.markdown(f"<div class='wa-card'><h4 style='color:{COLOR_TOP_BANNER}; margin-top:0;'>Most Active Time (Peak Hours)</h4>", unsafe_allow_html=True)
            fig_h = px.bar(
                hourly_df, x="Hour", y="Messages",
                color="Messages", color_continuous_scale=["#E8F5E9", COLOR_ACCENT_TEAL, COLOR_TOP_BANNER]
            )
            fig_h.update_layout(height=230, margin=dict(l=10, r=10, t=10, b=10), coloraxis_showscale=False, xaxis=dict(title=""))
            st.plotly_chart(fig_h, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # --- TAB 2: PARTICIPANTS ---
    with tab_participants:
        st.markdown(f"<h3 style='color:{COLOR_TOP_BANNER}; margin-bottom:0.3rem;'>👥 Participant Rankings & Comparison</h3>", unsafe_allow_html=True)
        col_list, col_comp = st.columns([1.2, 1])

        with col_list:
            st.markdown("#### Contact Activity List")
            for _, r in user_ranks.iterrows():
                initials = "".join([w[0] for w in r["User"].split()[:2]]).upper()
                st.markdown(f"""
                <div class="contact-item">
                    <div class="contact-left">
                        <div class="contact-avatar">{initials}</div>
                        <div>
                            <div class="contact-name">{r['User']}</div>
                            <div class="contact-sub">{r['Messages']:,} messages • {r['Avg Words/Msg']} words/msg</div>
                        </div>
                    </div>
                    <div>
                        <span class="contact-badge">{r['Percentage']}%</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        with col_comp:
            st.markdown("#### ⚡ 2-User Head-to-Head Comparison")
            if len(participants) >= 2:
                u1 = st.selectbox("Member 1:", options=participants, index=0)
                u2 = st.selectbox("Member 2:", options=participants, index=1 if len(participants) > 1 else 0)
                comp = ComparisonAnalyzer.compare_two_users(messages, u1, u2)
                m1 = comp['user1_stats'].get('total_messages', 0)
                m2 = comp['user2_stats'].get('total_messages', 0)
                tot_m = m1 + m2
                pct1 = round((m1 / tot_m * 100), 1) if tot_m > 0 else 50
                pct2 = round((m2 / tot_m * 100), 1) if tot_m > 0 else 50

                st.markdown(f"""
                <div class="wa-card" style="background:#F8FAF9;">
                    <div style="display:flex; justify-content:space-between; text-align:center; margin-bottom:0.75rem; font-weight:700; color:{COLOR_TOP_BANNER};">
                        <div style="flex:1;">👤 {u1} ({pct1}%)</div>
                        <div style="color:#667781; font-size:0.8rem; margin:0 8px;">VS</div>
                        <div style="flex:1;">👤 {u2} ({pct2}%)</div>
                    </div>
                    <div style="display:flex; height:10px; border-radius:5px; overflow:hidden; margin-bottom:1rem; background:#E2E8E4;">
                        <div style="width:{pct1}%; background:{COLOR_BUTTON_GREEN};"></div>
                        <div style="width:{pct2}%; background:{COLOR_ACCENT_TEAL};"></div>
                    </div>
                    <table style="width:100%; font-size:0.88rem; border-collapse:collapse;">
                        <tr style="border-bottom:1px solid #E2E8E4; height:34px;">
                            <td style="font-weight:600; text-align:center;">{m1:,}</td>
                            <td style="color:#667781; text-align:center; font-size:0.8rem;">Messages</td>
                            <td style="font-weight:600; text-align:center;">{m2:,}</td>
                        </tr>
                        <tr style="border-bottom:1px solid #E2E8E4; height:34px;">
                            <td style="font-weight:600; text-align:center;">{comp['user1_stats'].get('avg_words_per_msg', 0)}</td>
                            <td style="color:#667781; text-align:center; font-size:0.8rem;">Avg Words</td>
                            <td style="font-weight:600; text-align:center;">{comp['user2_stats'].get('avg_words_per_msg', 0)}</td>
                        </tr>
                        <tr style="height:34px;">
                            <td style="font-weight:600; text-align:center;">{comp['user1_stats'].get('avg_reply_mins', 'N/A')} m</td>
                            <td style="color:#667781; text-align:center; font-size:0.8rem;">Reply Speed</td>
                            <td style="font-weight:600; text-align:center;">{comp['user2_stats'].get('avg_reply_mins', 'N/A')} m</td>
                        </tr>
                    </table>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("At least 2 participants needed for comparison.")

    # --- TAB 3: WORDS & SENTIMENTS ---
    with tab_words:
        st.markdown(f"<h3 style='color:{COLOR_TOP_BANNER}; margin-bottom:0.3rem;'>🔤 Words, Emojis & Sentiment Analysis</h3>", unsafe_allow_html=True)
        
        sentiments = analysis["sentiments"]
        st.markdown(f'''<div class="wa-card">
<h4 style="color:{COLOR_TOP_BANNER}; margin-top:0;">Sentiment Analysis Gauge (Status Rings)</h4>
<div class="status-ring-container">
    <div class="status-circle pos">
        <span style="font-size:1.3rem;">{sentiments['pos_pct']}%</span>
        <span style="font-size:0.7rem; text-transform:uppercase;">Positive</span>
    </div>
    <div class="status-circle neu">
        <span style="font-size:1.3rem;">{sentiments['neu_pct']}%</span>
        <span style="font-size:0.7rem; text-transform:uppercase;">Neutral</span>
    </div>
    <div class="status-circle neg">
        <span style="font-size:1.3rem;">{sentiments['neg_pct']}%</span>
        <span style="font-size:0.7rem; text-transform:uppercase;">Negative</span>
    </div>
</div>
<div class="sentiment-legend-box">
    <div style="font-size:0.92rem; font-weight:700; color:{COLOR_TOP_BANNER}; margin-bottom:4px;">
        ℹ️ Positive, Neutral & Negative Sentiments Kya Define Karte Hain?
    </div>
    <div style="font-size:0.84rem; color:{COLOR_TEXT_SECONDARY}; margin-bottom:10px;">
        Yeh classifier English aur Roman Urdu alfaz aur emojis ke polarity score ko analyze karta hai:
    </div>
    <div class="sentiment-legend-grid">
        <div class="sentiment-item-card">
            <span class="sentiment-badge-pos">🟢 Positive ({sentiments['pos_pct']}%)</span>
            <div style="color:{COLOR_TEXT_SECONDARY}; margin-top:4px;">
                <strong>Tareef, Khushi & Ittefaq:</strong> Messages jismein appreciation, shukriya, ya positive jazbaat hon.
                <br/><em style="color:#2E7D32;">Alfaz: zabardast, behtareen, shukriya, awesome, good, mubarak, ❤️, 👍, 🎉, 🔥</em>
            </div>
        </div>
        <div class="sentiment-item-card">
            <span class="sentiment-badge-neu">⚪ Neutral ({sentiments['neu_pct']}%)</span>
            <div style="color:{COLOR_TEXT_SECONDARY}; margin-top:4px;">
                <strong>Mamool / Factual Data:</strong> Routine coordination, links, questions, aur baghair kisi jazbati polarity ke messages.
                <br/><em style="color:#54656F;">Misal: "Meeting 3 PM pe rakhein?", "Document upload kar diya hai"</em>
            </div>
        </div>
        <div class="sentiment-item-card">
            <span class="sentiment-badge-neg">🔴 Negative ({sentiments['neg_pct']}%)</span>
            <div style="color:{COLOR_TEXT_SECONDARY}; margin-top:4px;">
                <strong>Shikayat, Masla & Afsos:</strong> Messages jismein pareshani, der (delay), issue, ghalat, ya disagreement ho.
                <br/><em style="color:#C62828;">Alfaz: sorry, late, problem, issue, kharab, masla, ghalat, bekaar, 😢, 😡, 💔</em>
            </div>
        </div>
    </div>
</div>
</div>''', unsafe_allow_html=True)

        col_w, col_e = st.columns([1.2, 1])
        with col_w:
            st.markdown(f"<div class='wa-card'><h4 style='color:{COLOR_TOP_BANNER}; margin-top:0;'>Top Words (Green Chips)</h4>", unsafe_allow_html=True)
            words_data = analysis["words"]
            if words_data:
                chips_html = "".join([f"<span class='word-chip'>{w} ({c})</span>" for w, c in words_data[:24]])
                st.markdown(f"<div>{chips_html}</div>", unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                wc = WordCloud(width=500, height=270, background_color="white", colormap="Greens", max_words=60).generate_from_frequencies(dict(words_data))
                fig_wc, ax_wc = plt.subplots(figsize=(6, 3.3))
                ax_wc.imshow(wc, interpolation="bilinear")
                ax_wc.axis("off")
                plt.tight_layout(pad=0)
                st.pyplot(fig_wc, use_container_width=True)
                plt.close(fig_wc)
            st.markdown("</div>", unsafe_allow_html=True)

        with col_e:
            st.markdown(f"<div class='wa-card'><h4 style='color:{COLOR_TOP_BANNER}; margin-top:0;'>Top Emojis (Reaction Style)</h4>", unsafe_allow_html=True)
            emojis_df = analysis["emojis"]
            if not emojis_df.empty:
                e_cols = st.columns(3)
                for idx, (_, erow) in enumerate(emojis_df.head(9).iterrows()):
                    with e_cols[idx % 3]:
                        st.markdown(f"""
                        <div class="emoji-pill-box">
                            <div style="font-size:1.8rem; line-height:1;">{erow['Emoji']}</div>
                            <div style="font-weight:700; color:{COLOR_TOP_BANNER}; font-size:0.85rem; margin-top:0.25rem;">{erow['Count']}</div>
                            <div style="font-size:0.7rem; color:#667781;">{erow['Percentage']}%</div>
                        </div>
                        """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # --- TAB 4: ACTIVITY & TIMELINE ---
    with tab_activity:
        st.markdown(f"<h3 style='color:{COLOR_TOP_BANNER}; margin-bottom:0.3rem;'>📈 Activity Trends & Response Speeds</h3>", unsafe_allow_html=True)
        c_a1, c_a2 = st.columns([1.2, 1.2])
        with c_a1:
            st.markdown(f"<div class='wa-card'><h4 style='color:{COLOR_TOP_BANNER}; margin-top:0;'>Hourly Activity (24 Hours)</h4>", unsafe_allow_html=True)
            fig_h2 = px.bar(
                analysis["hourly_timeline"], x="Hour", y="Messages",
                color="Messages", color_continuous_scale=["#C8E6C9", COLOR_TOP_BANNER]
            )
            fig_h2.update_layout(height=230, margin=dict(l=10, r=10, t=10, b=10), coloraxis_showscale=False, xaxis=dict(title=""))
            st.plotly_chart(fig_h2, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
        with c_a2:
            st.markdown(f"<div class='wa-card'><h4 style='color:{COLOR_TOP_BANNER}; margin-top:0;'>Weekly Pattern (Day of Week)</h4>", unsafe_allow_html=True)
            fig_w = px.bar(
                analysis["weekday_dist"], x="Weekday", y="Messages",
                color="Messages", color_continuous_scale=["#C8E6C9", COLOR_ACCENT_TEAL]
            )
            fig_w.update_layout(height=230, margin=dict(l=10, r=10, t=10, b=10), coloraxis_showscale=False, xaxis=dict(title=""))
            st.plotly_chart(fig_w, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(f"<div class='wa-card'><h4 style='color:{COLOR_TOP_BANNER}; margin-top:0;'>⏱️ Average Response Speeds (Leaderboard)</h4>", unsafe_allow_html=True)
        reply_df = analysis["reply_times"]
        if not reply_df.empty:
            medals = ["🥇", "🥈", "🥉"] + ["👤"] * 20
            r_cols = st.columns(min(len(reply_df), 4))
            for idx, (_, rrow) in enumerate(reply_df.head(4).iterrows()):
                with r_cols[idx]:
                    mins = rrow.get("Average Reply Time (mins)", rrow.get("Avg Reply Minutes", 0.0))
                    speed_tag = "⚡ Fast" if mins < 5 else ("🕒 Steady" if mins < 20 else "⏳ Relaxed")
                    st.markdown(f'''<div style="background:#F8FAF9; border:1px solid #E9EDEF; border-radius:10px; padding:0.85rem; text-align:center;">
<div style="font-size:1.6rem; margin-bottom:0.2rem;">{medals[idx]}</div>
<div style="font-weight:700; color:{COLOR_TEXT_PRIMARY}; font-size:0.95rem;">{html.escape(str(rrow['User']))}</div>
<div style="font-size:1.25rem; font-weight:700; color:{COLOR_TOP_BANNER}; margin:0.25rem 0;">{mins} <span style="font-size:0.75rem; font-weight:500;">mins</span></div>
<span style="background:#E7F8F0; color:#0B6644; font-size:0.75rem; font-weight:600; padding:0.15rem 0.5rem; border-radius:12px;">{speed_tag}</span>
</div>''', unsafe_allow_html=True)
        else:
            st.info("Not enough message interchanges to calculate reply speed.")
        st.markdown("</div>", unsafe_allow_html=True)

    # --- TAB 5: CHAT BREAKDOWN ---
    with tab_chat:
        st.markdown(f'''<div class="chat-breakdown-heading-row">
<h3 class="chat-breakdown-title">📱 Individual Chat Breakdown</h3>
<p class="chat-breakdown-sub">Browse full message history, search conversations, and inspect message exchanges with delivery status.</p>
</div>''', unsafe_allow_html=True)

        chat_msgs = [m for m in messages if not m.is_system]
        if st.session_state.selected_user != "Overall":
            chat_msgs = [m for m in chat_msgs if m.sender == st.session_state.selected_user]
        total_in_scope = len(chat_msgs)

        c_search, c_info = st.columns([2.8, 1.2], vertical_alignment="center")
        with c_search:
            search_query = st.text_input(
                "Search conversation messages",
                key="chat_search_kw",
                placeholder="🔍 Search messages, links, or keywords...",
                label_visibility="collapsed"
            )

        filtered_msgs = chat_msgs
        if search_query.strip():
            kw = search_query.strip().lower()
            filtered_msgs = [m for m in chat_msgs if kw in (m.text or "").lower() or kw in (m.sender or "").lower()]

        with c_info:
            if search_query.strip():
                st.markdown(
                    f'<div class="chat-count-pill highlight">Found <strong>{len(filtered_msgs)}</strong> of {total_in_scope}</div>',
                    unsafe_allow_html=True
                )
            else:
                display_count = min(len(filtered_msgs), 150)
                st.markdown(
                    f'<div class="chat-count-pill">Showing <strong>{display_count}</strong> of {total_in_scope} msgs</div>',
                    unsafe_allow_html=True
                )

        if search_query.strip() and not filtered_msgs:
            safe_kw = html.escape(search_query.strip())
            empty_html = f'''<div class="wa-chat-window">
<div class="chat-empty-state">
<div class="chat-empty-icon">🔍</div>
<div class="chat-empty-title">No messages found</div>
<div class="chat-empty-desc">No messages matching "<strong>{safe_kw}</strong>". Try checking for typos or searching a different keyword.</div>
</div>
</div>'''
            st.markdown(empty_html, unsafe_allow_html=True)
        else:
            # Determine outgoing vs incoming perspective
            if st.session_state.selected_user != "Overall":
                primary_sender = st.session_state.selected_user
            elif "You" in participants:
                primary_sender = "You"
            else:
                primary_sender = participants[0] if participants else "You"

            # Stable color palette for incoming participant headers
            PARTICIPANT_COLORS = [
                "#128C7E", "#1F7A8C", "#BF4080", "#E56F2B",
                "#4B6584", "#6C5CE7", "#D63031", "#0984E3"
            ]
            sender_color_map = {}
            for idx, p in enumerate(participants):
                sender_color_map[p] = PARTICIPANT_COLORS[idx % len(PARTICIPANT_COLORS)]

            chat_parts = ['<div class="wa-chat-window"><div class="wa-chat-stream">']
            last_date_str = None
            prev_sender = None

            for m in filtered_msgs[:150]:
                msg_date = m.datetime.strftime("%d %B %Y") if m.datetime else ""
                if msg_date and msg_date != last_date_str:
                    chat_parts.append(
                        f'<div class="chat-date-divider"><span class="chat-date-chip">{html.escape(msg_date)}</span></div>'
                    )
                    last_date_str = msg_date
                    prev_sender = None  # Reset consecutive grouping on date boundary

                is_out = (m.sender == primary_sender)
                is_consecutive = (m.sender == prev_sender)
                prev_sender = m.sender

                row_cls = f"msg-row {'out' if is_out else 'in'} {'consecutive' if is_consecutive else 'new-sender'}"
                bubble_cls = f"msg-bubble {'out' if is_out else 'in'}"
                t_str = m.datetime.strftime("%I:%M %p").lstrip("0") if m.datetime else ""

                # Safely escape message body so raw HTML, tags, or script tags are never evaluated
                safe_text = html.escape(m.text or "")
                safe_text = safe_text.replace("\n", "<br/>")

                # Sender header: ONLY for incoming messages AND ONLY if first in consecutive block
                sender_header = ""
                if not is_out and not is_consecutive:
                    scolor = sender_color_map.get(m.sender, "#128C7E")
                    sender_header = f'<div class="msg-sender" style="color:{scolor};">{html.escape(m.sender)}</div>'

                # Media badge
                media_html = ""
                if m.is_media:
                    m_type = html.escape(m.media_type or "Media file")
                    icon = "📷" if m.media_type == "Image" else ("🎥" if m.media_type == "Video" else ("🎵" if m.media_type == "Audio" else "📎"))
                    media_html = f'<div class="msg-media-box"><span class="msg-media-icon">{icon}</span><span>{m_type}</span></div>'

                # Delivery ticks: blue double checkmark on outgoing bubbles
                ticks_html = '<span class="blue-ticks" title="Read">✓✓</span>' if is_out else ''

                chat_parts.append(
                    f'<div class="{row_cls}">'
                    f'<div class="{bubble_cls}">'
                    f'{sender_header}'
                    f'{media_html}'
                    f'<div class="msg-text-content">{safe_text}</div>'
                    f'<div class="msg-footer"><span>{t_str}</span>{ticks_html}</div>'
                    f'</div>'
                    f'</div>'
                )

            chat_parts.append('</div></div>')
            chat_html = "".join(chat_parts)
            st.markdown(chat_html, unsafe_allow_html=True)

        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
        summary_text = f"""WhatsApp Chat Analysis Report
Generated: {datetime.now().strftime('%d %B %Y %H:%M')}
Chat File: {st.session_state.chat_filename}
Date Range: {date_range_label}
Filter: {st.session_state.selected_user}

SUMMARY STATISTICS:
Total Messages: {stats.total_messages:,}
Total Words: {stats.total_words:,}
Active Days: {stats.total_days}
Media Files: {stats.media_count}
Links Shared: {stats.link_count}
Busiest Day: {busiest_day_name}
Top Communicator: {most_active_user}
"""
        st.download_button(
            "📥 Download Analysis Report (.txt)",
            data=summary_text,
            file_name=f"whatsapp_analysis_{st.session_state.selected_user}_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain",
            key="dl_analysis_report"
        )

    # --- TAB 6: CHATBOT ASSISTANT ---
    with tab_bot:
        st.markdown(f'''<div class="chat-breakdown-heading-row">
<h3 class="chat-breakdown-title">🤖 WhatsApp Analyzer AI Assistant</h3>
<p class="chat-breakdown-sub">Is application ke kisi bhi feature, metric, ya calculation ki wazahat (explanation) ke liye sawal poochhein.</p>
</div>''', unsafe_allow_html=True)

        st.markdown('''
        <div style="margin: 8px 0 10px 0; font-size: 0.88rem; font-weight: 600; color: #54656F;">
            💡 Quick Help Topics (Click to ask instantly):
        </div>
        ''', unsafe_allow_html=True)

        b_c1, b_c2, b_c3 = st.columns(3)
        with b_c1:
            if st.button("💡 Sentiments (Pos/Neu/Neg)?", use_container_width=True, key="bot_btn_sent"):
                add_bot_turn("Sentiments (Positive, Neutral, Negative) kya define karte hain?")
                st.rerun()
        with b_c2:
            if st.button("⏱️ Reply Speed Kaise Calculate Hoti Hai?", use_container_width=True, key="bot_btn_speed"):
                add_bot_turn("Reply speed kaise calculate hoti hai?")
                st.rerun()
        with b_c3:
            if st.button("👥 Participant Comparison Kaise Kaam Karta Hai?", use_container_width=True, key="bot_btn_comp"):
                add_bot_turn("Participant comparison kaise kaam karta hai?")
                st.rerun()

        b_c4, b_c5, b_c6 = st.columns(3)
        with b_c4:
            if st.button("📈 Peak Hours & Busiest Day?", use_container_width=True, key="bot_btn_peak"):
                add_bot_turn("Peak hours aur busiest day ka kya matlab hai?")
                st.rerun()
        with b_c5:
            if st.button("🔒 Kya Mera Chat Data Safe Hai?", use_container_width=True, key="bot_btn_safe"):
                add_bot_turn("Kya mera chat data safe aur private hai?")
                st.rerun()
        with b_c6:
            if st.button("📲 WhatsApp Chat Kaise Export Karein?", use_container_width=True, key="bot_btn_exp"):
                add_bot_turn("WhatsApp chat export kaise karein?")
                st.rerun()

        # Chat message stream
        bot_html_parts = ['<div class="wa-chat-window" style="max-height:460px; margin: 16px 0;"><div class="wa-chat-stream">']
        for msg in st.session_state.bot_messages:
            is_user = (msg["role"] == "user")
            row_cls = f"msg-row {'out' if is_user else 'in'} new-sender"
            bubble_cls = f"msg-bubble {'out' if is_user else 'in'}"
            sender_tag = "" if is_user else '<div class="msg-sender" style="color:#128C7E; margin-bottom:4px;">🤖 Analyzer Assistant</div>'
            formatted_text = render_bot_markdown(msg["content"])
            
            bot_html_parts.append(
                f'<div class="{row_cls}">'
                f'<div class="{bubble_cls}" style="max-width:85%; font-size:14px;">'
                f'{sender_tag}'
                f'<div class="msg-text-content">{formatted_text}</div>'
                f'</div>'
                f'</div>'
            )
        bot_html_parts.append('</div></div>')
        st.markdown("".join(bot_html_parts), unsafe_allow_html=True)

        # Question input form with submit and clear
        with st.form("bot_question_form", clear_on_submit=True):
            f_in, f_btn = st.columns([5, 1], vertical_alignment="center")
            with f_in:
                bot_user_text = st.text_input(
                    "Ask question to assistant",
                    placeholder="💬 Type any question (e.g. Stopwords ka kya matlab hai?)...",
                    label_visibility="collapsed"
                )
            with f_btn:
                send_clicked = st.form_submit_button("Send 🚀", use_container_width=True)

            if send_clicked and bot_user_text.strip():
                add_bot_turn(bot_user_text.strip())
                st.rerun()

        c_rst, _ = st.columns([2, 4])
        with c_rst:
            if st.button("🗑️ Clear Assistant Chat", use_container_width=True, key="bot_clear_chat"):
                reset_bot_messages()
                st.rerun()

    # Bottom Footer Banner on Dashboard
    st.markdown("""
    <div class="bottom-footer-banner">
        <strong>Instant Insights:</strong> Discover who's texting the most messages, see peak activity times, and uncover hidden patterns in your friends' conversation
    </div>
    """, unsafe_allow_html=True)

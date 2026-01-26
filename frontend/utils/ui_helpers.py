"""
Reusable UI components
"""
import streamlit as st


def display_metric_card(label: str, value, help_text: str = None):
    """Display a metric card"""
    st.metric(
        label=label,
        value=value,
        help=help_text
    )


def display_section_header(title: str):
    """Display a section header"""
    st.markdown(f"## {title}")

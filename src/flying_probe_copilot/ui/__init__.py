"""Phase 2 slice 3 — Streamlit + Plotly dashboard.

Five-page interactive UI over the analytics layer (yield_over_time,
failure_pareto, individuals_chart, z_score_anomalies) backed by a
read-only DuckDB connection with ``st.cache_resource`` / ``st.cache_data``
caching.

Sub-modules
-----------
data    — connection, caching wrappers, pure transform helpers
charts  — pure Plotly figure builders
views   — 5 page render functions (render_overview / yield / pareto / spc / anomalies)
app     — Streamlit entry-point (``main()``); run with ``streamlit run src/.../ui/app.py``
"""

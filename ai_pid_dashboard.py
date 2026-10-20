from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title='AI-PID Motor Dashboard', page_icon='⚙️', layout='wide')
st.title('⚙️ AI-Assisted PID Motor Speed Control')
st.caption('Offline demonstration | 42 recorded experiments | Predictions are not live motor measurements')

@st.cache_data
def read_csv(filename):
    path = ROOT / filename
    return pd.read_csv(path) if path.exists() else None

rankings = read_csv('ai_pid_42_gain_rankings.csv')
metrics = read_csv('ai_42_run_metrics.csv')
validation = read_csv('ai_42_validation.csv')
accuracy = read_csv('ai_42_accuracy_summary.csv')

if rankings is None:
    st.error('Missing ai_pid_42_gain_rankings.csv. Put this script in the same folder as your AI output CSV files.')
    st.stop()

st.subheader('AI-selected PID gains')
conditions = sorted(rankings['Condition'].dropna().astype(str).unique().tolist())
condition = st.selectbox('Experimental power condition', conditions, index=conditions.index('usb_repeat') if 'usb_repeat' in conditions else 0)
speeds = sorted(rankings.loc[rankings['Condition'].astype(str) == condition, 'Target_RPM'].dropna().unique().tolist())
target = st.selectbox('Target motor speed (RPM)', speeds, format_func=lambda x: f'{x:g} RPM')
selection = rankings[(rankings['Condition'].astype(str) == condition) & (rankings['Target_RPM'] == target)]
if not selection.empty:
    choice = selection.iloc[0]
    cols = st.columns(4)
    for col, key, label in zip(cols, ['Kp','Ki','Kd','AI_Predicted_Score'], ['Kp','Ki','Kd','Predicted score (lower is better)']):
        value = choice.get(key, float('nan'))
        col.metric(label, f'{float(value):.3f}' if pd.notna(value) else 'N/A')
    st.info('These are offline recommendations based on tested gain combinations. They are not proof of better live motor control.')

st.divider()
st.subheader('Model validation')
if validation is not None and {'Score', 'Predicted_Score_CV', 'Baseline_Score_CV'}.issubset(validation.columns):
    valid = validation.dropna(subset=['Score', 'Predicted_Score_CV', 'Baseline_Score_CV']).copy()
    if not valid.empty:
        ai_mae = (valid['Score'] - valid['Predicted_Score_CV']).abs().mean()
        baseline_mae = (valid['Score'] - valid['Baseline_Score_CV']).abs().mean()
        improvement = (baseline_mae - ai_mae) / baseline_mae * 100 if baseline_mae else float('nan')
        a, b, c = st.columns(3)
        a.metric('AI prediction MAE', f'{ai_mae:.3f}')
        b.metric('Baseline prediction MAE', f'{baseline_mae:.3f}')
        c.metric('MAE improvement', f'{improvement:.2f}%')
        fig = px.scatter(valid, x='Score', y='Predicted_Score_CV', color='Condition' if 'Condition' in valid else None,
                         hover_data=[col for col in ['File','Target_RPM','Kp','Ki'] if col in valid],
                         labels={'Score':'Measured performance score','Predicted_Score_CV':'Cross-validated AI predicted score'},
                         title='Actual vs predicted PID performance score')
        lo = min(valid['Score'].min(), valid['Predicted_Score_CV'].min())
        hi = max(valid['Score'].max(), valid['Predicted_Score_CV'].max())
        fig.add_shape(type='line', x0=lo, y0=lo, x1=hi, y1=hi, line={'dash':'dash', 'color':'gray'})
        st.plotly_chart(fig, use_container_width=True)
        comparison = pd.DataFrame({'Model':['Random Forest AI', 'Target-mean baseline'], 'MAE':[ai_mae, baseline_mae]})
        st.plotly_chart(px.bar(comparison, x='Model', y='MAE', title='Prediction error comparison (lower is better)'), use_container_width=True)
else:
    st.warning('Validation CSV not found or expected columns are missing.')

st.divider()
st.subheader('Experimental run results')
if metrics is not None:
    st.dataframe(metrics, use_container_width=True, hide_index=True)
    if {'Target_RPM','Score'}.issubset(metrics.columns):
        fig = px.box(metrics, x='Target_RPM', y='Score', color='Condition' if 'Condition' in metrics else None,
                     points='all', title='Measured PID performance scores by target RPM')
        st.plotly_chart(fig, use_container_width=True)
else:
    st.warning('ai_42_run_metrics.csv not found; experiment table unavailable.')

if accuracy is not None:
    with st.expander('Full cross-validation accuracy summary'):
        st.dataframe(accuracy, use_container_width=True, hide_index=True)

st.caption('Study limitation: run-level cross-validation can share gain combinations across folds. USB and external-power experiments are not directly interchangeable.')
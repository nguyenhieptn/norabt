import plotly.graph_objects as go
from plotly.subplots import make_subplots

fig = make_subplots(rows=1, cols=1)
fig.add_trace(go.Scatter(x=[1], y=[10], mode="markers", marker=dict(symbol="triangle-up", size=10)), row=1, col=1)

fig.add_annotation(
    x=1, y=10, text="Buy", showarrow=False, yshift=-15,
    font=dict(color="white", size=9), bgcolor="#008000", borderpad=2, row=1, col=1
)

fig.write_html("test.html")

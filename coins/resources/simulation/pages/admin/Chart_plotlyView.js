import React, { Component } from 'react';
import Plot from 'react-plotly.js';

class Chart_plotlyView extends Component {
    render() {
        return (
            <div>
                <div >
                    <Plot
                        data={[
                            {
                                x: [1, 2, 3],
                                y: [2, 6, 3],
                                type: 'scatter',
                                mode: 'lines+markers',
                                marker: { color: 'red' },
                            },
                            { type: 'bar', x: [1, 2, 3], y: [2, 5, 3] },
                        ]}
                        layout={{ title: 'A Fancy Plot' }}
                        style={{ width: '100%' }}
                    />
                </div>

                <div >
                    <Plot
                        data={[
                            {
                                x: [1, 2, 3],
                                y: [2, 6, 3],
                                type: 'scatter',
                                mode: 'lines+markers',
                                marker: { color: 'red' },
                            },
                            { type: 'bar', x: [1, 2, 3], y: [2, 5, 3] },
                        ]}
                        layout={{ title: 'A Fancy Plot' }}
                        style={{ width: '100%' }}
                    />
                </div>
            </div>
        );
    }
}

export default Chart_plotlyView;
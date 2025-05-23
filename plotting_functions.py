from matplotlib.figure import Figure

def get_plot(data, var1, plot_type, var2=None):
    fig = Figure(figsize=(8, 6))
    ax = fig.subplots()

    if plot_type in ['histogram', 'boxplot', 'barchart', 'density']:
        x = data[var1].dropna()

        if plot_type == 'histogram':
            ax.hist(x, bins=30, color='blue', alpha=0.7)
            ax.set_title(f'Histogram of {var1}')
            ax.set_xlabel(var1)
            ax.set_ylabel('Frequency')

        elif plot_type == 'boxplot':
            ax.boxplot(x, vert=True)
            ax.set_title(f'Boxplot of {var1}')
            ax.set_ylabel(var1)

        elif plot_type == 'barchart':
            counts = x.value_counts()
            ax.bar(counts.index.astype(str), counts.values, color='green', alpha=0.7)
            ax.set_title(f'Bar Chart of {var1}')
            ax.set_xlabel(var1)
            ax.set_ylabel('Count')
            for label in ax.get_xticklabels():
                label.set_rotation(45)
                label.set_ha('right')

        elif plot_type == 'density':
            ax.hist(x, bins=50, density=True, alpha=0.6, color='purple')
            ax.set_title(f'Density Plot of {var1}')
            ax.set_xlabel(var1)
            ax.set_ylabel('Density')

    elif plot_type in ['scatter', 'line', 'heatmap']:
        if var2 is None:
            raise ValueError(f"plot_type '{plot_type}' requires a second variable 'var2'")

        x = data[var1]
        y = data[var2]

        if plot_type == 'scatter':
            ax.scatter(x, y, alpha=0.7)
            ax.set_title(f'Scatter Plot of {var1} vs {var2}')
            ax.set_xlabel(var1)
            ax.set_ylabel(var2)

        elif plot_type == 'line':
            sorted_idx = x.argsort()
            ax.plot(x.iloc[sorted_idx], y.iloc[sorted_idx])
            ax.set_title(f'Line Plot of {var1} vs {var2}')
            ax.set_xlabel(var1)
            ax.set_ylabel(var2)

        elif plot_type == 'heatmap':
            h = ax.hist2d(x, y, bins=30, cmap='Blues')
            fig.colorbar(h[3], ax=ax, label='Count')
            ax.set_title(f'Heatmap (2D Histogram) of {var1} vs {var2}')
            ax.set_xlabel(var1)
            ax.set_ylabel(var2)

    else:
        raise ValueError(f"Unsupported plot type: {plot_type}")

    fig.tight_layout()
    return fig
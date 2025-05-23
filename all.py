import pandas as pd
import numpy as np
import plotly.express as px
import tkinter as tk
from tkinter import ttk, Toplevel
from sqlalchemy import create_engine
import webbrowser
import matplotlib
from tkhtmlview import HTMLLabel
matplotlib.use('Qt5Agg')

def show_html_in_window(filepath, title="HTML Plot"):
    with open(filepath, "r", encoding="utf-8") as file:
        html_content = file.read()

    window = Toplevel()
    window.title(title)
    window.geometry("800x600")

    html_label = HTMLLabel(window, html=html_content)
    html_label.pack(fill="both", expand=True)

# DB connection
engine = create_engine('postgresql://postgres:nghiem115940@localhost:5432/postgres')

# Load and process full data
query = """
SELECT
    fr.rating,
    fr.rating_count,
    fr.actual_price,
    fr.discount_price,
    dp.product_id,
    dp.name,
    dc.category
FROM fact_reviews fr
JOIN dim_products dp ON fr.product_id = dp.product_id
JOIN dim_categories dc ON dp.category_id = dc.category_id
WHERE fr.rating IS NOT NULL
    AND fr.rating_count IS NOT NULL
    AND fr.actual_price IS NOT NULL
    AND fr.discount_price IS NOT NULL
"""
df = pd.read_sql(query, engine).dropna()

# Clean and calculate extra columns
df["rating"] = pd.to_numeric(df["rating"])
df["rating_count"] = pd.to_numeric(df["rating_count"])
df["actual_price"] = pd.to_numeric(df["actual_price"])
df["discount_price"] = pd.to_numeric(df["discount_price"])
df["discount_percent"] = ((df["actual_price"] - df["discount_price"]) / df["actual_price"]) * 100
df["price"] = df["actual_price"] - df["discount_price"]
df["top_category"] = df["category"].str.split("|").str[0]

# Summary statistics
averages = {
    "Average Rating": df["rating"].mean(),
    "Average Actual Price": df["actual_price"].mean(),
    "Average Discount Price": df["discount_price"].mean(),
    "Average True Price": df["price"].mean(),
    "Average Discount %": df["discount_percent"].mean()
}

# --------- Functions --------- #

def show_summary():
    win = Toplevel()
    win.title("Overall Summary")
    win.geometry("400x300")
    ttk.Label(win, text="Overall Summary", font=("Arial", 16)).pack(pady=10)
    for k, v in averages.items():
        ttk.Label(win, text=f"{k}: {v:.2f}", font=("Arial", 12)).pack(pady=2)

def calculate_grouped_data(metric):
    if metric == "rating":
        grouped = df.groupby("top_category").agg(
            value=("rating", lambda x: np.average(x, weights=df.loc[x.index, "rating_count"]))
        ).reset_index()
    else:
        grouped = df.groupby("top_category")[metric].mean().reset_index(name="value")
    grouped = grouped.sort_values(by="value", ascending=False)
    return grouped

def show_category_plot(metric, title, y_label):
    data = calculate_grouped_data(metric)
    fig = px.bar(data, x="top_category", y="value", title=title,
                 labels={"top_category": "Category", "value": y_label}, text_auto=True)
    fig.update_layout(xaxis_tickangle=-45)
    filename = f"{metric}_category_plot.html"
    fig.write_html(filename)
    webbrowser.open_new_tab(filename)

def show_price_bin_plot(column, title):
    bins = pd.cut(df[column], bins=20)
    all_bins = pd.Series(bins.cat.categories, name="bin")
    grouped = df.groupby(bins, observed=False).agg({
        "rating": "mean",
        "rating_count": "mean"
    }).reindex(all_bins).reset_index()
    grouped["bin_str"] = grouped["bin"].astype(str)
    grouped["rating"] = grouped["rating"].interpolate()
    grouped["rating_count"] = grouped["rating_count"].interpolate()
    fig = px.line(grouped, x="bin_str", y="rating", title=f"Average Rating vs {title}",
                  labels={"rating": "Average Rating", "bin_str": title},
                  markers=True, hover_data={"rating_count": True})
    fig.update_traces(mode="lines+markers", connectgaps=True)
    fig.update_layout(xaxis_tickangle=-45)
    filename = f"{column}_bin_plot.html"
    fig.write_html(filename)
    webbrowser.open_new_tab(filename)

# --------- Main GUI --------- #

root = tk.Tk()
root.title("Product Review Visualizer")
root.geometry("500x600")

ttk.Label(root, text="Select Visualization", font=("Arial", 16)).pack(pady=20)

# Overview button
ttk.Button(root, text="Show Overview Summary", command=show_summary).pack(pady=10)

# Category-based
ttk.Label(root, text="By Category", font=("Arial", 14)).pack(pady=10)
ttk.Button(root, text="Average Rating", command=lambda: show_category_plot("rating", "Average Rating by Category", "Average Rating")).pack(pady=5)
ttk.Button(root, text="Actual Price", command=lambda: show_category_plot("actual_price", "Average Actual Price by Category", "Actual Price")).pack(pady=5)
ttk.Button(root, text="Discount Price", command=lambda: show_category_plot("discount_price", "Average Discount Price by Category", "Discount Price")).pack(pady=5)
ttk.Button(root, text="Discount %", command=lambda: show_category_plot("discount_percent", "Average % Discount by Category", "Discount (%)")).pack(pady=5)

# Price-bin-based
ttk.Label(root, text="By Price Bins", font=("Arial", 14)).pack(pady=10)
ttk.Button(root, text="Actual Price vs Rating", command=lambda: show_price_bin_plot("actual_price", "Actual Price")).pack(pady=5)
ttk.Button(root, text="Discount Price vs Rating", command=lambda: show_price_bin_plot("discount_price", "Discount Price")).pack(pady=5)
ttk.Button(root, text="Sold Price vs Rating", command=lambda: show_price_bin_plot("price", "Sold Price")).pack(pady=5)
ttk.Button(root, text="Discount % vs Rating", command=lambda: show_price_bin_plot("discount_percent", "Discount Percent")).pack(pady=5)

root.mainloop()

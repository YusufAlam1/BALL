# This script is to visualize the movement of players using animation

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

df = pd.read_csv("./data/201601020CHO/x_loc,y_loc,game_clock.csv")

df = df.sort_values("game_clock", ascending=False).reset_index(drop=True)

x = df["x_loc"].values
y = df["y_loc"].values
t = df["game_clock"].values

plt.style.use("ggplot")
fig, ax = plt.subplots(figsize=(7, 7))

ax.set_xlim(min(x) - 2, max(x) + 2)
ax.set_ylim(min(y) - 2, max(y) + 2)
ax.set_xlabel("X Position")
ax.set_ylabel("Y Position")
ax.set_title("Player Movement Animation")

# Cuztomizing visualization
dot, = ax.plot([], [], "o", color="red", markersize=8)  
trail, = ax.plot([], [], "-", color="blue", linewidth=2, alpha=0.6)

time_text = ax.text(0.02, 0.95, "", transform=ax.transAxes)

def update(frame):
    
    dot.set_data([x[frame]], [y[frame]])
    
    trail.set_data(x[:frame], y[:frame])

    time_text.set_text(f"Game Clock: {t[frame]:.2f}s")
    return dot, trail, time_text

anim = FuncAnimation(
    fig,
    update,
    frames=len(df),
    interval=30,      
    blit=True
)

plt.show()
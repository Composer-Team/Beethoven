import matplotlib.pyplot as plt

perf250mhz = {
    "read": {
        "HLS": 11.82,
        "Pure-HDL": 7.82,
        "Beethoven": 13.35,
        "Beethoven No-TLP": 7.45
    }, "write": {
        "HLS": 4.33,
        "Pure-HDL": 7.82,
        "Beethoven": 12.54,
        "Beethoven No-TLP": 9.48
    }, "memcpy": {
        "HLS": 2.82,
        "Pure-HDL": 7.31,
        "Beethoven": 6.82,
        "Beethoven No-TLP": 6.69
    }
}

# make a bar chart that plots the performance of read, write, and memcpy on visually separated sets of bars,
# and then plot the performance of the HLS, RTL, and Beethoven implementations of each of these on top of each other
plt.figure()
plt.ylabel("Performance (GB/s)")
scale = 2
w = scale / 5
# plt.bar([0, scale, scale*2], [perf250mhz["read"]["HLS"], perf250mhz["write"]["HLS"], perf250mhz["memcpy"]["HLS"]],
#         width=w, label="HLS")
# plt.bar([w, scale+w, scale*2+w], [perf250mhz["read"]["Pure-HDL"], perf250mhz["write"]["Pure-HDL"], perf250mhz["memcpy"]["Pure-HDL"]],
#         width=w, label="Pure-HDL")
# plt.bar([w*2, scale+2*w, 2*(scale+w)], [perf250mhz["read"]["Beethoven"], perf250mhz["write"]["Beethoven"], perf250mhz["memcpy"]["Beethoven"]],
#         width=w, label="Beethoven")
# plt.bar([w*3, scale+3*w, 2*scale+3*w], [perf250mhz["read"]["Beethoven No-TLP"], perf250mhz["write"]["Beethoven No-TLP"], perf250mhz["memcpy"]["Beethoven No-TLP"]],
#         width=w, label="Beethoven No-TLP")
# plt.xticks([1.5*w, scale+1.5*w, 2*scale+1.5*w], ["Read", "Write", "Memcpy"])

# Do the equivalent to above except use patterns instead of colors to identify the bars
plt.bar([0, scale, scale*2], [perf250mhz["read"]["HLS"], perf250mhz["write"]["HLS"], perf250mhz["memcpy"]["HLS"]],
        width=w, label="HLS", hatch='//', fill=False, edgecolor='black')
plt.bar([w, scale+w, scale*2+w], [perf250mhz["read"]["Pure-HDL"], perf250mhz["write"]["Pure-HDL"], perf250mhz["memcpy"]["Pure-HDL"]],
        width=w, label="Pure-HDL", hatch='\\\\', fill=False, edgecolor='black')
plt.bar([w*2, scale+2*w, 2*(scale+w)], [perf250mhz["read"]["Beethoven"], perf250mhz["write"]["Beethoven"], perf250mhz["memcpy"]["Beethoven"]],
        width=w, label="Beethoven", hatch='xx', fill=False, edgecolor='black')
plt.bar([w*3, scale+3*w, 2*scale+3*w], [perf250mhz["read"]["Beethoven No-TLP"], perf250mhz["write"]["Beethoven No-TLP"], perf250mhz["memcpy"]["Beethoven No-TLP"]],
        width=w, label="Beethoven No-TLP", hatch='--', color="gray", edgecolor='black')
plt.xticks([1.5*w, scale+1.5*w, 2*scale+1.5*w], ["Read", "Write", "Memcpy"])

# tight layout
plt.tight_layout()

# set the size of the figure

plt.gcf().set_size_inches(6, 3)

# draw light dashed lines along the y ticks
plt.grid(axis='y', linestyle='dashed')

plt.legend()
plt.show()

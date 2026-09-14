# -*- coding: utf-8 -*-
"""回测结果绘图:价格+买卖点、资金曲线 vs 基准。

render_axes() 把图画到给定的两个 Axes 上,供命令行(存文件)和 GUI(内嵌)共用。
"""

import matplotlib

# 中文字体(设在全局 rcParams,对所有 Figure 生效)
matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "sans-serif"]
matplotlib.rcParams["axes.unicode_minus"] = False


def render_axes(result, title, ax1, ax2):
    """把回测结果画到 ax1(价格+买卖点)与 ax2(资金曲线)。"""
    df = result.data
    trades = result.trades

    ax1.plot(df.index, df["close"], color="#333333", linewidth=1.1, label="收盘价")
    buys = [t for t in trades if t["type"] == "买入"]
    sells = [t for t in trades if t["type"] == "卖出"]
    if buys:
        ax1.scatter([t["date"] for t in buys], [t["price"] for t in buys],
                    marker="^", color="#e5533c", s=90, zorder=5, label="买入")
    if sells:
        ax1.scatter([t["date"] for t in sells], [t["price"] for t in sells],
                    marker="v", color="#2e8b57", s=90, zorder=5, label="卖出")
    ax1.set_title(title, fontsize=14, fontweight="bold")
    ax1.set_ylabel("价格")
    ax1.legend(loc="best")
    ax1.grid(alpha=0.3)

    ax2.plot(result.equity.index, result.equity.values,
             color="#2563eb", linewidth=1.6, label="策略资金曲线")
    ax2.plot(result.benchmark.index, result.benchmark.values,
             color="#999999", linewidth=1.3, linestyle="--", label="买入持有(基准)")
    ax2.set_ylabel("资金")
    ax2.set_xlabel("日期")
    ax2.legend(loc="best")
    ax2.grid(alpha=0.3)


def plot_result(result, title, out_path):
    """命令行用:创建图并保存为图片文件。"""
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(12, 9), sharex=True, gridspec_kw={"height_ratios": [1.3, 1]}
    )
    render_axes(result, title, ax1, ax2)
    fig.tight_layout()
    fig.savefig(out_path, dpi=110, bbox_inches="tight")
    plt.close(fig)
    return out_path

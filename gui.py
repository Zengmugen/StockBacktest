# -*- coding: utf-8 -*-
"""A 股策略回测工具 —— 图形界面(tkinter)

输入股票代码与参数,点击"开始回测"即可查看绩效指标与资金曲线图。
不懂代码也能用。
"""

import os
import threading
import datetime as dt
import tkinter as tk
from tkinter import ttk, messagebox

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from stock_backtest import (
    BacktestConfig, load_data_akshare, load_data_csv,
    signal_ma_cross, run_backtest, format_metrics,
)
from plotting import render_axes

HERE = os.path.dirname(os.path.abspath(__file__))


class BacktestApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("A 股策略回测工具  ·  双均线策略")
        root.geometry("1100x760")

        self._build_input_bar()
        self._build_body()
        self._set_status("就绪。输入股票代码后点击「开始回测」;无网络可点「示例数据演示」。")

    # ----- 顶部输入栏 -----
    def _build_input_bar(self):
        bar = ttk.Frame(self.root, padding=10)
        bar.pack(side=tk.TOP, fill=tk.X)

        self.vars = {
            "symbol": tk.StringVar(value="000001"),
            "start": tk.StringVar(value="20220101"),
            "end": tk.StringVar(value=dt.date.today().strftime("%Y%m%d")),
            "short": tk.StringVar(value="5"),
            "long": tk.StringVar(value="20"),
            "cash": tk.StringVar(value="100000"),
        }
        fields = [
            ("股票代码", "symbol", 8), ("开始日期", "start", 9), ("结束日期", "end", 9),
            ("短均线", "short", 5), ("长均线", "long", 5), ("初始资金", "cash", 9),
        ]
        for label, key, width in fields:
            ttk.Label(bar, text=label).pack(side=tk.LEFT, padx=(6, 2))
            ttk.Entry(bar, textvariable=self.vars[key], width=width).pack(side=tk.LEFT)

        self.run_btn = ttk.Button(bar, text="开始回测", command=self.on_run)
        self.run_btn.pack(side=tk.LEFT, padx=12)
        ttk.Button(bar, text="示例数据演示", command=self.on_run_sample).pack(side=tk.LEFT)

    # ----- 主体:左指标 + 右图表 -----
    def _build_body(self):
        body = ttk.Frame(self.root)
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        left = ttk.Frame(body, padding=(10, 6))
        left.pack(side=tk.LEFT, fill=tk.Y)
        ttk.Label(left, text="回测绩效", font=("Microsoft YaHei", 12, "bold")).pack(anchor=tk.W)
        self.metrics_text = tk.Text(left, width=40, height=20, font=("Consolas", 11),
                                    wrap=tk.NONE, relief=tk.FLAT, bg="#f5f7fa")
        self.metrics_text.pack(fill=tk.Y, expand=True, pady=6)

        right = ttk.Frame(body)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.fig = Figure(figsize=(8, 6), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=right)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.status = ttk.Label(self.root, text="", anchor=tk.W, relief=tk.SUNKEN, padding=4)
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

        # 免责声明
        ttk.Label(self.root, text="免责声明:本工具仅用于历史数据的技术回测与学习研究,不构成任何投资建议。",
                  foreground="#888").pack(side=tk.BOTTOM, fill=tk.X, padx=6)

    def _set_status(self, msg):
        self.status.config(text=msg)

    # ----- 事件 -----
    def on_run(self):
        self._start(self._load_online)

    def on_run_sample(self):
        self._start(self._load_sample)

    def _start(self, loader):
        self.run_btn.config(state=tk.DISABLED)
        self._set_status("正在获取数据并回测,请稍候 ...")
        threading.Thread(target=self._worker, args=(loader,), daemon=True).start()

    def _load_online(self):
        v = self.vars
        df = load_data_akshare(v["symbol"].get().strip(), v["start"].get().strip(),
                               v["end"].get().strip())
        return df, v["symbol"].get().strip()

    def _load_sample(self):
        path = os.path.join(HERE, "sample_data.csv")
        if not os.path.exists(path):
            raise FileNotFoundError("未找到 sample_data.csv 示例数据文件。")
        return load_data_csv(path), "示例数据"

    def _worker(self, loader):
        try:
            df, name = loader()
            short = int(self.vars["short"].get())
            long = int(self.vars["long"].get())
            cash = float(self.vars["cash"].get())
            pos = signal_ma_cross(df, short, long)
            result = run_backtest(df, pos, BacktestConfig(initial_cash=cash))
            title = f"{name}  双均线({short}/{long})回测"
            self.root.after(0, self._show_result, result, title)
        except Exception as e:  # noqa: BLE001
            self.root.after(0, self._show_error, str(e))

    def _show_result(self, result, title):
        self.metrics_text.delete("1.0", tk.END)
        self.metrics_text.insert(tk.END, title + "\n" + "=" * 26 + "\n")
        self.metrics_text.insert(tk.END, format_metrics(result.metrics))

        self.fig.clear()
        ax1, ax2 = self.fig.subplots(2, 1, sharex=True,
                                     gridspec_kw={"height_ratios": [1.3, 1]})
        render_axes(result, title, ax1, ax2)
        self.fig.tight_layout()
        self.canvas.draw()

        self.run_btn.config(state=tk.NORMAL)
        self._set_status(f"完成:{title}")

    def _show_error(self, msg):
        self.run_btn.config(state=tk.NORMAL)
        self._set_status("出错:" + msg)
        messagebox.showerror("回测失败", msg)


def main():
    root = tk.Tk()
    BacktestApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

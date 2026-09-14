# -*- coding: utf-8 -*-
"""A 股策略回测工具 —— 图形界面(tkinter)

选择策略、输入股票代码与参数,点击"开始回测"即可查看绩效指标与资金曲线图。
内置双均线 / RSI / 布林带 / MACD 四种策略。不懂代码也能用。
"""

import os
import threading
import datetime as dt
import tkinter as tk
from tkinter import ttk, messagebox

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from stock_backtest import (
    BacktestConfig, STRATEGIES, strategy_label_to_key,
    load_data_akshare, load_data_csv, run_backtest, format_metrics,
)
from plotting import render_axes

HERE = os.path.dirname(os.path.abspath(__file__))


class BacktestApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("A 股策略回测工具  ·  多策略")
        root.geometry("1150x780")

        self.param_vars = {}   # 当前策略的参数变量
        self._build_input_bar()
        self._build_body()
        self._rebuild_params()  # 初始化参数区
        self._set_status("就绪。选择策略、输入股票代码后点「开始回测」;无网络可点「示例数据演示」。")

    # ----- 顶部输入区(两行) -----
    def _build_input_bar(self):
        bar = ttk.Frame(self.root, padding=(10, 8))
        bar.pack(side=tk.TOP, fill=tk.X)

        # 第一行:代码 / 日期 / 资金 / 按钮
        row1 = ttk.Frame(bar)
        row1.pack(side=tk.TOP, fill=tk.X)
        self.vars = {
            "symbol": tk.StringVar(value="000001"),
            "start": tk.StringVar(value="20220101"),
            "end": tk.StringVar(value=dt.date.today().strftime("%Y%m%d")),
            "cash": tk.StringVar(value="100000"),
        }
        for label, key, width in [("股票代码", "symbol", 8), ("开始日期", "start", 9),
                                  ("结束日期", "end", 9), ("初始资金", "cash", 9)]:
            ttk.Label(row1, text=label).pack(side=tk.LEFT, padx=(6, 2))
            ttk.Entry(row1, textvariable=self.vars[key], width=width).pack(side=tk.LEFT)
        self.run_btn = ttk.Button(row1, text="开始回测", command=self.on_run)
        self.run_btn.pack(side=tk.LEFT, padx=12)
        ttk.Button(row1, text="示例数据演示", command=self.on_run_sample).pack(side=tk.LEFT)

        # 第二行:策略选择 + 动态参数
        row2 = ttk.Frame(bar)
        row2.pack(side=tk.TOP, fill=tk.X, pady=(8, 0))
        ttk.Label(row2, text="策略").pack(side=tk.LEFT, padx=(6, 2))
        labels = [s["label"] for s in STRATEGIES.values()]
        self.strategy_var = tk.StringVar(value=labels[0])
        combo = ttk.Combobox(row2, textvariable=self.strategy_var, values=labels,
                             state="readonly", width=16)
        combo.pack(side=tk.LEFT)
        combo.bind("<<ComboboxSelected>>", lambda e: self._rebuild_params())
        ttk.Label(row2, text="   参数:").pack(side=tk.LEFT)
        self.param_frame = ttk.Frame(row2)
        self.param_frame.pack(side=tk.LEFT)

    def _rebuild_params(self):
        """根据当前策略重建参数输入框。"""
        for w in self.param_frame.winfo_children():
            w.destroy()
        self.param_vars = {}
        key = strategy_label_to_key(self.strategy_var.get())
        for pk, plabel, default, _typ in STRATEGIES[key]["params"]:
            ttk.Label(self.param_frame, text=plabel).pack(side=tk.LEFT, padx=(8, 2))
            var = tk.StringVar(value=str(default))
            ttk.Entry(self.param_frame, textvariable=var, width=6).pack(side=tk.LEFT)
            self.param_vars[pk] = var

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
            key = strategy_label_to_key(self.strategy_var.get())
            spec = STRATEGIES[key]
            kwargs = {}
            for pk, plabel, default, typ in spec["params"]:
                kwargs[pk] = typ(self.param_vars[pk].get())
            cash = float(self.vars["cash"].get())
            pos = spec["func"](df, **kwargs)
            result = run_backtest(df, pos, BacktestConfig(initial_cash=cash))
            title = f"{name}  {spec['label']}  回测"
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
